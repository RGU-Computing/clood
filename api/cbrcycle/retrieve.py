# Retrieve functions
from datetime import datetime as dt
import math
import re
import time
import dateutil.parser
import requests
import json
import config as cfg


def getVector(text):
  """
  Calls an external service to get the 512 dimensional vector representation of a piece of text.
  """
  url = cfg.use_vectoriser
  res = requests.post(url, json={'text': text, 'access_key': cfg.vectoriser_access_key})
  res_dictionary = res.json()
  return res_dictionary['vectors']


def getVectorSemanticSBERT(text):
  """
  Calls an external service to get the 768 dimensional vector representation of a piece of text.
  """
  url = cfg.sbert_vectoriser
  res = requests.post(url, json={'text': text, 'access_key': cfg.vectoriser_access_key})
  res_dictionary = res.json()
  return res_dictionary['vectors']


def checkOntoSimilarity(ontology_id):
  """
  Calls an external service to check if an ontology based similarity measures exist.
  """
  # print('checkOntoSimilarity() =>', ontology_id)
  url = cfg.ontology_sim + '/status'
  res = requests.post(url, json={'ontologyId': ontology_id})
  resp = res.json()
  resp['statusCode'] = res.status_code
  return resp  #resp['statusCode'] = 200 if ontology exists and 404 otherwise


def getOntoSimilarity(ontology_id, key):
  """
  Calls an external service to get ontology based similarity values for concept comparisons.
  """
  # print('getOntoSimilarity() =>', ontology_id)
  url = cfg.ontology_sim + '/query'
  res = requests.post(url, json={'ontologyId': ontology_id, 'key': key})
  res_dictionary = res.json()
  return res_dictionary.get('map', {})


def setOntoSimilarity(ontology_id, ontology_sources, relation_type=None, root_node=None, similarity_method="wup"):
  """
  Calls an external service to create ontology based similarity values for concept comparisons.
  """
  # print('setOntoSimilarity() =>', ontology_id)
  url = cfg.ontology_sim + '/preload'
  body = {'ontologyId': ontology_id, 'sources': ontology_sources}
  if relation_type is not None and len(relation_type) > 0:
    body['relation_type'] = relation_type
  if root_node is not None and len(root_node) > 0:
    body['root_node'] = root_node
  body['similarity_method'] = similarity_method
  res = requests.post(url, json=body)
  return res.json()


def removeOntoIndex(ontology_id):
  """
  Calls an external service to remove an ontology index of similarity measures.
  """
  # print('removeOntoIndex() =>', ontology_id)
  url = cfg.ontology_sim + '/delete'
  body = {
    "ontologyId": ontology_id
  }
  try:
    res = requests.post(url, json=body)
    return res.json()
  except:
    print("Could not remove details for ontology with id " + ontology_id)
    return False


def add_vector_fields(attributes, data):
  """
  Expand data values to include vector fields.
  Transforms "x: val" to "x: {name: val, rep: vector(val)}"
  """
  for attrib in attributes:
    if attrib['similarity'] == 'Semantic USE':
      value = data.get(attrib['name'])
      if value is not None:
        newVal = {}
        newVal['name'] = value
        newVal['rep'] = getVector(value)
        data[attrib['name']] = newVal
    elif attrib['similarity'] == 'Semantic SBERT':
      value = data.get(attrib['name'])
      if value is not None:
        newVal = {}
        newVal['name'] = value
        newVal['rep'] = getVectorSemanticSBERT(value)
        data[attrib['name']] = newVal
  return data


def remove_vector_fields(attributes, data):
  """
  Flatten data values to remove vector fields.
  Transforms "x: {name: val, rep: vector(val)}" to "x: val"
  """
  for attrib in attributes:
    if attrib['similarity'] == 'Semantic USE' or attrib['similarity'] == 'Semantic SBERT':
      # print('data: ')
      # print(data)
      value = data.get(attrib['name'])
      if value is not None:
        data[attrib['name']] = value['name']
  return data


