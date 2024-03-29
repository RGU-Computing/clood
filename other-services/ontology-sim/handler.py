from distutils.debug import DEBUG
import re
import sys
import os
import math
import json
from timeit import default_timer as timer
from requests_aws4auth import AWS4Auth
from opensearchpy import OpenSearch, helpers, RequestsHttpConnection
from collections import OrderedDict
import numpy as np
import config as cfg

import rdflib  
import logging

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



# load graphs
def load_graphs(list_of_source_dicts):
    """
    Adds ontologies from a list (dictionaries of sources) to a graph and returns the graph.
    A dictionary specifies the source/link of an ontology and the format as in [{'source':'', format:''}, ...].
    """
    if len(list_of_source_dicts) < 1:
        return None
    
    graph = rdflib.Graph()
    for source_dict in list_of_source_dicts:
      if 'format' in source_dict:
        graph.parse(source_dict['source'], format=source_dict['format'])
      else:
        graph.parse(source_dict['source'],  format='xml')

    return graph


def execute_query(graph, qry):
    """
    Executes a SPARQL query against graph.
    """
    return graph.query(qry, DEBUG=False)


def mscs(graph, node1, node2, relation_type='rdfs:subClassOf'):
    """
    Finds the most specific common subsumer of two nodes in graph.
    """
    q = ("select ?lcs where {" +
      "?lcs ^(" + relation_type + "*) <" + node1 + ">, <" + node2 + "> ;"+
           "a owl:Class ." +
      "filter not exists { "+
        "?llcs ^(" + relation_type + "*) <" + node1 + ">, <" + node2 + "> ;"+
              "a owl:Class ;"+
              relation_type + "+ ?lcs ."+
      "}"+
    "}")
    
    for row in execute_query(graph, q):
        return row.lcs
    
    return None


def path_distance(graph, node1, node2, relation_type='rdfs:subClassOf'):
    """
    Calculates the number of edges between two nodes of a graph.
    """
    q1 = ("select (count(?mid) as ?distance) where { " +
      "<" + node1 + "> " + relation_type + "* ?mid ." +
      "?mid " + relation_type + "+ <" + node2 + "> ." +
    "}")
    
    q2 = ("select (count(?mid) as ?distance) where { " +
      "<" + node2 + "> " + relation_type + "* ?mid ." +
      "?mid " + relation_type + "+ <" + node1 + "> ." +
    "}")
    dst = 0
    for row in execute_query(graph, q1):
        dst = int(row.distance)
        break

    if dst == 0:  # try to measure from the other direction
        for row in execute_query(graph, q2):
            return int(row.distance)
    return dst


def distance_to_root(graph, node, relation_type='rdfs:subClassOf', root=None):
    """
    Calculates the number of edges between a node and the root node.
    Uses a specified root node if supplied.
    """
    if root is not None:
        return path_distance(graph, node, root)
    q = ("select ?sub (count(?mid) as ?distance) where {" +
          "<" + node + "> " + relation_type + "* ?mid ."+
          "?mid " + relation_type + "+ ?sub ." +
        "}"+
        "group by ?sub")

    max_val = -1
    for row in execute_query(graph, q):
        #print(type(row.sub))
        #print(f"{row}")
        if type(row.sub) is rdflib.term.URIRef and max_val < int(row.distance):
            max_val = int(row.distance)
    
    return max_val  # -1 means is_root or not_found


def all_nodes(graph, relation_type='rdfs:subClassOf', root=None):
    """
    Extracts all concepts in an ontology using the specified relation type to determine ontology structure.
    Extracts from a node and downwards if one is specified.
    """
    res = set()
    q = ''
    if root is None:
        q = ("select ?super ?sub ?othercat where {" +
              "?sub " + relation_type + "* ?super ."+
              "?othercat " + relation_type + " ?super ." +
            "} group by ?sub"
            )
    else:
        q = ("select ?sub ?othercat where {" +
              "?sub " + relation_type + "* <" + root + "> ."+
              "?othercat " + relation_type + " <" + root + "> ." +
            "} group by ?sub"
            )
    
    for row in execute_query(graph, q):
        if type(row.sub) is rdflib.term.URIRef:
            if root is None:
                res.add(row.sub)
            else:
                res.add(row.sub)

    return list(res)


def all_ancestor_nodes(graph, node, relation_type='rdfs:subClassOf'):
    """
    Extracts all ancestors of a concept (upward reachable nodes) in an ontology using the specified relation type
    to determine ontology structure.
    Extracts from a node and upwards (inc. the query node).
    """
    res = set()

    q = ("select ?sub where {" +
         "<" + node + "> " + relation_type + "* ?mid ." +
         "?mid " + relation_type + "+ ?sub ." +
         "}")

    res.add(str(node))  # include self
    for row in execute_query(graph, q):
        if type(row.sub) is rdflib.term.URIRef:
            res.add(str(row.sub))

    return list(res)


