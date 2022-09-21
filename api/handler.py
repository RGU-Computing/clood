import sys
import os
import json
import copy
import uuid
import requests
import time
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

def all_projects(event, context=None):
  """
  End-point: Retrieves all projects. Each project is separate CBR application.
  """
  result = []
  # retrieve if ES index does exist
  es = getESConn()
  if es.indices.exists(index=projects_db):
    query = {}
    query['query'] = retrieve.MatchAll()

    res = es.search(index=projects_db, body=query)
    for hit in res['hits']['hits']:
      entry = hit['_source']
      entry['id__'] = hit['_id']
      result.append(entry)

  response = {
    "statusCode": 200,
    "headers": headers,
    "body": json.dumps(result)
  }
  return response


def get_project(event, context=None):
  """
  End-point: Retrieves a project (details of a CBR application).
  """
  pid = event['pathParameters']['id']
  # retrieve if ES index does exist
  result = utility.getByUniqueField(getESConn(), projects_db, "_id", pid)

  response = {
    "statusCode": 200,
    "headers": headers,
    "body": json.dumps(result)
  }
  return response


def new_project(event, context=None):
  """
  End-point: Creates a new CBR application (project).
  """
  result = {}
  statusCode = 201
  proj = json.loads(event['body'])  # parameters in request body
  # create ES index for Projects if it does not exist
  es = getESConn()
  proj_id = uuid.uuid4().hex
  proj['casebase'] = proj_id + '_casebase'
  if not es.indices.exists(index=projects_db):
    project_mapping = project.getProjectMapping()
    es.indices.create(index=projects_db, body=project_mapping)
    # create config db if it does not exist
    utility.createOrUpdateGlobalConfig(es, config_db=config_db)

  if 'casebase' not in proj or "" == proj['casebase'] or "" == proj['name']:
    result = "A new project has to specify a name and a casebase."
    statusCode = 400
  elif utility.indexHasDocWithFieldVal(es, index=projects_db, field='casebase',
                                       value=proj['casebase']):  # (index, field, value)
    result = "Casebase already exists. Choose a different name for the casebase."
    statusCode = 400
  else:
    proj['attributes'] = []
    proj['hasCasebase'] = False
    # print(proj)
    result = es.index(index=projects_db, body=proj, id=proj_id)

  proj["id__"] = proj_id
  response = {
    "statusCode": statusCode,
    "headers": headers,
    "body": json.dumps(proj)
  }
  return response


def update_project(event, context=None):
  """
  End-point: Updates a project
  """
  pid = event['pathParameters']['id']
  proj_old = utility.getByUniqueField(getESConn(), projects_db, "_id", pid)  # get previous version of project
  body = json.loads(event['body'])  # get to-update project from request body
  body.pop('id__', None)  # remove id__ (was added to dict to use a plain structure)
  source_to_update = {}
  source_to_update['doc'] = body  # parameters in request body
  # print(source_to_update)
  es = getESConn()
  res = es.update(index=projects_db, id=pid, body=source_to_update)
  # print(res)

  # create the ontology similarity if specified as part of project attributes (can be a lengthy operation for mid to large ontologies!)
  if body['hasCasebase']:  # check that the casebase has been created since similarity is computed when the casebase is created
    for attrib in body['attributes']:  # for each project casebase attribute
      if attrib['type'] == "Ontology Concept" and attrib.get('options') is not None and \
              attrib['options']:  # check that the attribute is ontology based
        old_onto_attrib = next((item for item in proj_old['attributes'] if item['name'] == attrib['name']), None)  # get the pre project update version of the attribute
        if old_onto_attrib is not None and attrib.get('similarity') is not None and attrib != old_onto_attrib:  # update ontology similarity measures if there are changes
          sim_method = 'san' if attrib['similarity'] == 'Feature-based' else 'wup'
          retrieve.setOntoSimilarity(pid + "_ontology_" + attrib['options'].get('name'), attrib['options'].get('sources'), relation_type=attrib['options'].get('relation_type', None),
                                   root_node=attrib['options'].get('root'), similarity_method=sim_method)

  source_to_update['doc']['id__'] = pid
  response = {
    "statusCode": 201,
    "headers": headers,
    "body": json.dumps(source_to_update['doc'])
  }
  return response


