import base64
import datetime
import hashlib
import hmac
import json
import re
import time
import requests

import config as cfg
from logger_config import logger

# Optional imports for LLM providers
try:
  from openai import OpenAI
except ImportError:
  OpenAI = None


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
  config['attributeOptions'].append({'type': 'String',
                                     'similarityTypes': ['Equal', 'EqualIgnoreCase', 'BM25', 'Semantic USE', 'Semantic SBERT', 'Semantic AnglE Matching', 'Semantic AnglE Retrieval', 'None'], 
                                     'reuseStrategy': ['NN value'],
                                     'filterOptions': ['None', '=']
                                     })
  config['attributeOptions'].append({'type': 'Integer',
                                     'similarityTypes': ['Equal', 'Nearest Number', 'McSherry More', 'McSherry Less',
                                                         'INRECA More', 'INRECA Less', 'Interval', 'None'],
                                     'reuseStrategy': ['NN value', 'Maximum', 'Minimum', 'Mean', 'Median', 'Mode'],
                                     'filterOptions': ['None', '=', '>', '>=', '<', '<=']
                                     })
  config['attributeOptions'].append({'type': 'Float',
                                     'similarityTypes': ['Equal', 'Nearest Number', 'McSherry More', 'McSherry Less',
                                                         'INRECA More', 'INRECA Less', 'Interval', 'None'],
                                     'reuseStrategy': ['NN value', 'Maximum', 'Minimum', 'Mean', 'Median'],
                                     'filterOptions': ['None', '=', '>', '>=', '<', '<=']
                                     })
  config['attributeOptions'].append({'type': 'Categorical',
                                     'similarityTypes': ['Equal', 'EqualIgnoreCase', 'Table', 'EnumDistance', 'None'],
                                     'reuseStrategy': ['NN value'],
                                     'filterOptions': ['None', '=']
                                     })
  config['attributeOptions'].append({'type': 'Boolean',
                                     'similarityTypes': ['Equal', 'None'],
                                     'reuseStrategy': ['NN value', 'Majority', 'Minority'],
                                     'filterOptions': ['None', '=']
                                     })
  config['attributeOptions'].append({'type': 'Date',
                                     'similarityTypes': ['Nearest Date', 'None'], 
                                     'reuseStrategy': ['NN value'],
                                     'filterOptions': ['None', '=', '>', '>=', '<', '<=']
                                     })
  config['attributeOptions'].append({'type': 'Array',
                                     'similarityTypes': ['Jaccard', 'Array SBERT', 'Query Intersection', 'Cosine', 'None'],
                                     'reuseStrategy': ['NN value'],
                                     'filterOptions': ['None']
                                     })
  config['attributeOptions'].append({'type': 'Location',
                                     'similarityTypes': ['Nearest Location', 'None'], 
                                     'reuseStrategy': ['NN value'],
                                     'filterOptions': ['None']
                                     })
  config['attributeOptions'].append({'type': 'Ontology Concept',
                                     'similarityTypes': ['Path-based', 'Feature-based', 'None'], 
                                     'reuseStrategy': ['NN value'],
                                     'filterOptions': ['None', '=']
                                     })
  config['attributeOptions'].append({'type': 'Object', 
                                     'similarityTypes': ['None'],
                                     'reuseStrategy': ['NN value'],
                                     'filterOptions': ['None']
                                     })
  # print(config)
  time.sleep(0.2) # wait before index create finishes 
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


# ============================================================================
# LLM Provider Support Functions
# ============================================================================

def call_llm_openai(prompt, max_tokens=1024):
  """
  Call OpenAI API using the official Python client.
  Supports OpenAI, Azure OpenAI, and compatible endpoints.
  
  Args:
    prompt: The user prompt to send to the LLM
    max_tokens: Maximum tokens in response
    
  Returns:
    Response text from LLM, or error message if failed
  """
  try:
    if OpenAI is None:
      return "OpenAI client library not installed. Install with: pip install openai"
    
    # Initialize client
    client_kwargs = {
      'api_key': cfg.llm.get('api_key')
    }
    logger.info(f"Creating OpenAI client with API key: {client_kwargs['api_key'][:5]}...")  
    
    # Support custom base URL for Azure OpenAI or compatible endpoints
    if cfg.llm.get('url'):
      client_kwargs['base_url'] = cfg.llm.get('url')
      logger.info(f"Using custom base URL for LLM: {cfg.llm.get('url')}")

    # print("Prompt: ")
    # print(json.dumps(prompt))
    # print("-------------------")
    
    if cfg.llm.get('url'):
      client = OpenAI(
        api_key=cfg.llm.get('api_key'),
        base_url=cfg.llm.get('url')
      )
    else:
      client = OpenAI(
        api_key=cfg.llm.get('api_key')
      )
    
    # Call the API
    response = client.responses.create(
      model=cfg.llm.get('model'),
      input=prompt
    )
    
    # Extract response text
    if response.output and len(response.output) > 0:
      return response.output[0].content[0].text
    else:
      return "No response from OpenAI"
      
  except Exception as e:
    logger.error(f"Exception calling OpenAI: {e}")
    return f"Exception calling LLM: {str(e)}"