def add_lowercase_fields(attributes, data):
  """
  Change values for fields of EqualIgnoreCase to lowercase.
  Transforms "x: Val" to "x: val"
  """
  for attrib in attributes:
    if attrib['similarity'] == 'EqualIgnoreCase':
      value = data.get(attrib['name'])
      if value is not None:
        data[attrib['name']] = value.lower()
  return data


def get_attribute_by_name(attributes, attributeName):
  """
  Retrieves an attribute by name from list of attributes.
  """
  for attrib in attributes:
    if attrib['name'] == attributeName:
      return attrib
  return None


def explain_retrieval(es, index_name, query, doc_id, matched_queries):
  """
  End-point: Explain the scoring for a retrieved case.
  """
  expl = []
  # print(matched_queries)
  query.pop("size", None)  # request does not support [size]
  res = es.explain(index=index_name, body=query, id=doc_id, stored_fields="true")
  details = res["explanation"]["details"]
  # print(json.dumps(res, indent=4))

  for idx, x in enumerate(matched_queries):
    expl.append({x: details[idx]['value']})

  # print(expl)
  return expl


def get_explain_details(match_explanation):
  """
  Extracts the field names and local similarity values from explanations.
  Note: Could fail if the format of explanations change as it uses regex to extract field names. Skips explanation for
  a field if it cannot find the field name.
  """
  expl = []
  matchers = match_explanation["details"]  # at times the explanation is not in 'details' list!!
  if len(matchers) <= 1: # not more than one explanation then match attribute in the entire string
    txt = str(match_explanation)
    m0 = re.search("attrib=([a-zA-Z0-9_\-\s]+)",
                   txt)  # FRAGILE: relies on specific format for the explanation to include attribute name
    if m0:  # if field name is found
      expl.append({"field": m0.group(1), "similarity": match_explanation['value']})
  else:  # more than one explanation then iterate and match attributes
    for x in matchers:
      txt = str(x)
      m0 = re.search("attrib=([a-zA-Z0-9_\-\s]+)", txt)
      if m0:  # if field name is found
        expl.append({"field": m0.group(1), "similarity": x['value']})

  # print(expl)
  return expl


def get_min_max_values(es,casebase,attribute):
  query = {
    "aggs": {
      "max": { "max": { "field": attribute } },
      "min": { "min": { "field": attribute } }
      }
    }
  res = es.search(index=casebase, body=query, explain=False)
  if res['aggregations']['max']['value'] is None or res['aggregations']['min']['value'] is None:
    res['aggregations']['max']['value'] = 1
    res['aggregations']['min']['value'] = 0
  
  res = {"max": res["aggregations"]["max"]["value"], "min": res["aggregations"]["min"]["value"], "interval": res["aggregations"]["max"]["value"] - res["aggregations"]["min"]["value"]}

  return res


def update_attribute_options(es,proj,attrNames = []):
  #time.sleep(2) # wait for the operation to complete
  if not attrNames: # if no attributes specified, update all attributes
      attrNames = []
      for attr in proj['attributes']:
        attrNames.append(attr['name'])
  for attr in attrNames:
      for elem in proj['attributes']:
        if elem['name'] == attr:
          if elem['type'] == "Integer" or elem['type'] == "Float" or elem['type'] == "Date":
              res = get_min_max_values(es, proj['casebase'], attr)
              if 'options' in elem:
                if 'min' in elem['options']:
                  elem['options']['min'] = res['min']
                if 'max' in elem['options']:
                  elem['options']['max'] = res['max']
                  if elem['options']['max'] == elem['options']['min']:   # if min and max are the same, set max to min + 0.001
                    elem['options']['max'] += 0.001
                if 'interval' in elem['options']:
                  elem['options']['interval'] = res['interval']
                if 'nscale' in elem['options']:   # set scale to 10% of the interval (floats and integers)
                  elem['options']['nscale'] = res['interval']/10
                  elem['options']['nscale'] = 1 if elem['options']['nscale'] < 1 else elem['options']['nscale']   # if nscale is less than 1, set it to 1
                  elem['options']['ndecay'] = 0.9
                if 'dscale' in elem['options']:   # set scale to 10% of the interval (dates)
                  elem['options']['dscale'] = str(math.ceil((dt.fromtimestamp(res['max']/1000)-dt.fromtimestamp(res['min']/1000)).days/10)) + "d"   # if date scale is 0, set it to 1 day
                  elem['options']['dscale'] = elem['options']['dscale'].replace("0d","1d")
                  elem['options']['ddecay'] = 0.9
  result = es.update(index='projects', id=proj['id__'], body={'doc': proj}, filter_path="-_seq_no,-_shards,-_primary_term,-_version,-_type",refresh=True)
  return result


