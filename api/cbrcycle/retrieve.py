# Retrieve functions
import dateutil.parser
import requests
import json
import config as cfg


def getVector(text):
  """
  Calls an external service to get the 512 dimensional vector representation of a piece of text.
  """
  url = cfg.use_vectoriser
  res = requests.post(url, json={'text': text})
  res_dictionary = res.json()
  return res_dictionary['vectors']


def checkOntoSimilarity(ontology_id):
  """
  Calls an external service to check if an ontology based similarity measures exist.
  """
  url = cfg.ontology_sim + '/status'
  res = requests.post(url, json={'ontologyId': ontology_id})
  return res.json()  #res['statusCode'] = 200 if ontology exists and 404 otherwise


def getOntoSimilarity(ontology_id, key):
  """
  Calls an external service to get ontology based similarity values for concept comparisons.
  """
  url = cfg.ontology_sim + '/query'
  res = requests.post(url, json={'ontologyId': ontology_id, 'key': key})
  res_dictionary = res.json()
  return res_dictionary.get('map', {})


def setOntoSimilarity(ontology_id, ontology_sources, relation_type=None, root_node=None, similarity_method="wup"):
  """
  Calls an external service to create ontology based similarity values for concept comparisons.
  """
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
  url = cfg.ontology_sim + '/delete'
  body = {
    "ontologyId": ontology_id
  }
  res = requests.post(url, json=body)
  return res.json()


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
  return data


def remove_vector_fields(attributes, data):
  """
  Flatten data values to remove vector fields.
  Transforms "x: {name: val, rep: vector(val)}" to "x: val"
  """
  for attrib in attributes:
    if attrib['similarity'] == 'Semantic USE':
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


def getQueryFunction(caseAttrib, queryValue, weight, simMetric, options):
  """
  Determine query function to use base on attribute specification and retrieval features.
  Add new query functions in the if..else statement as elif.
  """
  # minVal = kwargs.get('minVal', None) # optional parameter, minVal (name 'minVal' in function params when calling function e.g. minVal=5)
  if simMetric == "Equal" or simMetric == "EqualIgnoreCase":
    return Exact(caseAttrib, queryValue, weight)
  elif simMetric == "McSherry More":  # does not use the query value
    maxValue = options.get('max', 100.0) if options is not None else 100.0  # use 100 if no supplied max
    minValue = options.get('min', 0.0) if options is not None else 0.0  # use 0 if no supplied min
    return McSherryMoreIsBetter(caseAttrib, maxValue, minValue, weight)
  elif simMetric == "McSherry Less":  # does not use the query value
    maxValue = options.get('max', 100.0) if options is not None else 100.0  # use 100 if no supplied max
    minValue = options.get('min', 0.0) if options is not None else 0.0  # use 0 if no supplied min
    return McSherryLessIsBetter(caseAttrib, maxValue, minValue, weight)
  elif simMetric == "INRECA More":
    jump = options.get('jump', 1.0) if options is not None else 1.0  # use 1 if no supplied jump
    return InrecaMoreIsBetter(caseAttrib, queryValue, jump, weight)
  elif simMetric == "INRECA Less":
    jump = options.get('jump', 1.0) if options is not None else 1.0  # use 1 if no supplied jump
    maxValue = options.get('max', 100.0) if options is not None else 100.0  # use 100 if no supplied max
    return InrecaLessIsBetter(caseAttrib, queryValue, maxValue, jump, weight)
  elif simMetric == "Interval":
    interval = options.get('interval', 100.0) if options is not None else 100.0  # use 100 if no supplied interval
    return Interval(caseAttrib, queryValue, interval, weight)
  elif simMetric == "Semantic USE" and cfg.use_vectoriser is not None:
    return USE(caseAttrib, getVector(queryValue), weight)
  elif simMetric == "Nearest Date":
    return ClosestDate(caseAttrib, queryValue, weight)
  elif simMetric == "Nearest Number":
    return ClosestNumber(caseAttrib, queryValue, weight)
  elif simMetric == "Nearest Location":
    return ClosestLocation(caseAttrib, queryValue, weight)
  elif simMetric == "Table":
    return TableSimilarity(caseAttrib, queryValue, weight, options)
  elif simMetric == "EnumDistance":
    return EnumDistance(caseAttrib, queryValue, weight, options)
  elif simMetric == "Query Intersection":
    return QueryIntersection(caseAttrib, queryValue, weight)
  elif simMetric == "Path-based":
    sim_grid = getOntoSimilarity(options['id'], queryValue)
    return OntologySimilarity(caseAttrib, queryValue, weight, sim_grid)
  elif simMetric == "Feature-based":
    sim_grid = getOntoSimilarity(options['id'], queryValue)
    return OntologySimilarity(caseAttrib, queryValue, weight, sim_grid)
  else:
    return MostSimilar(caseAttrib, queryValue, weight)