def delete_project(event, context=None):
  """
  End-point: Deletes a project. Also deletes the project's casebase index if it exists.
  """
  pid = event['pathParameters']['id']  # project id
  es = getESConn()
  # delete casebase
  proj = utility.getByUniqueField(es, projects_db, "_id", pid)  # get project
  casebase = proj['casebase']
  es.indices.delete(index=casebase, ignore=[400, 404])  # delete index if it exists
  # delete any ontology indices that were created (if any)
  for attrib in proj['attributes']:
    if attrib['type'] == "Ontology Concept":
      ontologyId = pid + "_ontology_" + attrib['options'].get('name')
      if attrib['options'].get('name') is not None:
        retrieve.removeOntoIndex(ontologyId)
  # delete project
  res = es.delete(index=projects_db, id=pid)

  response = {
    "statusCode": 200,
    "headers": headers,
    "body": json.dumps(res['result'])
  }
  return response


def save_case_list(event, context=None):
  """
  End-point: Saves list of case instances
  Creates index for the casebase if one does not exist
  """
  # try:
  doc_list = json.loads(event['body'])  # parameters in request body
  es = getESConn()
  pid = event['pathParameters']['id']
  proj = utility.getByUniqueField(es, projects_db, "_id", pid)  # project
  # create index with mapping if it does not exist already
  project.indexMapping(es, proj)

  # Add documents to created index
  # print("Adding a hash field to each case for duplicate-checking")
  for x in doc_list:  # generate a hash after ordering dict by key
    x = retrieve.add_vector_fields(proj['attributes'], x)  # add vectors to Semantic USE fields
    x = retrieve.add_lowercase_fields(proj['attributes'], x)  # use lowercase values for EqualIgnoreCase fields
    x['hash__'] = str(hashlib.md5(json.dumps(OrderedDict(sorted(x.items()))).encode('utf-8')).digest())  # case hash for easy detection of duplicates
  # print("Attempting to index the list of docs using helpers.bulk()")
  resp = helpers.bulk(es, doc_list, index=proj['casebase'], doc_type="_doc")

  # Indicate that the project has a casebase
  # print("Casebase added. Attempting to update project detail. Set hasCasebase => True")
  proj['hasCasebase'] = True
  source_to_update = {'doc': proj}
  # print(source_to_update)
  res = es.update(index=projects_db, id=pid, body=source_to_update)
  # print(res)

  # create the ontology similarity if specified as part of project attributes (can be a lengthy operation for mid to large ontologies!)
  for attrib in proj['attributes']:
    if attrib['type'] == "Ontology Concept" and attrib.get('similarity') is not None and attrib.get('options') is not None and retrieve.checkOntoSimilarity(pid + "_ontology_" + attrib['options'].get('name'))['statusCode'] != 200:
      sim_method = 'san' if attrib['similarity'] == 'Feature-based' else 'wup'
      retrieve.setOntoSimilarity(pid + "_ontology_" + attrib['options'].get('name'), attrib['options'].get('sources'), relation_type=attrib['options'].get('relation_type'), root_node=attrib['options'].get('root'), similarity_method=sim_method)

  response = {
    "statusCode": 201,
    "headers": headers,
    "body": json.dumps(resp)
  }
  return response


# except ValueError:
#   print("Unexpected data type encountered")
# except:
#   print("An error occurred while trying to index updated cases")

