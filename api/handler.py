import base64
import io
from queue import Empty
import sys
import os
import json
import copy
import uuid
import requests
import time
from threading import Thread
from timeit import default_timer as timer
from requests_aws4auth import AWS4Auth
from opensearchpy import OpenSearch, helpers, RequestsHttpConnection
# imports for hash - to test for unique records
import hashlib
from collections import OrderedDict
# imports for reuse operations (using both libs increases overall project size by ~20MB)
import numpy as np
import statistics
import config as cfg

# Local: utility
sys.path.append(os.path.abspath("others"))
import project
import utility
import exceptions

# Local: functions for CBR cycle
sys.path.append(os.path.abspath("cbrcycle"))
import retrieve
import reuse
import revise
import retain


# For example, my-test-domain.us-east-1.es.amazonaws.com
host = cfg.aws['host']
region = cfg.aws['region']  # e.g. eu-west-2
access_key = cfg.aws['access_key']
secret_key = cfg.aws['secret_key']

is_dev = cfg.is_dev

# dbs
projects_db = "projects"
config_db = "config"
tokens_db = "tokens"

headers = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Credentials': "true",
  'Content-Type': 'application/json'
}


def getESConn():
  """
  Get connection to Amazon Elasticsearch service (the casebase).
  Can be modified to point to any other Elasticsearch cluster.
  """

  if(is_dev):
    return OpenSearch(
        hosts = [{'host': 'clood-opensearch', 'port': 9200}],
        http_compress = True, # enables gzip compression for request bodies
        http_auth = ('kibanaserver','kibanaserver'),
        use_ssl = False,
        verify_certs = False,
        ssl_assert_hostname = False,
        ssl_show_warn = False,
    )

  esconn = OpenSearch(
    hosts=[{'host': host, 'port': 443}],
    http_auth=AWS4Auth(access_key, secret_key, region, 'es'),
    use_ssl=True,
    verify_certs=True,
    connection_class=RequestsHttpConnection
  )
  return esconn


# The functions below are also exposed through the API (as specified in 'serverless.yml')


def auth(event, context=None):
  """
  End-point: Check if the user is authenticated.
  """
  token = event.get('authorizationToken', None)

  response = "Allow" if utility.verifyToken(token) else "Deny"

  authResponse = {
    "principalId": "user",
    "policyDocument": {
      "Version": "2012-10-17",
      "Statement": [
        {
          "Action": "execute-api:Invoke",
          "Effect": response,
          "Resource": "*"
        }
      ]
    }
  }
  return authResponse

def authenticate(event, context=None):
  """
  End-point: Authenticates the user.
  """
  body = json.loads(event['body'])
  username = body['username']
  password = body['password']

  if username == cfg.DEFAULT_USERNAME and password == cfg.DEFAULT_PASSWORD:
    token = utility.generateToken({"name":username,"expiry": time.time()+86400})   # also send time of expiry, default 1 hour
    body = {
      "token": token,
      "authenticated": True
    }
    statusCode = 200
  else:
    body = {
      "authenticated": False
    }
    #body = exceptions.authException()
    statusCode = 200

  response = {
    "statusCode": statusCode,
    "headers": headers,
    "body": json.dumps(body)
  }
  return response

def all_projects(event, context=None):
  """
  End-point: Retrieves all projects. Each project is separate CBR application.
  """
  result = []
  es = getESConn()
  if es.indices.exists(index=projects_db):   # retrieve if ES index does exist
    query = {"query" : retrieve.MatchAll()}
    statusCode = 200
    #print("Event arn ", event.methodArn)
    
    res = es.search(index=projects_db, body=query)
    
    for hit in res['hits']['hits']:
      entry = hit['_source']
      entry['id__'] = hit['_id']
      result.append(entry)
  else:
    result = exceptions.projectIndexException()
    statusCode = 404

  response = {
    "statusCode": statusCode,
    "headers": headers,
    "body": json.dumps(result)
  }
  return response


def get_project(event, context=None):
  """
  End-point: Retrieves a specified project (details of a CBR application).
  """
  projectId = event['pathParameters']['id']
  statusCode = 200
  es = getESConn()

  if es.indices.exists(index=projects_db):
    result = utility.getByUniqueField(es, projects_db, "_id", projectId)
  else:
    result = exceptions.projectIndexException()
    statusCode = 404
  
  if not result:
    result = exceptions.projectGetException()
    statusCode = 404

  response = {
    "statusCode": statusCode,
    "headers": headers,
    "body": json.dumps(result)
  }
  return response