def getQueryFunction(projId, caseAttrib, queryValue, weight, simMetric, options):
  """
  Determine query function to use base on attribute specification and retrieval features.
  Add new query functions in the if..else statement as elif.
  """
  # minVal = kwargs.get('minVal', None) # optional parameter, minVal (name 'minVal' in function params when calling function e.g. minVal=5)
  if simMetric == "Equal":
    return Exact(caseAttrib, queryValue, weight)
  elif simMetric == "EqualIgnoreCase":
    queryValue = queryValue.lower()
    return Exact(caseAttrib, queryValue, weight)
  elif simMetric == "McSherry More":  # does not use the query value
    maxValue = options.get('max', 100.0) if options is not None else 100.0  # use 100 if no supplied max
    minValue = options.get('min', 0.0) if options is not None else 0.0  # use 0 if no supplied min
    return McSherryMoreIsBetter(caseAttrib, queryValue, maxValue, minValue, weight)
  elif simMetric == "McSherry Less":  # does not use the query value
    maxValue = options.get('max', 100.0) if options is not None else 100.0  # use 100 if no supplied max
    minValue = options.get('min', 0.0) if options is not None else 0.0  # use 0 if no supplied min
    return McSherryLessIsBetter(caseAttrib, queryValue, maxValue, minValue, weight)
  elif simMetric == "INRECA More":
    jump = options.get('jump', 1.0) if options is not None else 1.0  # use 1 if no supplied jump
    return InrecaMoreIsBetter(caseAttrib, queryValue, jump, weight)
  elif simMetric == "INRECA Less":
    jump = options.get('jump', 1.0) if options is not None else 1.0  # use 1 if no supplied jump
    maxValue = options.get('max', 100.0) if options is not None else 100.0  # use 100 if no supplied max
    return InrecaLessIsBetter(caseAttrib, queryValue, maxValue, jump, weight)
  elif simMetric == "Interval":
    maxValue = options.get('max', 100.0) if options is not None else 100.0  # use 100 if no supplied max
    minValue = options.get('min', 100.0) if options is not None else 100.0  # use 100 if no supplied min
    return Interval(caseAttrib, queryValue, maxValue, minValue, weight)
  elif simMetric == "Semantic USE" and cfg.use_vectoriser is not None:
    return USE(caseAttrib, getVector(queryValue), weight)
  elif simMetric == "Semantic SBERT" and cfg.sbert_vectoriser is not None:
    return Semantic_SBERT(caseAttrib, getVectorSemanticSBERT(queryValue), weight)
  elif simMetric == "Nearest Date":
    scale = options.get('dscale', '365d') if options is not None else '365d'
    decay = options.get('ddecay', 0.999) if options is not None else 0.999
    return ClosestDate(caseAttrib, queryValue, weight, scale, decay)
  elif simMetric == "Nearest Number":
    scale = int(options.get('nscale', 1)) if options is not None else 1
    decay = options.get('ndecay', 0.999) if options is not None else 0.999
    return ClosestNumber(caseAttrib, queryValue, weight, scale, decay)
  elif simMetric == "Nearest Location":
    scale = options.get('lscale', '10km') if options is not None else '10km'
    decay = options.get('ldecay', 0.999) if options is not None else 0.999
    return ClosestLocation(caseAttrib, queryValue, weight, scale, decay)
  elif simMetric == "Table":
    return TableSimilarity(caseAttrib, queryValue, weight, options)
  elif simMetric == "EnumDistance":
    return EnumDistance(caseAttrib, queryValue, weight, options)
  elif simMetric == "Query Intersection":
    return QueryIntersection(caseAttrib, queryValue, weight)
  elif simMetric == "Path-based":
    sim_grid = getOntoSimilarity(projId + "_ontology_" + options['name'], queryValue)
    return OntologySimilarity(caseAttrib, queryValue, weight, sim_grid)
  elif simMetric == "Feature-based":
    sim_grid = getOntoSimilarity(projId + "_ontology_" + options['name'], queryValue)
    return OntologySimilarity(caseAttrib, queryValue, weight, sim_grid)
  elif simMetric == "Array":
    return Array(caseAttrib, queryValue, weight)
  else:
    return MostSimilar(caseAttrib, queryValue, weight)


