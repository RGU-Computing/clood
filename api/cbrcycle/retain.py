# Retain functions


def checkArrayWithCosine(attributes, data):
  """
  When using Array type and Cosine similarity, list size should be the same as the 
  configured vector attribute dimension and all array entries should be numeric.
  Function returns True if the required conditions are met and False otherwise.
  """
  for attrib in attributes:
    if attrib['type'] == 'Array' and attrib['similarity'] == 'Cosine':
      expected_dim = attrib.get('options').get('dimension', 512) if attrib.get('options') is not None else 512
      value = data.get(attrib['name'])  # expects list type of numeric entries
      if len(value) != expected_dim:  # check that dimension is as configured for attribute
        return False
      if not all(isinstance(e, (int, float)) for e in value):  # that all entries are numeric
        return False

  return True