def new_project(event, context=None):
  """
  End-point: Creates a new CBR application (project).
  """
  proj = json.loads(event['body']) if event['body'] else {"name":""}
  statusCode = 201
  proj_id = uuid.uuid4().hex
  proj['casebase'] = proj_id + '_casebase'

  es = getESConn()
  
  if not es.indices.exists(index=projects_db):
    project_mapping = project.getProjectMapping()
    es.indices.create(index=projects_db, body=project_mapping)   # create project_db index
    utility.createOrUpdateGlobalConfig(es, config_db=config_db)   # create config db if it does not exist
  if 'casebase' not in proj or "" == proj['casebase'] or "" == proj['name']:
    result = exceptions.projectNameException()
    statusCode = 400
  elif utility.indexHasDocWithFieldVal(es, index=projects_db, field='casebase',
                                       value=proj['casebase']):
    result = exceptions.projectDuplicateException()
    statusCode = 400
  else:
    if 'attributes' not in proj:
      proj['attributes'] = []

    if 'retainDuplicateCases' not in proj:
      proj['retainDuplicateCases'] = False
    proj['hasCasebase'] = False

    try:
      result = es.index(index=projects_db, body=proj, id=proj_id)
      result = {"index": result['_index'], "id": result['_id'], "result": result['result'], "project": proj}
    except:
      result = exceptions.projectCreateException()
      statusCode = 400

  proj["id__"] = proj_id
  response = {
    "statusCode": statusCode,
    "headers": headers,
    "body": json.dumps(result)
  }
  return response


def update_project(event, context=None):
  """
  End-point: Updates a project
  """
  projectId = event['pathParameters']['id']
  proj = json.loads(event['body']) if event['body'] else {}  # get to-update project from request body
  statusCode = 201
  
  proj.pop('id__', None)  # remove id__ (was added to dict to use a plain structure)
  

  proj_old = utility.getByUniqueField(getESConn(), projects_db, "_id", projectId)  # get previous version of project

  if not proj_old:
    result = exceptions.projectGetException()
    statusCode = 404
  else:
    source_to_update = {"doc" : proj}
    es = getESConn()
  
    try:
      result = es.update(index=projects_db, id=projectId, body=source_to_update)
      source_to_update['doc']['id__'] = projectId
      result = {"index": result['_index'], "id": result['_id'], "result": result['result'], "project": source_to_update['doc']}
    except:
      result = exceptions.projectUpdateException()
      statusCode = 404

    # create the ontology similarity if specified as part of project attributes (can be a lengthy operation for mid to large ontologies!)
    if 'attributes' in proj and 'hasCasebase' in proj:
      if proj['hasCasebase']:  # check that the casebase has been created since similarity is computed when the casebase is created
        for attrib in proj['attributes']:  # for each project casebase attribute
          if attrib['type'] == "Ontology Concept" and attrib.get('options') is not None and \
                  attrib['options']:  # check that the attribute is ontology based
            old_onto_attrib = next((item for item in proj_old['attributes'] if item['name'] == attrib['name']), None)  # get the pre project update version of the attribute
            if old_onto_attrib is not None and attrib.get('similarity') is not None and attrib != old_onto_attrib:  # update ontology similarity measures if there are changes
              sim_method = 'san' if attrib['similarity'] == 'Feature-based' else 'wup'
              retrieve.setOntoSimilarity(projectId + "_ontology_" + attrib['options'].get('name'), attrib['options'].get('sources'), relation_type=attrib['options'].get('relation_type', None),
                                      root_node=attrib['options'].get('root'), similarity_method=sim_method)

  response = {
    "statusCode": statusCode,
    "headers": headers,
    "body": json.dumps(result)
  }
  return response