def call_llm_anthropic(prompt, max_tokens=1024):
  """
  Call Anthropic Claude API.
  
  Args:
    prompt: The user prompt to send to the LLM
    max_tokens: Maximum tokens in response
    
  Returns:
    Response text from LLM, or error message if failed
  """
  try:
    headers_auth = {
      'x-api-key': cfg.llm.get('api_key'),
      'anthropic-version': '2023-06-01',
      'Content-Type': 'application/json'
    }
    payload = {
      "model": cfg.llm.get('model'),
      "max_tokens": max_tokens,
      "messages": [
        {"role": "user", "content": prompt}
      ]
    }
    
    response = requests.post(cfg.llm.get('url'), headers=headers_auth, json=payload, timeout=30)
    
    if response.ok:
      data = response.json()
      if 'content' in data and len(data['content']) > 0:
        return data['content'][0]['text']
    else:
      logger.error(f"Anthropic call failed: {response.status_code} {response.text}")
      return f"LLM call failed: {response.status_code}"
  except Exception as e:
    logger.error(f"Exception calling Anthropic: {e}")
    return f"Exception calling LLM: {str(e)}"


def call_llm_ollama(prompt, max_tokens=1024):
  """
  Call local Ollama instance.
  
  Args:
    prompt: The user prompt to send to the LLM
    max_tokens: Maximum tokens in response
    
  Returns:
    Response text from LLM, or error message if failed
  """
  try:
    payload = {
      "model": cfg.llm.get('model'),
      "prompt": prompt,
      "stream": False
    }
    
    response = requests.post(cfg.llm.get('url'), json=payload, timeout=60)
    
    if response.ok:
      data = response.json()
      return data.get('response', '')
    else:
      logger.error(f"Ollama call failed: {response.status_code} {response.text}")
      return f"LLM call failed: {response.status_code}"
  except Exception as e:
    logger.error(f"Exception calling Ollama: {e}")
    return f"Exception calling LLM: {str(e)}"


def call_llm_huggingface(prompt, max_tokens=1024):
  """
  Call Hugging Face Inference API.
  
  Args:
    prompt: The user prompt to send to the LLM
    max_tokens: Maximum tokens in response
    
  Returns:
    Response text from LLM, or error message if failed
  """
  try:
    headers_auth = {
      'Authorization': f"Bearer {cfg.llm.get('api_key')}",
      'Content-Type': 'application/json'
    }
    payload = {
      "inputs": prompt,
      "parameters": {
        "max_length": max_tokens
      }
    }
    
    response = requests.post(cfg.llm.get('url'), headers=headers_auth, json=payload, timeout=30)
    
    if response.ok:
      data = response.json()
      if isinstance(data, list) and len(data) > 0 and 'generated_text' in data[0]:
        return data[0]['generated_text']
    else:
      logger.error(f"Hugging Face call failed: {response.status_code} {response.text}")
      return f"LLM call failed: {response.status_code}"
  except Exception as e:
    logger.error(f"Exception calling Hugging Face: {e}")
    return f"Exception calling LLM: {str(e)}"


def call_llm(prompt, max_tokens=1024):
  """
  Route LLM call to appropriate provider based on configuration.
  
  Supported providers:
    - 'openai': OpenAI API (or compatible endpoints like Azure OpenAI, local servers)
    - 'anthropic': Anthropic Claude API
    - 'ollama': Local Ollama instance
    - 'huggingface': Hugging Face Inference API
  
  Args:
    prompt: The user prompt to send to the LLM
    max_tokens: Maximum tokens in response (default: 1024)
    
  Returns:
    Response text from LLM, or error message if call failed
  """
  provider = cfg.llm.get('provider', 'openai').lower()
  api_key = cfg.llm.get('api_key')
  
  # Check if provider is configured with API key
  if not api_key and provider != 'ollama':
    error_msg = f"No LLM provider configured or API key missing for provider: {provider}"
    logger.warning(error_msg)
    return error_msg
  
  if provider == 'openai':
    return call_llm_openai(prompt, max_tokens)
  elif provider == 'anthropic':
    return call_llm_anthropic(prompt, max_tokens)
  elif provider == 'ollama':
    return call_llm_ollama(prompt, max_tokens)
  elif provider == 'huggingface':
    return call_llm_huggingface(prompt, max_tokens)
  else:
    error_msg = f"Unknown LLM provider: {provider}"
    logger.error(error_msg)
    return error_msg
