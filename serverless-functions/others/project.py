
def indexMapping(es, project):
  """
  Creates mapping for a [project's] index.
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
  print(query)
  res = es.search(index=index, body=query)
  if (res['hits']['total']['value'] > 0):
    entry = res['hits']['hits'][0]['_source']
    entry['id__'] = res['hits']['hits'][0]['_id']
    result = entry
  return result


def getProjectMapping():
  pmap = {
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
  return pmap