def delete_project(event, context=None):
  """
  End-point: Deletes a project. Also deletes the project's casebase index if it exists.
  """
  projectId = event['pathParameters']['id']  # get project id from url
  
  statusCode = 200
  es = getESConn()
  proj = utility.getByUniqueField(es, projects_db, "_id", projectId)  # get project object

  if proj:
    if 'casebase' in proj:
      try:
        es.indices.delete(index=proj['casebase'], ignore_unavailable=True)  # delete casebase if it exists
        # delete any ontology indices that were created (if any)
        if proj['attributes']:
          for attrib in proj['attributes']:
            if attrib['type'] == "Ontology Concept":
              ontologyId = projectId + "_ontology_" + attrib['options'].get('name')
              if attrib['options'].get('name') is not None:
                retrieve.removeOntoIndex(ontologyId)
        result = es.delete(index=projects_db, id=projectId, filter_path="-_seq_no,-_shards,-_primary_term,-_version,-_type")   # delete project
      except:
        result = exceptions.projectDeleteException()
        statusCode = 400
  else:
    result = exceptions.projectGetException()
    statusCode = 404

  response = {
    "statusCode": statusCode,
    "headers": headers,
    "body": json.dumps(result)
  }
  return response


def save_case_list(event, context=None):
  """
  End-point: Saves list of case instances
  Creates index for the casebase if one does not exist
  """
  projectId = event['pathParameters']['id']
  doc_list = json.loads(event['body']) if event['body'] else {}  # parameters in request body
  verified_doc_list = []   # List to hold the cases after they have been checked
  duplicateCases = 0
  errors = ""
  hash_list = []

  statusCode = 201

  if type(doc_list) is not list:
    doc_list = [doc_list]

  es = getESConn()

  proj = utility.getByUniqueField(es, projects_db, "_id", projectId)  # get project from id

  if proj:
    project.indexMapping(es, proj)   # create project casebase if it doesn't already exist

    # format and hash documents
    for x in doc_list:
      x = retrieve.add_vector_fields(proj['attributes'], x)   # add vectors to Semantic USE fields
      x = retrieve.add_lowercase_fields(proj['attributes'], x)   # use lowercase values for EqualIgnoreCase fields
      x['hash__'] = str(hashlib.md5(json.dumps(OrderedDict(sorted(x.items()))).encode('utf-8')).digest())   # case hash for easy detection of duplicates
      if not proj['retainDuplicateCases'] and (x['hash__'] in hash_list or utility.indexHasDocWithFieldVal(es, index=proj['casebase'], field='hash__',
                                                                          value=x['hash__'])):
        duplicateCases += 1
      else:
        verified_doc_list.append(x)
        hash_list.append(x['hash__'])

    result = helpers.bulk(es, verified_doc_list, index=proj['casebase'], doc_type="_doc")   # add documents to created index
    retrieve.update_attribute_options(es,proj)

    if duplicateCases:
      errors = str(duplicateCases) + " cases were not added because they were duplicates. "
    result = {"casesAdded":result[0],"errors":[errors,result[1]]}

    # Indicate that the project has a casebase
    proj['hasCasebase'] = True
    source_to_update = {'doc': proj}

    try:
      resp = es.update(index=projects_db, id=projectId, body=source_to_update)
    except:
      result = exceptions.projectUpdateException()
      statusCode = 404
    # create the ontology similarity if specified as part of project attributes (can be a lengthy operation for mid to large ontologies!)
    for attrib in proj['attributes']:
      if attrib['type'] == "Ontology Concept" and attrib.get('similarity') is not None and attrib.get('options') is not None and retrieve.checkOntoSimilarity(projectId + "_ontology_" + attrib['options'].get('name'))['statusCode'] != 200:
        sim_method = 'san' if attrib['similarity'] == 'Feature-based' else 'wup'
        retrieve.setOntoSimilarity(projectId + "_ontology_" + attrib['options'].get('name'), attrib['options'].get('sources'), relation_type=attrib['options'].get('relation_type'), root_node=attrib['options'].get('root'), similarity_method=sim_method)
  else:
    result = exceptions.projectGetException()
    statusCode = 404

  response = {
    "statusCode": statusCode,
    "headers": headers,
    "body": json.dumps(result)
  }
  return response


def get_all_cases(event, context=None):
  """
  End-point: Returns the cases in a casebase. Need to include 'size' in request if more than 100 cases.
  Also supports pagination by including 'size' and 'start' (offset) properties
  """
  params = json.loads(event['body'])  # parameters in request body
  proj = params.get('project')
  projId = params.get('projectId')  
  statusCode = 200
  es = getESConn()  # es connection

  if proj is None and projId is not None:  
    proj = utility.getByUniqueField(es, projects_db, "_id", projId)   

  if proj:
    start = params.get('start', 0)  # optional offset (default is 0)
    size = params.get('size', 100)  # optional size (default is 100)
    if es.indices.exists(index=proj['casebase']):
      result = utility.getIndexEntries(es, proj['casebase'], start, size)
    else:
      result = exceptions.casebaseGetException()
      statusCode = 404
  else:
    result = exceptions.projectGetException()
    statusCode = 404

  response = {
    "statusCode": statusCode,
    "headers": headers,
    "body": json.dumps(result)
  }
  return response


