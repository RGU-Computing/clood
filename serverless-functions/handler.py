import json
import copy
from timeit import default_timer as timer
from elasticsearch import Elasticsearch, helpers, RequestsHttpConnection
import requests
from requests_aws4auth import AWS4Auth
# imports for hash - to test for unique records
import hashlib
from collections import OrderedDict
# imports for reuse operations (using both libs increases overall project size by ~20MB)
import numpy as np
import statistics
import config as cfg

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

es = Elasticsearch(
  hosts=[{'host': host, 'port': 443}],
  http_auth=AWS4Auth(access_key, secret_key, region, 'es'),
  use_ssl=True,
  verify_certs=True,
  connection_class=RequestsHttpConnection
)


# main function of your lambda

def all_projects(event, context=None):
  """
  End-point: Retrieves all projects
  """
  result = []
  # retrieve if ES index does exist
  if es.indices.exists(index=projects_db):
    query = {}
    query['query'] = {}
    query['query']['match_all'] = {}
    
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
  End-point: Retrieves a project
  """
  pid = event['pathParameters']['id']
  # retrieve if ES index does exist
  result = getByUniqueField(projects_db, "_id", pid)
  
  response = {
    "statusCode": 200,
    "headers": headers,
    "body": json.dumps(result)
  }
  return response


def new_project(event, context=None):
  """
  End-point: Creates a new project
  """
  result = {}
  statusCode = 201
  proj = json.loads(event['body'])  # parameters in request body
  # create ES index for Projects if it does not exist
  if not es.indices.exists(index=projects_db):
    project_mapping = {
      "mappings": {
        "properties": {
          "name": { "type": "text" },
          "description": { "type": "text" },
          "casebase": { "type": "text" },
          "hasCasebase": { "type": "boolean" },
          "retainDuplicateCases": { "type": "boolean" },
          "attributes": {
            "type": "nested",
            "properties": {
              "name": { "type": "keyword" },
              "type": { "type": "keyword" },
              "similarity": { "type": "keyword" }
            }
          }
        }
      }
    }
    es.indices.create(index=projects_db, body=project_mapping)
    # create config db if it does not exist
    createOrUpdateGlobalConfig()
    
  if 'casebase' not in proj or "" == proj['casebase'] or "" == proj['name']:
    result = "A new project has to specify a name and a casebase."
    statusCode = 400
  elif indexHasDocWithFieldVal(index=projects_db, field='casebase', value=proj['casebase']): # (index, field, value)
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
  # delete casebase
  proj = getByUniqueField(projects_db, "_id", pid) # get project
  casebase = proj['casebase']
  es.indices.delete(index=casebase, ignore=[400, 404])  # delete index if it exists
  # delete project
  res = es.delete(index=projects_db, id=pid)
  print(res)
  
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
  pid = event['pathParameters']['id']
  proj = getByUniqueField(projects_db, "_id", pid) # project
  index_name = proj['casebase']
  # create index with mapping if it does not exist already
  indexMapping(proj)
  
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
  pid = event['pathParameters']['id']
  proj = getByUniqueField(projects_db, "_id", pid) # project
  index_name = proj['casebase']
  res = indexMapping(proj)
  
  # Indicate that the project has a casebase (empty)
  print("Casebase added. Attempting to update project detail. Set hasCasebase => True")
  proj['hasCasebase'] = True
  source_to_update = { 'doc': proj }
  print(source_to_update)
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
  query = { "query": { "match_all": {} } }
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
  res = createOrUpdateGlobalConfig(json.loads(event['body']))
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
  End-point: Completes the retrieval step of the CBR cycle
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
      qfnc = getQueryFunction(field, value, weight, similarityType)
      query['query']['bool']['should'].append(qfnc)

  if not queryAdded: # retrieval all (up to k) if not query was added
    query['query']['bool']['should'].append(MatchAll())
  print(query)
  # perform retrieval
  counter = 0
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
  
  # Reuse: Get the recommended result using chosen reuse strategies for unknown attribute values and keep known attribute values supplied
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


def cbr_retain(event, context=None):
  """
  End-point: Completes the retain step of the CBR cycle by added a case to the casebase.
  To consider: Check for uniqueness here or sufficient to do so on the frontend?
  """
  statusCode = 201
  params = json.loads(event['body'])  # parameters in request body
  print(params)
  new_case = params['data']
  new_case['hash__'] = str(hashlib.md5(json.dumps(OrderedDict(sorted(new_case.items()))).encode('utf-8')).digest())
  proj = params['project']
  
  if not proj['retainDuplicateCases'] and indexHasDocWithFieldVal(index=proj['casebase'], field='hash__', value=new_case['hash__']):
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


def indexHasDocWithFieldVal(index, field, value):
  query = { "query": { "term": { field : value } } }
  res = es.search(index=index, body=query)
  return res['hits']['total']['value'] > 0
  
  
def createOrUpdateGlobalConfig(globalConfig=None):
  """
  Create or update the global configuration. The configuration resides in its own index and is the only document in it.
  The document's id is not tracked since it's the only document in the index and will not be updated often.
  """
  result = True
  if not es.indices.exists(index=config_db): # create index if it does not exist and add the default configuration
    res1 = es.indices.create(index=config_db) # create index
    print("Adding global configuration to ES.")
    config = {}
    config['attributeOptions'] = []
    config['attributeOptions'].append({ 'type': 'String', 'similarityTypes': ['Equal', 'EqualIgnoreCase', 'BM25', 'Semantic USE', 'None'], 'reuseStrategy': ['Best Match'] })
    config['attributeOptions'].append({ 'type': 'Integer', 'similarityTypes': ['Equal', 'McSherry More', 'McSherry Less', 'INRECA More', 'INRECA Less','Interval', 'None'], 'reuseStrategy': ['Best Match', 'Maximum', 'Minimum', 'Mean', 'Median', 'Mode'] })
    config['attributeOptions'].append({ 'type': 'Float', 'similarityTypes': ['Equal', 'McSherry More', 'McSherry Less', 'INRECA More', 'INRECA Less','Interval', 'None'], 'reuseStrategy': ['Best Match', 'Maximum', 'Minimum', 'Mean', 'Median'] })
    config['attributeOptions'].append({ 'type': 'Boolean', 'similarityTypes': ['Equal', 'None'], 'reuseStrategy': ['Best Match', 'Maximum', 'Minimum', 'Mean', 'Median'] })
    config['attributeOptions'].append({ 'type': 'Date', 'similarityTypes': ['ClosestDate', 'None'], 'reuseStrategy': ['Best Match'] })
    config['attributeOptions'].append({ 'type': 'Enum', 'similarityTypes': ['EnumDistance', 'None'], 'reuseStrategy': ['Best Match'] })
    print(config)
    res2 = es.index(index=config_db, body=config)
    result = False if not res2['_id'] else True
    if globalConfig is not None: # update the configuration if data is supplied
      # get config id
      query = { "query": { "match_all": {} } }
      res3 = es.search(index=config_db, body=query) 
      if (res3['hits']['total']['value'] > 0): # expects 1 document
        cid = res3['hits']['hits'][0]['_id'] # get id of config doc
        # update using supplied data
        source_to_update = {}
        source_to_update['doc'] = globalConfig 
        print(source_to_update)
        res4 = es.update(index=projects_db, id=cid, body=source_to_update)
        result = False if not res4['_id'] else True
  return result
    

def indexMapping(project):
  """
  Creates mapping for for a [project's] index.
  """
  index_name = project['casebase']
  res = 'Index already created or could not create index'
  if not es.indices.exists(index=index_name):
    print("Casebase does not exist. Creating casebase index mapping...")
    mapping = {} # create mapping
    mapping['mappings'] = {}
    mapping['mappings']['properties'] = {}
    for attrib in project['attributes']:
      mapping['mappings']['properties'].update({ attrib['name'] : getMappingFrag(attrib['type'], attrib['similarity']) })
    mapping['mappings']['properties'].update({ 'hash__' : { 'type': 'keyword' } }) # keeps hash of entry
    print(mapping)
    print("Creating casebase index...")
    res = es.indices.create(index=index_name, body=mapping)
    if res['acknowledged']: # update project to indicate that a casebase has been created (ES can add but not update mappings)
      print("Index created for casebase, " + project['name'])
  return res
  

def getMappingFrag(attrType, simMetric):
  """
  Generate mapping fragment for indexing document fields using Elasticsearch Reference v7.6.
  """
  res = {}
  if attrType == "Semantic":
    res['properties'] = { "name": { "type": "text" }, "rep": { "type": "dense_vector", "dims": 512 } } # dimension for universal sentence encoder. May require passing in as parameter
  elif attrType == "String" and not (simMetric == "Equal"):
    res['type'] = "text"
  elif attrType == "Boolean":
    res['type'] = "boolean"
  elif attrType == "Integer":
    res['type'] = "integer"
  elif attrType == "Float":
    res['type'] = "float"
  elif attrType == "Date":
    res['type'] = "keyword"
  elif attrType == "NativeDate":
    res['type'] = "date"
    res['format'] = "dd-MM-yyyy||dd-MM-yyyy HH:mm:ss||yyyy-MM-dd||yyyy-MM-dd HH:mm:ss||epoch_millis"
  elif attrType == "Autocomplete":
    res['type'] = "search_as_you_type"
  elif attrType == "Location":
    res['type'] = "geo_point"
  else:
    res['type'] = "keyword"
  return res


def getQueryFunction(caseAttrib, queryValue, weight, simMetric, *args, **kwargs):
  """
  Determine query function to use base on attribute specification and retrieval features
  """
  # minVal = kwargs.get('minVal', None) # optional parameter, minVal (name 'minVal' in function params when calling function e.g. minVal=5)
  if simMetric == "Equal":
    return Exact(caseAttrib, queryValue, weight)
  else:
    return MostSimilar(caseAttrib, queryValue, weight)
  

def getByUniqueField(index, field, value):
  """
  Retrieve an item from specified index using a unique field
  """
  result = {}
  # retrieve if ES index does exist
  query = {}
  query['query'] = {}
  query['query']['terms'] = {}
  query['query']['terms'][field] = []
  query['query']['terms'][field].append(value)
  print(query)
  res = es.search(index=projects_db, body=query)
  if (res['hits']['total']['value'] > 0):
    entry = res['hits']['hits'][0]['_source']
    entry['id__'] = res['hits']['hits'][0]['_id']
    result = entry
  return result


def test(event, context):
  body = {
    "message": "Go Serverless with CloodCBR! Your function executed successfully!",
    "input": event
  }

  response = {
    "statusCode": 200,
    "headers": headers,
    "body": json.dumps(body)
  }

  return response


# SIMILARITY FUNCTIONS. Requires field name and set of functions-specific parameters

def McSherryLessIsBetter(caseAttrib, queryValue, maxValue, minValue, weight):
  """
  Returns the similarity of two numbers following the McSherry - Less is better formula. queryVal is not used!
  """
  try:
    queryValue = float(queryValue)
    # build query string
    queryFnc = {
      "function_score": {
        "query": {
          "match_all": {}
        },
        "script_score": {
          "script": {
            "source": "(params.max - doc[caseAttrib].value) / (params.max - params.min)",
            "params": {
              "max": maxValue,
              "min": minValue
            }
          }
        },
        "boost": weight,
        "_name": "mcsherryless"
      }
    }
    return queryFnc

  except ValueError:
    print("McSherryLessIsBetter() is only applicable to numbers")


def McSherryMoreIsBetter(caseAttrib, queryValue, maxValue, minValue, weight):
  """
  Returns the similarity of two numbers following the McSherry - More is better formula. queryVal is not used!
  """
  try:
    queryValue = float(queryValue)
    # build query string
    queryFnc = {
      "function_score": {
        "query": {
          "match_all": {}
        },
        "script_score": {
          "script": {
            "source": "1 - ( (params.max - doc[caseAttrib].value) / (params.max - params.min) )",
            "params": {
              "max": maxValue,
              "min": minValue
            }
          }
        },
        "boost": weight,
        "_name": "mcsherrymore"
      }
    }
    return queryFnc

  except ValueError:
    print("McSherryMoreIsBetter() is only applicable to numbers")


def InrecaLessIsBetter(caseAttrib, queryValue, maxValue, jump, weight):
  """
  Returns the similarity of two numbers following the INRECA - Less is better formula.
  """
  try:
    queryValue = float(queryValue)
    # build query string
    queryFnc = {
      "function_score": {
        "query": {
          "match_all": {}
        },
        "script_score": {
          "script": {
            "source": "if (doc[caseAttrib].value <= params.queryValue) { return 1 } if (doc[caseAttrib].value >= params.maxValue) { return 0 } return params.jump * (params.maxValue - doc[caseAttrib].value) / (params.maxValue - params.queryValue)",
            "params": {
              "jump": jump,
              "maxValue": maxValue,
              "queryValue": queryValue
            }
          }
        },
        "boost": weight,
        "_name": "inrecaless"
      }
    }
    return queryFnc

  except ValueError:
    print("InrecaLessIsBetter() is only applicable to numbers")


def InrecaMoreIsBetter(caseAttrib, queryValue, jump, weight):
  """
  Returns the similarity of two numbers following the INRECA - More is better formula.
  """
  try:
    queryValue = float(queryValue)
    # build query string
    queryFnc = {
      "function_score": {
        "query": {
          "match_all": {}
        },
        "script_score": {
          "script": {
            "source": "if (doc[caseAttrib].value <= params.queryValue) { return 1 } return params.jump * (1 - ((params.queryValue - doc[caseAttrib].value) / params.queryValue))",
            "params": {
              "jump": jump,
              "queryValue": queryValue
            }
          }
        },
        "boost": weight,
        "_name": "inrecamore"
      }
    }
    return queryFnc

  except ValueError:
    print("InrecaMoreIsBetter() is only applicable to numbers")


def Interval(caseAttrib, queryValue, interval, weight):
  """
  Returns the similarity of two numbers inside an interval.
  """
  try:
    queryValue = float(queryValue)
    # build query string
    queryFnc = {
      "function_score": {
        "query": {
          "match_all": {}
        },
        "script_score": {
          "script": {
            "params": {
              "interval": interval,
              "queryValue": queryValue
            },
            "source": "1 - ( Math.abs(params.queryValue - doc[caseAttrib].value) / params.interval )"
          }
        },
        "boost": weight,
        "_name": "interval"
      }
    }
    return queryFnc

  except ValueError:
    print("Interval() is only applicable to numbers")

#To test!!
def EnumDistance(caseAttrib, queryValue, arrayList, weight): # stores enum as array
  """
  Implements EnumDistance local similarity function. 
  Returns the similarity of two enum values as their distance sim(x,y) = |ord(x) - ord(y)|.
  """
  try:
    queryValue = float(queryValue)
    # build query string
    queryFnc = {
      "function_score": {
        "query": {
          "match_all": {}
        },
        "script_score": {
          "script": {
            "params": {
              "lst": arrayList,
              "queryValue": queryValue
            },
            "source": "1 - ( Math.abs(lst.indexOf(params.queryValue) - lst.indexOf(doc[caseAttrib].value)) / lst.length )"
          }
        },
        "boost": weight,
        "_name": "interval"
      }
    }
    return queryFnc

  except ValueError:
    print("Interval() is only applicable to numbers")


def Exact(caseAttrib, queryValue, weight):
  """
  Exact matches for fields defined as equal. Attributes that use this are indexed using 'keyword'.
  """
  # build query string
  query = {
    "term": {
      caseAttrib: {
        "value": queryValue,
        "boost": weight,
        "_name": "exact"
      }
    }
  }
  return query


def MostSimilar(caseAttrib, queryValue, weight):
  """
  Most similar matches using ES default (works for all attribute types). Default similarity for strings and exact match for other types.
  """
  # build query string
  query = {
    "match": {
      caseAttrib: {
        "query": queryValue,
        "boost": weight,
        "_name": "mostsimilar"
      }
    }
  }
  return query


def ClosestDate(caseAttrib, queryValue, weight, maxDate, minDate): # format 'dd-MM-yyyy' e.g. '01-02-2020'
  """
  Find the documents whose attribute values have the closest date to the query date. The date field field is indexed as 'keyword' to enable use of this similarity metric.
  """
  queryValue = float(queryValue)
  # build query string
  queryFnc = {
    "script_score": {
			"query": {
		    	"match_all": {}
		    },
		    "script": {
		    	"params": {
					"weight": weight,
					"queryValue": queryValue,
					"oldestDate": minDate,
					"newestDate": maxDate
				},
		    	"source": "SimpleDateFormat sdf = new SimpleDateFormat('dd-MM-yyyy', Locale.ENGLISH); doc[caseAttrib].size()==0 ? 0 : (1 - Math.abs(sdf.parse(doc[caseAttrib].value).getTime() - sdf.parse(params.queryValue).getTime()) / ((sdf.parse(params.newestDate).getTime() - sdf.parse(params.oldestDate).getTime()) + 1)) * params.weight"
		    },
		    "_name": "closestdate"
		}
  }
  return queryFnc


def MatchAll():
  """
  Retrieve all documents. There is a 10,000 size limit for Elasticsearch query results! The Scroll API can be used to 
  retrieve more than 10,000. 
  """
  return { "match_all": {} }