def wup(graph, x, y, relation_type='rdfs:subClassOf', root=None):
    """
    Ontology-based similarity using the Wu & Palmer algorithm.
    """
    # find the most specific common subsumer
    lcs = mscs(graph, x, y)
    if lcs is None:  # No common subsumer found
        return 0
    # count edges in the shortest paths from x to mscs and y to mcsc
    c1 = path_distance(graph, x, lcs)
    c2 = path_distance(graph, y, lcs)
    # count edges from mscs to the root node, root
    c3 = distance_to_root(graph, lcs, relation_type=relation_type, root=root) + 1
    
    return round(((2 * c3) / ((2 * c3) + c1 + c2)), 3)


def san(graph, x, y):
    """
    Ontology-based similarity using the Sanchez et al. dissimilarity algorithm.
    """
    # find the ancestors of each node
    a = all_ancestor_nodes(graph, x)
    b = all_ancestor_nodes(graph, y)

    i = set(a).difference(set(b))  # a \ b
    j = set(b).difference(set(a))  # b \ a
    u = set(a).union(set(b))  # a U b

    num = 1 + (float(len(i) + len(j)) / len(u))

    return round((1 - math.log2(num)), 3)


def getOntologyMapping():
    """
    Mapping for ontologies.
    """
    pmap = {
        "mappings": {
            "properties": {
                "key": {"type": "keyword"},
                "map": {
                   "type": "nested",
                    "properties": {
                       "value": {"type": "float"},
                     },
                }
            }
        }
    }
    return pmap

def preload(event, context=None):
  """
  End-point: Preload Ontology index
  """
  statusCode = 200
  params = json.loads(event['body'])
  ontologyId = params.get('ontologyId', None)
  sources     = params.get('sources', None)

  root_node = params.get('root_node', None)
  relation_type = params.get('relation_type', "rdfs:subClassOf")
  sim_method = params.get('similarity_method', "wup")

  graph = load_graphs(sources)
  #2. extract unique list of concepts in the graph
  concepts = all_nodes(graph, relation_type=relation_type, root=root_node)  # can specify a root node or a relation type to use
  #3. compute pairwise similarity values of concepts (there can be different similarity metrics to choose from)
  similarity_grid = []
  for c1 in concepts:
      res = {}
      for c2 in concepts:
          if str(c1) == str(c2):  # no need to compute for same values
              res.update({str(c2): 1.0})
          elif sim_method == 'san':
              res.update({str(c2): san(graph, c1, c2)})
          else:
              res.update({str(c2): wup(graph, c1, c2)})
      similarity_grid.append({"key": str(c1), "map": res})

  es = getESConn()

  if es.indices.exists(index=ontologyId):
    es.indices.delete(index=ontologyId)

  ont_mapping = getOntologyMapping()
  es.indices.create(index=ontologyId, body=ont_mapping)

  resp = helpers.bulk(es, similarity_grid, index=ontologyId, doc_type="_doc")

  response = {
      "statusCode": statusCode,
      "headers": headers,
      "body": json.dumps({"message":"Succesfully Added"})
    }
  return response

def query_cache(event, context=None):
  """
  End-point: Cache Ontology based on Query
  """
  statusCode = 200
  params = json.loads(event['body'])
  ontologyId = params.get('ontologyId', None)
  sources     = params.get('sources', None)
  key = str(params.get('key', None))
  root_node = params.get('root_node', None)
  relation_type = params.get('relation_type', "rdfs:subClassOf")
  sim_method = params.get('similarity_method', "wup")
  
  es = getESConn()

  if not es.indices.exists(index=ontologyId):
    ont_mapping = getOntologyMapping()
    es.indices.create(index=ontologyId, body=ont_mapping)

  # retrieve if ES index does exist
  result = getByUniqueField(es, ontologyId, "key", key)

  # If existing in the index already return the value
  if(result):
    response = {
      "statusCode": 200,
      "headers": headers,
      "body": json.dumps(result)
    }
    return response

  graph = load_graphs(sources)
  #2. extract unique list of concepts in the graph
  concepts = all_nodes(graph,relation_type=relation_type, root=root_node)  # can specify a root node or a relation type to use
  
  #3. compute pairwise similarity values of concepts (there can be different similarity metrics to choose from)
  similarity_grid = []
  for c1 in concepts:
      if str(c1) != key:
        continue
      res = {}
      for c2 in concepts:
          if str(c1) == str(c2):  # no need to compute for same values
              res.update({str(c2): 1.0})
          elif sim_method == 'san':
              res.update({str(c2): san(graph, c1, c2)})
          else:
              res.update({str(c2): wup(graph, c1, c2)})
      similarity_grid.append({"key": str(c1), "map": res})

  resp = helpers.bulk(es, similarity_grid, index=ontologyId, doc_type="_doc")

  if len(similarity_grid) > 0:
    response = {
        "statusCode": statusCode,
        "headers": headers,
        "body": json.dumps(similarity_grid[0])
      }
  else: 
    response = {
        "statusCode": statusCode,
        "headers": headers,
        "body": json.dumps({})
      }
  return response