def get_case(event, context=None):
  """
  End-point: Retrieves a specific case from a project's casebase.
  """
  statusCode = 200
  projectId = event['pathParameters']['id']
  caseId = event['pathParameters']['cid']
  es = getESConn()

  if utility.getByUniqueField(es, projects_db, "_id", projectId):
    if es.indices.exists(index=projectId+"_casebase"):
      result = utility.getByUniqueField(es, projectId+"_casebase", "_id", caseId) # get case
    else:
      result = exceptions.casebaseGetException()
      statusCode = 404
  else:
    result = exceptions.projectGetException()
    statusCode = 404

  if not result:
    result = exceptions.caseGetException()
    statusCode = 404

  response = {
    "statusCode": statusCode,
    "headers": headers,
    "body": json.dumps(result)
  }  

  return response


def update_case(event, context=None):
  """
  End-point: Updates the specified case.
  """
  statusCode = 201
  case = json.loads(event['body']) if event['body'] else {}  # parameters in request body
  projectId = event['pathParameters']['id']
  caseId = event['pathParameters']['cid']
  casebase = projectId + "_casebase"
  
  es = getESConn()
  proj = utility.getByUniqueField(es, projects_db, "_id", projectId)

  if proj:
    if es.indices.exists(index=casebase):
      oldCase = utility.getByUniqueField(es, casebase, "_id", caseId)
      if oldCase:
        oldCase.pop('id__', None)
        oldCase.pop('score__', None)
        oldCase.pop('hash__', None)

        for key,value in case.items():
          for attr in proj['attributes']:
            if attr['name'] == key:
              if attr['similarity'] == "Semantic SBERT":
                if key not in oldCase or oldCase[key] is None or oldCase[key]['name'] is None:
                  oldCase[key] = {'name':'', 'rep': ''}
                oldCase[key]['name'] = value
                oldCase[key]['rep'] = retrieve.getVectorSemanticSBERT(value)
              else:
                oldCase[key] = value
        oldCase['hash__'] = str(hashlib.md5(json.dumps(OrderedDict(sorted(oldCase.items()))).encode('utf-8')).digest()) # Create new hash
        source_to_update = {'doc': oldCase}

        if not proj['retainDuplicateCases'] and utility.indexHasDocWithFieldVal(es, index=proj['casebase'], field='hash__',
                                                                          value=oldCase['hash__']):
          result = exceptions.caseDuplicateException()
          statusCode = 400
        else:
          try:
            result = es.update(index=casebase, id=caseId, body=source_to_update,filter_path="-_seq_no,-_shards,-_primary_term,-_type",refresh=True)
            retrieve.update_attribute_options(es,proj)
          except:
            result = exceptions.caseUpdateException()
            statusCode = 400
      else:
        result = exceptions.caseGetException()
        statusCode = 404
    else:
      result = exceptions.casebaseGetException()
      statusCode = 404      
  else:
    result = exceptions.projectGetException()
    statusCode = 404
    
  response = {
    "statusCode": statusCode,
    "headers": headers,
    "body": json.dumps(result)
  }  

  return response


def delete_casebase(event, context=None):
  """
  End-point: Deletes the casebase for a specific project
  """
  statusCode = 200
  projectId = event['pathParameters']['id']
  casebase = projectId + "_casebase"

  es = getESConn()

  proj = utility.getByUniqueField(es, projects_db, "_id", projectId)

  if proj:
    try:
      result = es.indices.delete(index=casebase, ignore_unavailable = True) 
    except:
      result = exceptions.casebaseDeleteException()
      statusCode = 400

    if statusCode == 200:
      proj['hasCasebase'] = False
      source_to_update = {'doc': proj}
      es.update(index=projects_db, id=projectId, body=source_to_update)

  else:
    result = exceptions.projectGetException()
    statusCode = 404

  response = {
    "statusCode": statusCode,
    "headers": headers,
    "body": json.dumps(result)
  }

  return response