# Similarity measure functions for retrieve phase of CBR cycle.
# Each similarity function returns a Painless script for Elasticsearch. 
# Each function requires field name and set of functions-specific parameters.

def Array(caseAttrib, queryValue, weight):
  """
  Returns the similarity between two arrays
  """
  try:
    # build query string comparing two arrays

    queryFnc = {
      "script_score": {
        "query": {
          "exists": {
            "field": caseAttrib
          }
        },
        "script": {
          "source": "float sum = 0; for (int i = 0; i < doc[params.attrib].length; i++) { for (int j = 0; j < params.queryValue.length; j++) { if (doc[params.attrib][i] == params.queryValue[j]) { sum += 1; } } } return sum/(doc[params.attrib].length+params.queryValue.length-sum);",
          "params": {
            "attrib": caseAttrib,
            "queryValue": queryValue
          }
        }
      }
    }
    return queryFnc

  except ValueError:
    print("Error")

def McSherryLessIsBetter(caseAttrib, queryValue, maxValue, minValue, weight):
  """
  Returns the similarity of two numbers following the McSherry - Less is better formula. queryVal is not used!
  """
  try:
    # build query string
    queryFnc = {
      "script_score": {
        "query": {
          "exists": {
            "field": caseAttrib
          }
        },
        "script": {
          "source": "((float)(Math.max(params.max,params.queryValue) - doc[params.attrib].value) / (float)(Math.max(params.max,params.queryValue) - Math.min(params.min,params.queryValue))) * params.weight",
          "params": {
            "attrib": caseAttrib,
            "queryValue": queryValue,
            "max": maxValue,
            "min": minValue,
            "weight": weight
          }
        },
        "_name": caseAttrib
      }
    }
    return queryFnc

  except ValueError:
    print("McSherryLessIsBetter() is only applicable to numbers")