def query_not_cache(event, context=None):
  """
  End-point: Non-Cached Ontology based on Query
  """
  statusCode = 200
  params = json.loads(event['body'])
  ontologyId = params.get('ontologyId', None)
  sources     = params.get('sources', None)
  key = str(params.get('key', None))
  root_node = params.get('root_node', None)
  relation_type = params.get('relation_type', "rdfs:subClassOf")
  sim_method = params.get('similarity_method', "wup")
  
  graph = load_graphs(sources)
  #2. extract unique list of concepts in the graph
  concepts = all_nodes(graph, relation_type=relation_type, root=root_node)  # can specify a root node or a relation type to use
  
  #3. compute pairwise similarity values of concepts (there can be different similarity metrics to choose from)
  similarity_grid = []
  for c1 in concepts:
      if str(c1) != key:
        continue
      res = {}
      for c2 in concepts:
          if str(c1) == str(c2):  # no need to compute for same values
              res.update({str(c2): 1.0})
          elif sim_method == 'san':
              res.update({str(c2): san(graph, c1, c2)})
          else:  # wup default
              res.update({str(c2): wup(graph, c1, c2)})
      similarity_grid.append({"key": str(c1), "map": res})

  if len(similarity_grid) > 0:
    response = {
        "statusCode": statusCode,
        "headers": headers,
        "body": json.dumps(similarity_grid[0])
      }
  else: 
    response = {
        "statusCode": statusCode,
        "headers": headers,
        "body": json.dumps({})
      }
  return response

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


def query_ontology(event, context=None):
  """
  End-point: Retrieves an ontology reference based on query
  """
  statusCode = 200
  params = json.loads(event['body'])
  ontologyId = params.get('ontologyId', None)
  key     = params.get('key', None)

  es = getESConn()

  if not es.indices.exists(index=ontologyId):
    response = {
        "statusCode": 404,
        "headers": headers,
        "body": json.dumps({"message": "Cannot find ontology"})
      }
    return response

  # retrieve if ES index does exist
  result = getByUniqueField(es, ontologyId, "key", key)

  response = {
    "statusCode": 200,
    "headers": headers,
    "body": json.dumps(result)
  }
  return response

def check_status(event, context=None):
  """
  End-point: Checks if an index exists. Returns number of documents in the index if the index exists.
  """
  count = {"count": 0}
  # retrieve if ES index does exist
  es = getESConn()
  params = json.loads(event['body'])
  ontologyId = params.get('ontologyId', None)

  if not es.indices.exists(index=ontologyId):
    response = {
        "statusCode": 404,
        "headers": headers,
        "body": json.dumps({"message": "Cannot find ontology"})
      }
    return response

  if es.indices.exists(index=ontologyId):
    es.indices.refresh(ontologyId)
    countes = es.cat.count(ontologyId, params={"format": "json"})  # count of documents in index
    countes = countes[0]
    count["count"] = countes["count"]

  response = {
    "statusCode": 200,
    "headers": headers,
    "body": json.dumps(count)
  }
  return response


def delete(event, context=None):
  """
  End-point: Delete an Ontology index
  """
  statusCode = 200
  params = json.loads(event['body'])
  ontologyId = params.get('ontologyId', None)

  es = getESConn()

  if es.indices.exists(index=ontologyId):
    es.indices.delete(index=ontologyId)

  response = {
      "statusCode": statusCode,
      "headers": headers,
      "body": json.dumps({"message": "Succesfully Deleted"})
    }
  return response


def home(event, context):
  """
  End-point: To check API reachability.
  """
  body = {
    "message": "Your function executed successfully! Ontology-based similarity service is running."
  }

  response = {
    "statusCode": 200,
    "headers": headers,
    "body": json.dumps(body)
  }
  
  return response