def delete_case(event, context=None):
  """
  End-point: Delete the specified case from a project
  """
  statusCode = 200
  projectId = event['pathParameters']['id']
  caseId = event['pathParameters']['cid']
  casebase = projectId + "_casebase"
  es = getESConn()
  proj = utility.getByUniqueField(es, projects_db, "_id", projectId)

  if es.indices.exists(index=casebase):
    if es.exists(index=casebase, id=caseId):
      try:
        result = es.delete(index=casebase, id=caseId, filter_path="-_seq_no,-_shards,-_primary_term,-_version,-_type",refresh=True)
        retrieve.update_attribute_options(es,proj)
      except:
        result = exceptions.caseDeleteException()
        statusCode = 400
    else:
      result = exceptions.caseGetException()
      statusCode = 404
  else:
    result = exceptions.casebaseGetException()
    statusCode = 404

  response = {
    "statusCode": statusCode,
    "headers": headers,
    "body": json.dumps(result)
  }
  return response


def update_attribute_options(event, context=None):
  """
  End-point: Updates the options for a specific attribute or attributes
  """
  statusCode = 201
  projectId = event['pathParameters']['id']
  attrNames = json.loads(event['body']) if event['body'] else {}

  es = getESConn()
  proj = utility.getByUniqueField(es, projects_db, "_id", projectId)

  if proj:
    result = retrieve.update_attribute_options(es, proj, attrNames)
  else:
    result = exceptions.projectGetException()
    statusCode = 404

  response = {
    "statusCode": statusCode,
    "headers": headers,
    "body": json.dumps(result)
  }

  return response


def create_project_index(event, context=None):
  """
  End-point: Creates the mapping for an index if it does not exist.
  """
  es = getESConn()
  pid = event['pathParameters']['id']
  proj = utility.getByUniqueField(es, projects_db, "_id", pid)  # project
  res = project.indexMapping(es, proj)

  # Indicate that the project has a casebase (empty)
  proj['hasCasebase'] = True
  source_to_update = {'doc': proj}
  res = es.update(index=projects_db, id=pid, body=source_to_update)

  response = {
    "statusCode": 201,
    "headers": headers,
    "body": json.dumps(res)
  }
  return response


def re_create_config(event, context=None):
  """
  End-point: (Temporary) To re-create the config after changes are made programmatically
  """
  # get config. configuration index has 1 document
  result = []
  es = getESConn()
  utility.createOrUpdateGlobalConfig(es, config_db=config_db)
  time.sleep(0.3)  # 0.3 sec wait to allow time for created index to be ready
  query = {"query": retrieve.MatchAll()}
  res = es.search(index=config_db, body=query)
  if (res['hits']['total']['value'] > 0):
    result = res['hits']['hits'][0]['_source']
  response = {
    "statusCode": 200,
    "headers": headers,
    "body": json.dumps(result)
  }
  return response


def get_config(event, context=None):
  """
  End-point: Retrieves configuration
  """
  # get config. configuration index has 1 document
  result = []
  es = getESConn()
  if not es.indices.exists(index=config_db):  # create config db if it does not exist
    utility.createOrUpdateGlobalConfig(es, config_db=config_db)
    time.sleep(1)  # 0.3 sec wait to allow time for created index to be ready
  query = {"query": retrieve.MatchAll()}
  res = es.search(index=config_db, body=query)
  if (res['hits']['total']['value'] > 0):
    result = res['hits']['hits'][0]['_source']
  response = {
    "statusCode": 200,
    "headers": headers,
    "body": json.dumps(result)
  }
  return response


def update_config(event, context=None):
  """
  End-point: Updates configuration
  """
  res = utility.createOrUpdateGlobalConfig(getESConn(), config_db=config_db, globalConfig=json.loads(event['body']))
  msg = "Configuration updated" if res else "Configuration not updated"
  body = {
    "result": res,
    "message": msg
  }
  response = {
    "statusCode": 201,
    "headers": headers,
    "body": json.dumps(body)
  }
  return response


def check_ontology_sim(event, context=None):
  """
  End-point: Check if the similarity measures of an ontology's concepts exist.
  """
  ontology_id = event['pathParameters']['ontology_id']
  res = retrieve.checkOntoSimilarity(ontology_id)
  body = {
    "result": res
  }
  response = {
    "statusCode": 201,
    "headers": headers,
    "body": json.dumps(body)
  }
  return response