def McSherryMoreIsBetter(caseAttrib, queryValue, maxValue, minValue, weight):
  """
  Returns the similarity of two numbers following the McSherry - More is better formula.
  """
  try:
    # build query string
    queryFnc = {
      "script_score": {
        "query": {
          "exists": {
            "field": caseAttrib
          }
        },
        "script": {
          "source": "(1 - ((float)(Math.max(params.max,params.queryValue) - doc[params.attrib].value) / (float)(Math.max(params.max,params.queryValue) - Math.min(params.min,params.queryValue)) )) * params.weight",
          "params": {
            "attrib": caseAttrib,
            "queryValue": queryValue,
            "max": maxValue,
            "min": minValue,
            "weight": weight
          }
        },
        "_name": caseAttrib
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
      "script_score": {
        "query": {
          "exists": {
            "field": caseAttrib
          }
        },
        "script": {
          "source": "if (doc[params.attrib].value <= params.queryValue) { return (1.0 * params.weight) } if (doc[params.attrib].value >= (Math.max(params.max,params.queryValue)) { return 0 } return (params.jump * (float)((Math.max(params.max,params.queryValue) - doc[params.attrib].value) / (float)((Math.max(params.max,params.queryValue) - params.queryValue)) * params.weight",
          "params": {
            "attrib": caseAttrib,
            "queryValue": queryValue,
            "jump": jump,
            "max": maxValue,
            "weight": weight
          }
        },
        "_name": caseAttrib
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
      "script_score": {
        "query": {
          "exists": {
            "field": caseAttrib
          }
        },
        "script": {
          "source": "if (doc[params.attrib].value >= params.queryValue) { return (1.0 * params.weight) } return (params.jump * (1 - ((float)(params.queryValue - doc[params.attrib].value) / (float)params.queryValue))) * params.weight",
          "params": {
            "attrib": caseAttrib,
            "queryValue": queryValue,
            "jump": jump,
            "weight": weight
          }
        },
        "_name": caseAttrib
      }
    }
    return queryFnc

  except ValueError:
    print("InrecaMoreIsBetter() is only applicable to numbers")


def Interval(caseAttrib, queryValue, max, min, weight):
  """
  Returns the similarity of two numbers inside an interval.
  """
  try:
    queryValue = float(queryValue)
    # build query string
    queryFnc = {
      "script_score": {
        "query": {
          "exists": {
            "field": caseAttrib
          }
        },
        "script": {
          "params": {
            "attrib": caseAttrib,
            "queryValue": queryValue,
            "max": max,
            "min": min,
            "weight": weight
          },
          "source": "(1 - (float)( Math.abs(params.queryValue - doc[params.attrib].value) / ((float)Math.max(params.max,params.queryValue) - (float)Math.min(params.min,params.queryValue)) )) * params.weight"
        },
        "_name": caseAttrib
      }
    }
    return queryFnc

  except ValueError:
    print("Interval() is only applicable to numbers")


def EnumDistance(caseAttrib, queryValue, weight, options):  # stores enum as array
  """
  Implements EnumDistance local similarity function. 
  Returns the similarity of two enum values as their distance sim(x,y) = |ord(x) - ord(y)|.
  """
  try:
    # build query string
    queryFnc = {
      "script_score": {
        "query": {
          "exists": {
            "field": caseAttrib
          }
        },
        "script": {
          "params": {
            "attrib": caseAttrib,
            "queryValue": queryValue,
            "lst": options.get('values'),
            "weight": weight
          },
          "source": "if (params.lst.contains(doc[params.attrib].value)) { return (1 - ( (float) Math.abs(params.lst.indexOf(params.queryValue) - params.lst.indexOf(doc[params.attrib].value)) / (float)params.lst.length )) * params.weight }"
        },
        "_name": caseAttrib
      }
    }
    return queryFnc

  except ValueError:
    print("Interval() is only applicable to numbers")


# def TermQuery(caseAttrib, queryValue, weight):
#   """
#   Matches query to equal field values using in-built method.
#   """
#   # build query string
#   query = {
#     "term": {
#       caseAttrib: {
#         "value": queryValue,
#         "boost": weight,
#         "_name": caseAttrib
#       }
#     }
#   }
#   return query


def Exact(caseAttrib, queryValue, weight):
  """
  Exact matches for fields defined as equal. Attributes that use this are indexed using 'keyword'.
  """
# build query string
  queryFnc = {
    "script_score": {
      "query": {
        "match": {
          caseAttrib: queryValue
        }
      },
      "script": {
        "params": {
          "attrib": caseAttrib,
          "queryValue": queryValue,
          "weight": weight
        },
        "source": "if (params.queryValue == doc[params.attrib].value) { return (1.0 * params.weight) }"
      },
      "_name": caseAttrib
    }
  }
  return queryFnc


# def MostSimilar_2(caseAttrib, queryValue, weight):
#   """
#   Most similar matches using ES default (works for all attribute types). Default similarity for strings and exact match for other types.
#   """
#   # build query string
#   query = {
#     "match": {
#       caseAttrib: {
#         "query": queryValue,
#         "boost": weight,
#         "_name": caseAttrib
#       }
#     }
#   }
#   return query


def MostSimilar(caseAttrib, queryValue, weight):
  """
  Most similar matches using ES default (works for all attribute types).
  Default similarity (BM25) for strings and exact match for other types.
  """
  # build query string
  queryFnc = {
    "script_score": {
      "query": {
        "match": {
          caseAttrib: queryValue
        }
      },
      "script": {
        "params": {
          "attrib": caseAttrib,
          "weight": weight
        },
        "source": "params.weight * _score"  # right side is a dummy to help explanation method
      },
      "_name": caseAttrib
    }
  }
  return queryFnc


# def ClosestDate_2(caseAttrib, queryValue, weight, maxDate, minDate):  # format 'dd-MM-yyyy' e.g. '01-02-2020'
#   """
#   Find the documents whose attribute values have the closest date to the query date. The date field is indexed as 'keyword' to enable use of this similarity metric.
#   """
#   # build query string
#   queryFnc = {
#     "script_score": {
#       "query": {
#         "match_all": {}
#       },
#       "script": {
#         "params": {
#           "attrib": caseAttrib,
#           "weight": weight,
#           "queryValue": queryValue,
#           "oldestDate": minDate,
#           "newestDate": maxDate
#         },
#         "source": "SimpleDateFormat sdf = new SimpleDateFormat('dd-MM-yyyy', Locale.ENGLISH); doc[params.attrib].size()==0 ? 0 : (1 - Math.abs(sdf.parse(doc[params.attrib].value).getTime() - sdf.parse(params.queryValue).getTime()) / ((sdf.parse(params.newestDate).getTime() - sdf.parse(params.oldestDate).getTime()) + 1)) * params.weight"
#       },
#       "_name": caseAttrib
#     }
#   }
#   return queryFnc


def ClosestDate(caseAttrib, queryValue, weight, scale, decay):  # format 'dd-MM-yyyy' e.g. '01-02-2020'
  """
  Find the documents whose attribute values have the closest date to the query date. The date field field is indexed as 'keyword' to enable use of this similarity metric.
  """
  # format = "%d-%m-%Y"'T'"%H:%M:%SZ"
  # qd = dateutil.parser.isoparse(queryValue)
  # queryValue = qd.strftime(format)   # enforce query conversion to a known date format

  # build query string
  queryFnc = {
    "script_score": {
      "query": {
        "exists": {
          "field": caseAttrib
        }
      },
      "script": {
        "params": {
          "attrib": caseAttrib,
          "origin": queryValue,
          "scale": scale,
          "offset": "0",
          "decay": decay,
          "weight": weight
        },
        "source": "decayDateExp(params.origin, params.scale, params.offset, params.decay, doc[params.attrib].value) * params.weight",
      },
      "_name": caseAttrib
    }
  }
  return queryFnc


def USE(caseAttrib, queryValue, weight):
  """
  Returns the similarity of two numbers using their vector representation.
  """
  # build query string
  queryFnc = {
    "script_score": {
      "query": {
        "exists": {
          "field": caseAttrib
        }
      },
      "script": {
        "params": {
          "attrib": caseAttrib,
          "query_vector": queryValue,
          "attrib_vector": caseAttrib + '.rep',
          "weight": weight
        },
        "source": "(cosineSimilarity(params.query_vector, doc[params.attrib_vector])+1)/2 * params.weight"
      },
      "_name": caseAttrib
    }
  }
  return queryFnc

def Semantic_SBERT(caseAttrib, queryValue, weight):
  """
  Returns the similarity of two numbers using their vector representation.
  """
  # build query string
  queryFnc = {
    "script_score": {
      "query": {
        "exists": {
          "field": caseAttrib
        }
      },
      "script": {
        "params": {
          "attrib": caseAttrib,
          "query_vector": queryValue,
          "attrib_vector": caseAttrib + '.rep',
          "weight": weight
        },
        "source": "(cosineSimilarity(params.query_vector, doc[params.attrib_vector])+1)/2 * params.weight"
      },
      "_name": caseAttrib
    }
  }
  return queryFnc


def ClosestNumber(caseAttrib, queryValue, weight, scale, decay):
  """
  Find the documents whose attribute values have the closest number to the query value.
  """
  # build query string
  queryFnc = {
    "script_score": {
      "query": {
        "exists": {
          "field": caseAttrib
        }
      },
      "script": {
        "params": {
          "attrib": caseAttrib,
          "origin": queryValue,
          "scale": scale,
          "offset": 0,
          "decay": decay,
          "weight": weight
        },
        "source": "decayNumericExp(params.origin, params.scale, params.offset, params.decay, doc[params.attrib].value) * params.weight",
      },
      "_name": caseAttrib
    }
  }
  return queryFnc


def ClosestLocation(caseAttrib, queryValue, weight, scale, decay):
  """
  Find the documents whose attribute values have the geo_point to the query value.
  """
  # build query string
  queryFnc = {
    "script_score": {
      "query": {
        "exists": {
          "field": caseAttrib
        }
      },
      "script": {
        "params": {
          "attrib": caseAttrib,
          "origin": queryValue,
          "scale": scale,
          "offset": "0km",
          "decay": decay,
          "weight": weight
        },
        "source": "decayGeoExp(params.origin, params.scale, params.offset, params.decay, doc[params.attrib].value) * params.weight",
      },
      "_name": caseAttrib
    }
  }
  return queryFnc


def TableSimilarity(caseAttrib, queryValue, weight, options):  # stores enum as array
  """
  Implements Table local similarity function.
  Returns the similarity of two categorical values as specified in a similarity table.
  """
  # build query string
  queryFnc = {
    "script_score": {
      "query": {
        "exists": {
          "field": caseAttrib
        }
      },
      "script": {
        "params": {
          "attrib": caseAttrib,
          "queryValue": queryValue,
          "sim_grid": options.get('sim_grid'),
          "grid_values": list(options.get('sim_grid', {})),
          "weight": weight
        },
        "source": "if (params.grid_values.contains(doc[params.attrib].value)) { return (params.sim_grid[params.queryValue][doc[params.attrib].value]) * params.weight }"
      },
      "_name": caseAttrib
    }
  }
  return queryFnc


def QueryIntersection(caseAttrib, queryValue, weight):
  """
  Implements Query Intersection local similarity function.
  Returns the similarity between two sets as their intersect offset by the length of the query set.
  If query set is q and case attribute value is a, returns |a∩q|/|q|
  """
  # build query string
  queryFnc = {
    "script_score": {
      "query": {
        "exists": {
          "field": caseAttrib
        }
      },
      "script": {
        "params": {
          "attrib": caseAttrib,
          "queryValue": list(queryValue),
          "weight": weight
        },
        "source": "double intersect = 0.0; "
                  "if (doc[params.attrib].size() > 0 && doc[params.attrib].value.length() > 0) { "
                  "for (item in doc[params.attrib]) { if (params.queryValue.contains(item)) { intersect = intersect + 1; } }"
                  "return (intersect/params.queryValue.length) * params.weight;} "
                  # "else { return 0;}"
      },
      "_name": caseAttrib
    }
  }
  return queryFnc


def OntologySimilarity(caseAttrib, queryValue, weight, sim_grid):
  """
  Uses similarity values from an ontology-based measure such as the Wu & Palmer algorithm.
  Returns the similarity of two ontology entities as specified in a similarity grid.
  """
  # build query string
  queryFnc = {
    "script_score": {
      "query": {
        "exists": {
          "field": caseAttrib
        }
      },
      "script": {
        "params": {
          "attrib": caseAttrib,
          "queryValue": queryValue,
          "sim_grid": sim_grid,
          "grid_concepts": list(sim_grid),
          "weight": weight
        },
        "source": "if (params.grid_concepts.contains(doc[params.attrib].value)) { return (params.sim_grid[doc[params.attrib].value]) * params.weight }"
      },
      "_name": caseAttrib
    }
  }
  return queryFnc


def MatchAll():
  """
  Retrieve all documents. There is a 10,000 size limit for Elasticsearch query results! The Scroll API can be used to 
  retrieve more than 10,000. 
  """
  return {"match_all": {}}
