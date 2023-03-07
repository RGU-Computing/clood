import base64
import datetime
import hashlib
import hmac
import json
import re
import time

import config as cfg


def indexHasDocWithFieldVal(es, index, field, value):
  query = {"query": {"term": {field: value}}}
  res = es.search(index=index, body=query)
  return res['hits']['total']['value'] > 0


def createOrUpdateGlobalConfig(es, config_db="config", globalConfig=None):
  """
  Create or update the global configuration. The configuration resides in its own index and is the only document in it.
  The document's id is not tracked since it's the only document in the index and will not be updated often.
  """
  result = True
  # if not es.indices.exists(index=config_db): # create index if it does not exist and add the default configuration
  es.indices.delete(index=config_db, ignore=[400, 404])
  time.sleep(0.3)  # 0.3 sec wait
  es.indices.create(index=config_db)  # create index
  # print("Adding global configuration to ES.")
  config = {}
  config['attributeOptions'] = []
  config['attributeOptions'].append(
    {'type': 'String', 'similarityTypes': ['Equal', 'EqualIgnoreCase', 'BM25', 'Semantic USE', 'Semantic SBERT','Array', 'Array SBERT', 'None'],
     'reuseStrategy': ['Best Match']})
  config['attributeOptions'].append({'type': 'Integer',
                                     'similarityTypes': ['Equal', 'Nearest Number', 'McSherry More', 'McSherry Less',
                                                         'INRECA More', 'INRECA Less', 'Interval', 'Array', 'None'],
                                     'reuseStrategy': ['Best Match', 'Maximum', 'Minimum', 'Mean', 'Median', 'Mode']})
  config['attributeOptions'].append({'type': 'Float',
                                     'similarityTypes': ['Equal', 'Nearest Number', 'McSherry More', 'McSherry Less',
                                                         'INRECA More', 'INRECA Less', 'Interval', 'Array','None'],
                                     'reuseStrategy': ['Best Match', 'Maximum', 'Minimum', 'Mean', 'Median']})
  config['attributeOptions'].append({'type': 'Categorical',
                                     'similarityTypes': ['Equal', 'EqualIgnoreCase', 'Table', 'EnumDistance', 'Query Intersection', 'None'],
                                     'reuseStrategy': ['Best Match']})
  config['attributeOptions'].append({'type': 'Boolean', 'similarityTypes': ['Equal', 'None'],
                                     'reuseStrategy': ['Best Match', 'Maximum', 'Minimum', 'Mean', 'Median']})
  config['attributeOptions'].append(
    {'type': 'Date', 'similarityTypes': ['Nearest Date', 'None'], 'reuseStrategy': ['Best Match']})
  config['attributeOptions'].append(
    {'type': 'Location', 'similarityTypes': ['Nearest Location', 'None'], 'reuseStrategy': ['Best Match']})
  config['attributeOptions'].append(
    {'type': 'Ontology Concept', 'similarityTypes': ['Path-based', 'Feature-based', 'None'], 'reuseStrategy': ['Best Match']})
  config['attributeOptions'].append({'type': 'Object', 'similarityTypes': ['None'], 'reuseStrategy': ['Best Match']})
  # print(config)
  res2 = es.index(index=config_db, body=config)
  result = False if not res2['_id'] else True
  if globalConfig is not None:  # update the configuration if data is supplied
    # get config id
    query = {"query": {"match_all": {}}}
    res3 = es.search(index=config_db, body=query)
    if (res3['hits']['total']['value'] > 0):  # expects 1 document
      cid = res3['hits']['hits'][0]['_id']  # get id of config doc
      # update using supplied data
      source_to_update = {}
      source_to_update['doc'] = globalConfig
      # print(source_to_update)
      res4 = es.update(index=config_db, id=cid, body=source_to_update)
      result = False if not res4['_id'] else True
  return result


def getByUniqueField(es, index, field, value):
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
  #   print(query)
  res = es.search(index=index, body=query)
  if (res['hits']['total']['value'] > 0):
    entry = res['hits']['hits'][0]['_source']
    entry['id__'] = res['hits']['hits'][0]['_id']
    result = entry
  return result


def getIndexEntries(es, index, start=0, size=100):
  """
  Retrieve documents from specified index (100 documents by default).
  """
  result = []
  # retrieve if ES index does exist
  query = {}
  query['query'] = {"match_all": {}}
  query['from'] = start
  query['size'] = size
  # print(query)
  res = es.search(index=index, body=query)
  for entry in res['hits']['hits']:
    doc = entry['_source']
    doc['id__'] = entry['_id']
    result.append(doc)
  return result

def verifyToken(token):
  """
  Verify the token
  """
  result = False
  if token is not None:
    # regex JWT token
    JWTregex = r"^[A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.?[A-Za-z0-9-_.+/=]*$"
    if re.match(JWTregex, token):

      # split token into header, payload and signature
      tokenParts = (token.split('.'))

      # HMAC of sha256 hash of header and payload using secret key
      signature =  base64.b64encode(hmac.HMAC(cfg.SECRET.encode('utf-8'), (tokenParts[0] + '.' + tokenParts[1]).encode('utf-8'), hashlib.sha256).digest(),b"-_")
      signature = signature.replace(b'=', b'').decode("utf-8") # strip padding

      # compare the new signature with the provided signature
      if signature == tokenParts[2]:
        result = True
        # Check if the token has passed its expiry time
        payload = json.loads(base64.b64decode(tokenParts[1] + '=='))
        if float(payload['expiry']) < (time.time()):
          result = False

  return result

def generateToken(token):
  """
  Generate a token
  """
  result = None
  if token is not None and token['name'] is not None and token['expiry'] is not None:
    # get current time
    now = time.time()
    # create header
    header = {}
    header['alg'] = 'HS256'
    header['typ'] = 'JWT'
    # create payload
    payload = {}
    payload['name'] = token['name']
    if 'description' in token:
      payload['description'] = token['description']
    payload['expiry'] = token['expiry']

    # encode header and payload
    encodedHeader = base64.b64encode(json.dumps(header).encode('utf-8'),b"-_")
    encodedHeader = encodedHeader.replace(b'=', b'').decode("utf-8") # strip padding
    encodedPayload = base64.b64encode(json.dumps(payload).encode('utf-8'),b"-_")
    encodedPayload = encodedPayload.replace(b'=', b'').decode("utf-8") # strip padding

    # HMAC of sha256 hash of header and payload using secret key
    signature =  base64.b64encode(hmac.HMAC(cfg.SECRET.encode('utf-8'), (encodedHeader + '.' + encodedPayload).encode('utf-8'), hashlib.sha256).digest(),b"-_")
    signature = signature.replace(b'=', b'').decode("utf-8") # strip padding

    # create token
    result = encodedHeader + '.' + encodedPayload + '.' + signature

  return result