def remove_case(event, context=None):
  """
  End-point: Update operation for an existing case.
  """
  statusCode = 200
  params = json.loads(event['body'])  # parameters in request body
  casebase = params.get('projectId', None)  # name of casebase
  case = params.get('caseId', None)

  if casebase is None or case is None:
    result = "Details of the case to be removed are missing."
    statusCode = 400
  else:
    es = getESConn()
    result = es.delete(index=casebase, id=case)

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
  index_name = proj['casebase']
  res = project.indexMapping(es, proj)

  # Indicate that the project has a casebase (empty)
  # print("Casebase added. Attempting to update project detail. Set hasCasebase => True")
  proj['hasCasebase'] = True
  source_to_update = {'doc': proj}
  res = es.update(index=projects_db, id=pid, body=source_to_update)
  # print(res)

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
  result = {'recommended': {}, 'bestK': []}
  es = getESConn()  # es connection
  # query["query"]["bool"]["should"].append(queryFnc)
  queryAdded = False
  params = json.loads(event['body'])  # parameters in request body
  # print(params)
  queryFeatures = params.get('data')
  addExplanation = params.get('explanation')
  proj = params.get('project')
  if proj is None:
    projId = params.get('projectId')  # name of casebase
    proj = utility.getByUniqueField(es, projects_db, "_id", projId)

  proj_attributes = proj['attributes']
  globalSim = params['globalSim']  # not used as default aggregation is a weighted sum of local similarity values
  k = params['topk']
  query = {"query": {"bool": {"should": []}}}
  query["size"] = int(k)  # top k results
  for entry in queryFeatures:
    if ('value' in entry) and entry['value'] is not None and "" != entry['value'] and int(
            entry.get('weight', 0)) > 0 and entry['similarity'] != "None":
      queryAdded = True
      field = entry['name']
      similarityType = entry['similarity']
      options = retrieve.get_attribute_by_name(proj['attributes'], field).get('options', None)
      # print(options)
      # fieldType = entry['type']
      # use lowercase when field is specified as case-insensitive
      value = entry['value']
      weight = entry['weight']
      # isProblem = entry['unknown']
      # strategy = entry['strategy']

      qfnc = retrieve.getQueryFunction(proj['id__'], field, value, weight, similarityType, options)
      query["query"]["bool"]["should"].append(qfnc)

  if not queryAdded:  # retrieval all (up to k) if not query was added
    query["query"]["bool"]["should"].append(retrieve.MatchAll())
  # perform retrieval
  counter = 0
  res = es.search(index=proj['casebase'], body=query, explain=addExplanation)
  for hit in res['hits']['hits']:
    # print(hit)
    entry = hit['_source']
    entry.pop('hash__', None)  # remove hash field and value
    entry = retrieve.remove_vector_fields(proj_attributes, entry)  # remove vectors from Semantic USE fields
    if counter == 0:
      result['recommended'] = copy.deepcopy(entry)
    # entry['id__'] = hit['_id'] # using 'id__' to track this case (this is removed during an update operation)
    entry['score__'] = hit['_score']  # removed during an update operation
    result['bestK'].append(entry)
    if addExplanation:  # if retrieval needs an explanation included
      # entry['match_explanation'] = retrieve.explain_retrieval(es, proj['casebase'], query, hit['_id'], hit['matched_queries'])
      entry['match_explanation'] = retrieve.get_explain_details(hit['_explanation'])
    counter += 1

  # Recommend: Get the recommended result using chosen reuse strategies for unknown attribute values and
  # keep known attribute values (query) supplied
  if counter > 0:
    for entry in queryFeatures:
      if not entry['unknown'] and ('value' in entry) and entry['value'] is not None and "" != entry[
        'value']:  # copy known values
        result['recommended'][entry['name']] = entry['value']
      if entry.get('similarity') is not None and entry['unknown'] and entry[
        'strategy'] != "Best Match":  # use reuse strategies for unknown fields
        if entry['strategy'] == "Maximum":
          result['recommended'][entry['name']] = max(d[entry['name']] for d in result['bestK'])
        if entry['strategy'] == "Minimum":
          result['recommended'][entry['name']] = min(d[entry['name']] for d in result['bestK'])
        if entry['strategy'] == "Mean":
          result['recommended'][entry['name']] = np.mean([x[entry['name']] for x in result['bestK']])
        if entry['strategy'] == "Median":
          result['recommended'][entry['name']] = np.median([x[entry['name']] for x in result['bestK']])
        if entry['strategy'] == "Mode":
          result['recommended'][entry['name']] = statistics.mode([x[entry['name']] for x in result['bestK']])
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
  # reuse logic here

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
  result = {}
  # retain logic here
  statusCode = 201
  params = json.loads(event['body'])  # parameters in request body
  proj = params.get('project')
  es = getESConn()
  if proj is None:
    projId = params.get('projectId')  # name of casebase
    proj = utility.getByUniqueField(es, projects_db, "_id", projId)

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
  case_id = new_case.get('id')  # check for optional id in case description
  new_case = retrieve.add_vector_fields(proj['attributes'], new_case)  # add vectors to Semantic USE fields
  new_case['hash__'] = str(hashlib.md5(json.dumps(OrderedDict(sorted(new_case.items()))).encode('utf-8')).digest())

  if not proj['retainDuplicateCases'] and utility.indexHasDocWithFieldVal(es, index=proj['casebase'], field='hash__',
                                                                          value=new_case['hash__']):
    result = "The case already exists in the casebase"
    statusCode = 400
  else:
    if case_id is None:
      result = es.index(index=proj['casebase'], body=new_case)
    else:
      result = es.index(index=proj['casebase'], body=new_case, id=case_id)

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
