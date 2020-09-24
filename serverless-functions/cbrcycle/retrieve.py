# Retrieve functions
import requests
import config as cfg


def getVector(text):
	"""
  Calls an external service to get the 512 dimensional vector representation of a piece of text.
  """
	url = cfg.use_vectoriser
	res = requests.post(url, json={'text': text})
	res_dictionary = res.json()
	return res_dictionary['vectors']


def getQueryFunction(caseAttrib, queryValue, weight, simMetric, *args, **kwargs):
	"""
  Determine query function to use base on attribute specification and retrieval features.
  Add new query functions in the if..else statement as elif.
  """
	# minVal = kwargs.get('minVal', None) # optional parameter, minVal (name 'minVal' in function params when calling function e.g. minVal=5)
	if simMetric == "Equal":
		return Exact(caseAttrib, queryValue, weight)
	elif simMetric == "McSherry More":
		minValue = 0.0  # TO BE REPLACED WITH SUPPLIED minValue
		maxValue = 100.0  # TO BE REPLACED WITH SUPPLIED maxValue
		return McSherryMoreIsBetter(caseAttrib, queryValue, maxValue, minValue, weight)
	elif simMetric == "McSherry Less":
		minValue = 0.0  # TO BE REPLACED WITH SUPPLIED minValue
		maxValue = 100.0  # TO BE REPLACED WITH SUPPLIED maxValue
		return McSherryLessIsBetter(caseAttrib, queryValue, maxValue, minValue, weight)
	elif simMetric == "INRECA More":
		jump = 0.0  # TO BE REPLACED WITH SUPPLIED jump
		return InrecaMoreIsBetter(caseAttrib, queryValue, jump, weight)
	elif simMetric == "INRECA Less":
		jump = 1.0  # TO BE REPLACED WITH SUPPLIED jump
		return InrecaLessIsBetter(caseAttrib, queryValue, jump, weight)
	elif simMetric == "Interval":
		interval = 2.0  # TO BE REPLACED WITH SUPPLIED interval
		return Interval(caseAttrib, queryValue, interval, weight)
	elif simMetric == "Semantic USE" and cfg.use_vectoriser is not None:
		print('Using vector-based similarity (USE)')
		return USE(caseAttrib, getVector(queryValue), weight)
	else:
		return MostSimilar(caseAttrib, queryValue, weight)


# Similarity measure functions for retrieve phase of CBR cycle.
# Each similarity function returns a Painless script for Elasticsearch. 
# Each function requires field name and set of functions-specific parameters.

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
						"source": "(params.max - doc[params.attrib].value) / (params.max - params.min)",
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
						"source": "1 - ( (params.max - doc[params.attrib].value) / (params.max - params.min) )",
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
						"source": "if (doc[params.attrib].value <= params.queryValue) { return 1 } if (doc[params.attrib].value >= params.maxValue) { return 0 } return params.jump * (params.maxValue - doc[params.attrib].value) / (params.maxValue - params.queryValue)",
						"params": {
							"jump": jump,
							"maxValue": maxValue,
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
						"source": "if (doc[params.attrib].value <= params.queryValue) { return 1 } return params.jump * (1 - ((params.queryValue - doc[params.attrib].value) / params.queryValue))",
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
						"source": "1 - ( Math.abs(params.queryValue - doc[params.attrib].value) / params.interval )"
					}
				},
				"boost": weight,
				"_name": "interval"
			}
		}
		return queryFnc
	
	except ValueError:
		print("Interval() is only applicable to numbers")


# NOT TESTED
def EnumDistance(caseAttrib, queryValue, arrayList, weight):  # stores enum as array
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
							"attrib": caseAttrib,
							"queryValue": queryValue
						},
						"source": "1 - ( Math.abs(lst.indexOf(params.queryValue) - lst.indexOf(doc[params.attrib].value)) / lst.length )"
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


def ClosestDate(caseAttrib, queryValue, weight, maxDate, minDate):  # format 'dd-MM-yyyy' e.g. '01-02-2020'
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
					"newestDate": maxDate,
					"attrib": caseAttrib
				},
				"source": "SimpleDateFormat sdf = new SimpleDateFormat('dd-MM-yyyy', Locale.ENGLISH); doc[params.attrib].size()==0 ? 0 : (1 - Math.abs(sdf.parse(doc[params.attrib].value).getTime() - sdf.parse(params.queryValue).getTime()) / ((sdf.parse(params.newestDate).getTime() - sdf.parse(params.oldestDate).getTime()) + 1)) * params.weight"
			},
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


def MatchAll():
	"""
  Retrieve all documents. There is a 10,000 size limit for Elasticsearch query results! The Scroll API can be used to 
  retrieve more than 10,000. 
  """
	return {"match_all": {}}
