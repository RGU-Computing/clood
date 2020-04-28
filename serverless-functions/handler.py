import sys
import os
import json
import copy
import requests
from timeit import default_timer as timer
from elasticsearch import Elasticsearch, helpers, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
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
  esconn = Elasticsearch(
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
  if not es.indices.exists(index=projects_db):
    project_mapping = project.getProjectMapping()
    es.indices.create(index=projects_db, body=project_mapping)
    # create config db if it does not exist
    utility.createOrUpdateGlobalConfig(es, config_db=config_db)
    
  if 'casebase' not in proj or "" == proj['casebase'] or "" == proj['name']:
    result = "A new project has to specify a name and a casebase."
    statusCode = 400
  elif utility.indexHasDocWithFieldVal(es, index=projects_db, field='casebase', value=proj['casebase']): # (index, field, value)
    result = "Casebase already exists. Choose a different name for the casebase."
    statusCode = 400
  else:
    proj['attributes'] = []
    proj['hasCasebase'] = False
    print(proj)
    result = es.index(index=projects_db, body=proj)
    
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
  pid = event['pathParameters']['id']
  body = json.loads(event['body'])
  body.pop('id__', None) # remove id__ (was added to dict to use a plain structure)
  source_to_update = {}
  source_to_update['doc'] = body  # parameters in request body
  print(source_to_update)
  es = getESConn()
  res = es.update(index=projects_db, id=pid, body=source_to_update)
  print(res)
  
  response = {
    "statusCode": 201,
    "headers": headers,
    "body": json.dumps(res)
  }
  return response


def delete_project(event, context=None):
  """
  End-point: Deletes a project. Also deletes the project's casebase index if it exists.
  """
  pid = event['pathParameters']['id'] # project id
  es = getESConn()
  # delete casebase
  proj = utility.getByUniqueField(es, projects_db, "_id", pid) # get project
  casebase = proj['casebase']
  es.indices.delete(index=casebase, ignore=[400, 404])  # delete index if it exists
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
  doc_list = json.loads(event['body']) # parameters in request body
  es = getESConn()
  pid = event['pathParameters']['id']
  proj = utility.getByUniqueField(es, projects_db, "_id", pid) # project
  index_name = proj['casebase']
  # create index with mapping if it does not exist already
  project.indexMapping(es, proj)
  
  # Add documents to created index
  print("Adding a hash field to each case for duplicate-checking")
  for x in doc_list: # generate a hash after ordering dict by key
    x['hash__'] = str(hashlib.md5(json.dumps(OrderedDict(sorted(x.items()))).encode('utf-8')).digest())
  print("Attempting to index the list of docs using helpers.bulk()")
  resp = helpers.bulk(es, doc_list, index=proj['casebase'], doc_type="_doc")
  
  # Indicate that the project has a casebase
  print("Casebase added. Attempting to update project detail. Set hasCasebase => True")
  proj['hasCasebase'] = True
  source_to_update = { 'doc': proj }
  print(source_to_update)
  res = es.update(index=projects_db, id=pid, body=source_to_update)
  print(res)
  
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


def create_project_index(event, context=None):
  """
  End-point: Creates the mapping for an index if it does not exist.
  """
  es = getESConn()
  pid = event['pathParameters']['id']
  proj = utility.getByUniqueField(es, projects_db, "_id", pid) # project
  index_name = proj['casebase']
  res = project.indexMapping(es, proj)
  
  # Indicate that the project has a casebase (empty)
  print("Casebase added. Attempting to update project detail. Set hasCasebase => True")
  proj['hasCasebase'] = True
  source_to_update = { 'doc': proj }
  res = es.update(index=projects_db, id=pid, body=source_to_update)
  print(res)
  
  response = {
    "statusCode": 201,
    "headers": headers,
    "body": json.dumps(res)
  }
  return response
  

def get_config(event, context=None):
  """
  End-point: Retrieves configuration
  """
  # get config. configuration index has 1 document
  result = []
  es = getESConn()
  if not es.indices.exists(index=config_db): # create config db if it does not exist
    utility.createOrUpdateGlobalConfig(es, config_db=config_db)
  query = { "query": retrieve.MatchAll() }
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


def cbr_retrieve(event, context=None):
  """
  End-point: Completes the Retrieve step of the CBR cycle.
  """
  start = timer() # start timer
  result = { 'recommended': {}, 'bestK': [] }
  # query['query']['bool']['should'].append(queryFnc)
  queryAdded = False
  params = json.loads(event['body'])  # parameters in request body
  print(params)
  queryFeatures = params['data']
  proj = params['project']
  globalSim = params['globalSim']
  k = params['topk']
  query = { 'query': {'bool': {'should': []}} }
  query['size'] = int(k) # top k results
  for entry in queryFeatures:
    if ('value' in entry) and entry['value'] is not None and "" != entry['value'] and int(entry['weight']) > 0 and entry['similarityType'] != "None":
      queryAdded = True
      field = entry['field']
      # fieldType = entry['type']
      value = entry['value']
      weight = entry['weight']
      # isProblem = entry['unknown']
      # strategy = entry['strategy']
      similarityType = entry['similarityType']
      qfnc = retrieve.getQueryFunction(field, value, weight, similarityType)
      query['query']['bool']['should'].append(qfnc)

  if not queryAdded: # retrieval all (up to k) if not query was added
    query['query']['bool']['should'].append(retrieve.MatchAll())
  print(query)
  # perform retrieval
  counter = 0
  es = getESConn()
  res = es.search(index=proj['casebase'], body=query)
  for hit in res['hits']['hits']:
    entry = hit['_source']
    entry.pop('hash__', None) # remove hash field and value
    if counter == 0:
      result['recommended'] = copy.deepcopy(entry)
    # entry['id__'] = hit['_id'] # using 'id__' to track this case (this is removed during an update operation)
    entry['score__'] = hit['_score'] # removed during an update operation
    result['bestK'].append(entry)
    counter += 1
  
  # Recommend: Get the recommended result using chosen reuse strategies for unknown attribute values and keep known attribute values supplied
  if counter > 0:
    for entry in queryFeatures:
      if not entry['unknown'] and ('value' in entry) and entry['value'] is not None and "" != entry['value']: # copy known values
        result['recommended'][entry['field']] = entry['value']
      if entry['similarityType'] != "None" and entry['unknown'] and entry['strategy'] != "Best Match": # use reuse strategies for unknown fields
        if entry['strategy'] == "Maximum":
          result['recommended'][entry['field']] = max(d[entry['field']] for d in result['bestK'])
        if entry['strategy'] == "Minimum":
          result['recommended'][entry['field']] = min(d[entry['field']] for d in result['bestK'])
        if entry['strategy'] == "Mean":
          result['recommended'][entry['field']] = np.mean( [x[entry['field']] for x in result['bestK']] )
        if entry['strategy'] == "Median":
          result['recommended'][entry['field']] = np.median( [x[entry['field']] for x in result['bestK']] )
        if entry['strategy'] == "Mode":
          result['recommended'][entry['field']] = statistics.mode( [x[entry['field']] for x in result['bestK']] )
  
  end = timer() # end timer
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
  End-point: Completes the Retain step of the CBR cycle.
  """
  result = {}
  # retain logic here
  statusCode = 201
  params = json.loads(event['body'])  # parameters in request body
  print(params)
  new_case = params['data']
  new_case['hash__'] = str(hashlib.md5(json.dumps(OrderedDict(sorted(new_case.items()))).encode('utf-8')).digest())
  proj = params['project']
  es = getESConn()
  if not proj['retainDuplicateCases'] and project.indexHasDocWithFieldVal(es, index=proj['casebase'], field='hash__', value=new_case['hash__']):
    result = "The case already exists in the casebase"
    statusCode = 400
  else:
    result = es.index(index=proj['casebase'], body=new_case)
  
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