# def update_ontology_sim(event, context=None):
#   """
#   End-point: Computes and persists the similarity measures of an ontology's concepts using its hierarchical structure.
#   """
#   attrib = json.loads(event['body'])
#   res = retrieve.setOntoSimilarity(attrib['options'].get('name'), attrib['options'].get('sources'), relation_type=attrib['options'].get('relation_type', None), root_node=attrib['options'].get('root', None))
#   body = {
#     "result": res
#   }
#   response = {
#     "statusCode": 201,
#     "headers": headers,
#     "body": json.dumps(body)
#   }
#   return response


def cbr_retrieve(event, context=None):
  """
  End-point: Completes the Retrieve step of the CBR cycle.
  """
  start = timer()  # start timer

  params = json.loads(event['body'])  # parameters in request body
  # print(params)
  queryFeatures = params.get('data')
  addExplanation = params.get('explanation')
  addFeedback = params.get('feedback')
  proj = params.get('project')
  # filter = params.get('filter', None)
  globalSim = params.get('globalSim', "Weighted Sum")  # not used as default aggregation is a weighted sum of local similarity values

  result = {'recommended': {}, 'bestK': []}
  response = {"statusCode": 200, "headers": headers, "body": ""}
  queryAdded = False
  es = getESConn()

  if proj is None:   # if project object is not specified, find using project id
    projId = params.get('projectId')
    proj = utility.getByUniqueField(es, projects_db, "_id", projId)

  proj_attributes = proj['attributes']
  
  query = {"query": {"bool": {"filter": [], "should": []}}}
  query["size"] = int(params.get('topk', 5))  # number of cases to retrieve, default is 5

  for entry in queryFeatures: # add term filters (extend to include range filters for numbers and dates)
    if entry.get('filterTerm') is not None and entry.get('filterTerm') != 'None':
      field = entry.get('name')
      value = entry.get('value')
      # filter = { "term":  { field: value }}
      filter = retrieve.get_filter_object(entry.get('filterTerm'), field, entry.get('filterValue'), value)
      if filter is not None:
        query["query"]["bool"]["filter"].append(filter)
        queryAdded = True

    if entry.get('value') is not None and "" != entry['value'] and int(
            entry.get('weight', 1)) > 0 and entry.get('similarity') != "None":
      field = entry['name']
      value = entry['value']
      similarityType = entry.get('similarity', [x['similarity'] for x in proj_attributes if x['name'] == field][0])  # get similarity type from project attributes if not stated in query
      valueType = entry.get('type', [x['type'] for x in proj_attributes if x['name'] == field][0])  # get value type from project attributes if not stated in query
      weight = entry.get('weight', [x['weight'] for x in proj_attributes if x['name'] == field][0])  # default weight if property is missing
      options = retrieve.get_attribute_by_name(proj['attributes'], field).get('options', None)   # get options for attribute
      queryAdded = True

      qfnc = retrieve.getQueryFunction(proj['id__'], field, value, valueType, weight, similarityType, options)
      query["query"]["bool"]["should"].append(qfnc)

  # if filter is not None and filter != "" and filter != {}:   # add filter to query if specified
  #   query["query"]["bool"].update({"filter": {"term": filter} })

  if not queryAdded:  # If no query features are specified, return all cases up to topk
    query["query"]["bool"]["should"].append(retrieve.MatchAll())
  
  # perform retrieval
  res = es.search(index=proj['casebase'], body=query, explain=addExplanation)

  # format results
  counter = 0
  for hit in res['hits']['hits']:
    entry = hit['_source']
    entry.pop('hash__', None)  # remove hash field and value
    entry = retrieve.remove_vector_fields(proj_attributes, entry)  # remove vectors from Semantic USE and Semantic SBERT fields
    if counter == 0:
      result['recommended'] = copy.deepcopy(entry)   # Make recommended case the first case in the result
    entry['score__'] = hit['_score']  # removed during an update operation
    result['bestK'].append(entry)
    if addExplanation:  # if retrieval needs an explanation included
      entry['match_explanation'] = retrieve.get_explain_details(hit['_explanation'])
    if addFeedback:  # if retrieval needs feedback included
      entry['feedback'] = retrieve.get_feedback_details(queryFeatures, proj['casebase'], hit['_id'], es)
    counter += 1

  # Get the recommended result using chosen reuse strategies for unknown attribute values
  if counter > 0:
    for entry in queryFeatures:
      field = entry['name']
      strategy = entry.get('strategy', "NN value")  # NN (nearest neighbour)
      if not entry.get('unknown', False) and entry.get('value') is not None and "" != entry['value']:  # copy known values
        result['recommended'][field] = entry['value']
      else:  # use reuse strategies for unknown fields
        if field in result['recommended']:
          if strategy == "Maximum":
            result['recommended'][field] = max(d[field] for d in result['bestK'])
          elif strategy == "Minimum":
            result['recommended'][field] = min(d[field] for d in result['bestK'])
          elif strategy == "Mean":
            result['recommended'][field] = np.mean([x[field] for x in result['bestK']])
          elif strategy == "Median":
            result['recommended'][field] = np.median([x[field] for x in result['bestK']])
          elif strategy == "Mode" or strategy == "Majority":
            result['recommended'][field] = statistics.mode([x[field] for x in result['bestK']])
          elif strategy == "Minority":
            lst = [x[field] for x in result['bestK']]
            result['recommended'][field] = min(set(lst), key=lst.count)
          else:
            result['recommended'][field] = result['bestK'][0][field]  # assign value of 'NN value'
    # generate a new random id to make (if there was an id) to make it different from existing cases
    if result['recommended'].get('id') is not None:
      result['recommended']['id'] = uuid.uuid4().hex

  end = timer()  # end timer
  result['retrieveTime'] = end - start
  result['esTime'] = res['took']
  response = {
    "statusCode": 200,
    "headers": headers,
    "body": json.dumps(result)
  }
  return response