# Similarity measure functions for retrieve phase of CBR cycle.
# Each similarity function returns a Painless script for Elasticsearch. 
# Each function requires field name and set of functions-specific parameters.

def McSherryLessIsBetter(caseAttrib, maxValue, minValue, weight):
  """
  Returns the similarity of two numbers following the McSherry - Less is better formula. queryVal is not used!
  """
  try:
    # build query string
    queryFnc = {
      "function_score": {
        "query": {
          "match_all": {}
        },
        "script_score": {
          "script": {
            "source": "(float)(params.max - doc[params.attrib].value) / (float)(params.max - params.min)",
            "params": {
              "max": maxValue,
              "min": minValue,
              "attrib": caseAttrib
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


def McSherryMoreIsBetter(caseAttrib, maxValue, minValue, weight):
  """
  Returns the similarity of two numbers following the McSherry - More is better formula.
  """
  try:
    # build query string
    queryFnc = {
      "function_score": {
        "query": {
          "match_all": {}
        },
        "script_score": {
          "script": {
            "source": "1 - ( (float)(params.max - doc[params.attrib].value) / (float)(params.max - params.min) )",
            "params": {
              "max": maxValue,
              "min": minValue,
              "attrib": caseAttrib
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
            "source": "if (doc[params.attrib].value <= params.queryValue) { return 1.0 } if (doc[params.attrib].value >= params.max) { return 0 } return params.jump * (float)(params.max - doc[params.attrib].value) / (float)(params.max - params.queryValue)",
            "params": {
              "jump": jump,
              "max": maxValue,
              "attrib": caseAttrib,
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
            "source": "if (doc[params.attrib].value >= params.queryValue) { return 1.0 } return params.jump * (1 - ((float)(params.queryValue - doc[params.attrib].value) / (float)params.queryValue))",
            "params": {
              "jump": jump,
              "attrib": caseAttrib,
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
              "attrib": caseAttrib,
              "queryValue": queryValue
            },
            "source": "1 - (float)( Math.abs(params.queryValue - doc[params.attrib].value) / (float)params.interval )"
          }
        },
        "boost": weight,
        "_name": "interval"
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
      "function_score": {
        "query": {
          "match_all": {}
        },
        "script_score": {
          "script": {
            "params": {
              "lst": options.get('values'),
              "attrib": caseAttrib,
              "queryValue": queryValue
            },
            "source": "if (params.lst.contains(doc[params.attrib].value)) { return 1 - ( (float) Math.abs(params.lst.indexOf(params.queryValue) - params.lst.indexOf(doc[params.attrib].value)) / (float)params.lst.length ) }"
          }
        },
        "boost": weight,
        "_name": "enumdistance"
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


def ClosestDate_2(caseAttrib, queryValue, weight, maxDate, minDate):  # format 'dd-MM-yyyy' e.g. '01-02-2020'
  """
  Find the documents whose attribute values have the closest date to the query date. The date field is indexed as 'keyword' to enable use of this similarity metric.
  """
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
          "newestDate": maxDate,
          "attrib": caseAttrib
        },
        "source": "SimpleDateFormat sdf = new SimpleDateFormat('dd-MM-yyyy', Locale.ENGLISH); doc[params.attrib].size()==0 ? 0 : (1 - Math.abs(sdf.parse(doc[params.attrib].value).getTime() - sdf.parse(params.queryValue).getTime()) / ((sdf.parse(params.newestDate).getTime() - sdf.parse(params.oldestDate).getTime()) + 1)) * params.weight"
      },
      "_name": "closestdate2"
    }
  }
  return queryFnc


def ClosestDate(caseAttrib, queryValue, weight):  # format 'dd-MM-yyyy' e.g. '01-02-2020'
  """
  Find the documents whose attribute values have the closest date to the query date. The date field field is indexed as 'keyword' to enable use of this similarity metric.
  """
  format = "%d-%m-%Y"
  qd = dateutil.parser.isoparse(queryValue)
  queryValue = qd.strftime(format)   # enforce query conversion to a known date format
  # build query string
  queryFnc = {
    "function_score": {
      "query": {
        "match_all": {}
      },
      "functions": [
        {
          "linear": {
            caseAttrib: {
              "origin": queryValue,
              "scale": "365d",
              "offset": "0",
              "decay": 0.999
            }
          }
        }
      ],
      "boost": weight,
      "_name": "closestdate"
    }
  }
  return queryFnc


def USE(caseAttrib, queryValue, weight):
  """
  Returns the similarity of two numbers using their vector representation.
  """
  # build query string
  queryFnc = {
    "function_score": {
      "query": {
        "match_all": {}
      },
      "script_score": {
        "script": {
          "params": {
            "query_vector": queryValue,
            "attrib": caseAttrib + '.rep'
          },
          "source": "cosineSimilarity(params.query_vector, doc[params.attrib]) + 1.0"
        }
      },
      "boost": weight,
      "_name": "USE"
    }
  }
  return queryFnc


def ClosestNumber(caseAttrib, queryValue, weight):
  """
  Find the documents whose attribute values have the closest number to the query value.
  """
  # build query string
  queryFnc = {
    "function_score": {
      "query": {
        "match_all": {}
      },
      "functions": [
        {
          "linear": {
            caseAttrib: {
              "origin": queryValue,
              "scale": 1,
              "decay": 0.999
            }
          }
        }
      ],
      "boost": weight,
      "_name": "closestnumber"
    }
  }
  return queryFnc


def ClosestLocation(caseAttrib, queryValue, weight):
  """
  Find the documents whose attribute values have the geo_point to the query value.
  """
  # build query string
  queryFnc = {
    "script_score": {
      "query": {
        "match_all": {}
      },
      "script": {
        "params": {
          "attrib": caseAttrib,
          "origin": queryValue,
          "scale": "10km",
          "offset": "0km",
          "decay": 0.999,
          "weight": weight,
        },
        "source": "decayGeoExp(params.origin, params.scale, params.offset, params.decay, doc[params.attrib].value) * params.weight",
      },
      "_name": "closestlocation"
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
    "function_score": {
      "query": {
        "match_all": {}
      },
      "script_score": {
        "script": {
          "params": {
            "attrib": caseAttrib,
            "queryValue": queryValue,
            "sim_grid": options.get('sim_grid'),
            "grid_values": list(options.get('sim_grid', {}))
          },
          "source": "if (params.grid_values.contains(doc[params.attrib].value)) { return params.sim_grid[params.queryValue][doc[params.attrib].value] } return 0.0"
        }
      },
      "boost": weight,
      "_name": "table"
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
    "function_score": {
      "query": {
        "match_all": {}
      },
      "script_score": {
        "script": {
          "params": {
            "attrib": caseAttrib,
            "queryValue": list(queryValue)
          },
          "source": "double intersect = 0.0; "
                    "if (doc[params.attrib].size() > 0 && doc[params.attrib].value.length() > 0) { "
                    "for (item in doc[params.attrib]) { if (params.queryValue.contains(item)) { intersect = intersect + 1; } }"
                    "return intersect/params.queryValue.length;} "
                    "else { return 0;}"
        }
      },
      "boost": weight,
      "_name": "queryintersect"
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
    "function_score": {
      "query": {
        "match_all": {}
      },
      "script_score": {
        "script": {
          "params": {
            "attrib": caseAttrib,
            "queryValue": queryValue,
            "sim_grid": sim_grid,
            "grid_concepts": list(sim_grid)
          },
          "source": "if (params.grid_concepts.contains(doc[params.attrib].value)) { return params.sim_grid[doc[params.attrib].value] } return 0.0"
        }
      },
      "boost": weight,
      "_name": "ontosim"
    }
  }
  return queryFnc


def MatchAll():
  """
  Retrieve all documents. There is a 10,000 size limit for Elasticsearch query results! The Scroll API can be used to 
  retrieve more than 10,000. 
  """
  return {"match_all": {}}