def cbr_reuse(event, context=None):
  """
  End-point: Completes the Reuse step of the CBR cycle.
  """
  result = {}
  params = json.loads(event['body'])  # parameters in request body
  # get reuse type
  reuse_type = params.get('reuse_type', 'isee-question-intent')
  if reuse_type == 'isee-question-intent':
    result = reuse.custom_reuse_isee(params)

  response = {
    "statusCode": 200,
    "headers": headers,
    "body": json.dumps(result)
  }
  return response


def cbr_revise(event, context=None):
  """
  End-point: Completes the Revise step of the CBR cycle.
  """
  result = {}
  # revise logic here

  response = {
    "statusCode": 200,
    "headers": headers,
    "body": json.dumps(result)
  }
  return response


def cbr_retain(event, context=None):
  """
  End-point: Completes the Retain step of the CBR cycle. Note: If the new case have id of an existing case, the new case will replace the existing entry.
  """
  statusCode = 201
  params = json.loads(event['body'])  # parameters in request body
  proj = params.get('project')
  es = getESConn()

  if proj is None:   # if project object is not specified, find using project id
    projId = params.get('projectId')
    proj = utility.getByUniqueField(es, projects_db, "_id", projId)

  if proj:
    pid = proj["id__"]
    if(not proj['hasCasebase']): # Update project status if only using retain API
      proj['hasCasebase'] = True
      source_to_update = {'doc': proj}
      res = es.update(index=projects_db, id=pid, body=source_to_update)
      # create index with mapping if it does not exist already
      project.indexMapping(es, proj)

      # create the ontology similarity if specified as part of project attributes (can be a lengthy operation for mid to large ontologies!)
      for attrib in proj['attributes']:
        if attrib['type'] == "Ontology Concept" and attrib.get('similarity') is not None and attrib.get(
                'options') is not None and \
                retrieve.checkOntoSimilarity(pid + "_ontology_" + attrib['options'].get('name'))['statusCode'] != 200:
          sim_method = 'san' if attrib['similarity'] == 'Feature-based' else 'wup'
          retrieve.setOntoSimilarity(pid + "_ontology_" + attrib['options'].get('name'),
                                    attrib['options'].get('sources'),
                                    relation_type=attrib['options'].get('relation_type'),
                                    root_node=attrib['options'].get('root'), similarity_method=sim_method)

    new_case = params['data']
    if isinstance(new_case, str):  # new_case could be str or dict
      new_case = json.loads(new_case)
    case_id = new_case.get('_id') # check for optional id in case description
    new_case = retrieve.add_vector_fields(proj['attributes'], new_case)  # add vectors to Semantic USE fields

    new_case['hash__'] = str(hashlib.md5(json.dumps(OrderedDict(sorted(new_case.items()))).encode('utf-8')).digest())
    new_case.pop('_id',None) # remove id field if present

    if not proj['retainDuplicateCases'] and utility.indexHasDocWithFieldVal(es, index=proj['casebase'], field='hash__',
                                                                            value=new_case['hash__']):
      result = exceptions.caseDuplicateException()
      statusCode = 400
    else:
      if case_id is None:
        result = es.index(index=proj['casebase'], body=new_case, filter_path="-_seq_no,-_shards,-_primary_term,-_version,-_type")
      else:
        result = es.index(index=proj['casebase'], body=new_case, id=case_id, filter_path="-_seq_no,-_shards,-_primary_term,-_version,-_type")
  else:
    result = exceptions.projectGetException()
    statusCode = 404

  response = {
    "statusCode": statusCode,
    "headers": headers,
    "body": json.dumps(result)
  }
  return response


def retrieve_explain(event, context):
  """
  End-point: Explain the scoring for a retrieved case.
  """
  res = {}
  statusCode = 201
  params = json.loads(event['body'])  # parameters in request body

  proj = params.get('project')
  query = params.get('query')
  caseId = params.get('caseId')
  es = getESConn()
  if proj is None:
    projId = params.get('projectId')  # name of casebase
    proj = utility.getByUniqueField(es, projects_db, "_id", projId)

  res = es.explain(index=proj['casebase'], body=query, id=caseId)

  response = {
    "statusCode": statusCode,
    "headers": headers,
    "body": json.dumps(res)
  }
  return response

def all_tokens(event, context):
  """
  End-point: Get all tokens in the casebase.
  """
  result = []
  es = getESConn()
  if es.indices.exists(index=tokens_db):
    query = {"query" : retrieve.MatchAll()}
    statusCode = 200
    #print("Event arn ", event.methodArn)
    
    res = es.search(index=tokens_db, body=query)
    
    for hit in res['hits']['hits']:
      entry = hit['_source']
      entry['id__'] = hit['_id']
      result.append(entry)
  else:
    result = exceptions.tokenIndexException()
    statusCode = 404

  response = {
    "statusCode": statusCode,
    "headers": headers,
    "body": json.dumps(result)
  }
  return response

def new_token(event, context):
  """
  End-point: Creates a new JWT token.
  """
  token = json.loads(event['body']) if event['body'] else {"name":""}
  statusCode = 201
  token_id = uuid.uuid4().hex

  es = getESConn()
  
  if not es.indices.exists(index=tokens_db):
    token_mapping = project.getTokenMapping()
    es.indices.create(index=tokens_db, body=token_mapping)   # create project_db index
    utility.createOrUpdateGlobalConfig(es, config_db=config_db)   # create config db if it does not exist
  if 'expiry' not in token or "" == token['expiry'] or 'name' not in token or "" == token['name']:
    result = exceptions.tokenNameException()
    statusCode = 400
  else:
    token['token'] = utility.generateToken(token)
    # print("token ", token)
    if "token" in token and token['token'] is not None:
      try:
        # print("token2 ", token)
        result = es.index(index=tokens_db, body=token, id=token_id)
        result = {"index": result['_index'], "id": result['_id'], "result": result['result'], "token": token}
      except:
        result = exceptions.tokenCreateException()
        statusCode = 400

  token["id__"] = token_id
  response = {
    "statusCode": statusCode,
    "headers": headers,
    "body": json.dumps(result)
  }
  return response

def delete_token(event, context):
  """
  End-point: Delete a token.
  """
  token_id = event['pathParameters']['id']
  es = getESConn()
  if es.indices.exists(index=tokens_db):
    try:
      result = es.delete(index=tokens_db, id=token_id)
      statusCode = 200
    except:
      result = exceptions.tokenDeleteException()
      statusCode = 400
  else:
    result = exceptions.tokenIndexException()
    statusCode = 404

  response = {
    "statusCode": statusCode,
    "headers": headers,
    "body": json.dumps(result)
  }
  return response

def home(event, context):
  """
  End-point: To check API reachability.
  """
  body = {
    "message": "Go Serverless with CloodCBR! Your function executed successfully!"
  }

  response = {
    "statusCode": 200,
    "headers": headers,
    "body": json.dumps(body)
  }
  
  return response