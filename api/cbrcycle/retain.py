# Retain functions


# def checkArrayWithCosine(attributes, data):
#   """
#   When using Array type and Cosine similarity, list size should be the same as the 
#   configured vector attribute dimension and all array entries should be numeric.
#   Function returns True if the required conditions are met and False otherwise.
#   """
#   for attrib in attributes:
#     if attrib['type'] == 'Array' and attrib['similarity'] == 'Cosine':
#       expected_dim = attrib.get('options').get('dimension', 512) if attrib.get('options') is not None else 512
#       value = data.get(attrib['name'])  # expects list type of numeric entries
#       if len(value) != expected_dim:  # check that dimension is as configured for attribute
#         return False
#       if not all(isinstance(e, (int, float)) for e in value):  # that all entries are numeric
#         return False

#   return True

# imports for logger configuration
import sys
import os
sys.path.append(os.path.abspath("../"))
from logger_config import logger

def checkArrayWithCosine(attributes, data):
    """
    When using Array type and Cosine similarity, list size should be the same as the 
    configured vector attribute dimension and all array entries should be numeric.
    Function returns True if the required conditions are met and False otherwise.
    """
    try:
        logger.info("Checking array with cosine similarity for data validation")
        for attrib in attributes:
            if attrib['type'] == 'Array' and attrib['similarity'] == 'Cosine':
                expected_dim = attrib.get('options', {}).get('dimension', 512)
                value = data.get(attrib['name'])
                
                if value is None:
                    logger.error(f"Attribute '{attrib['name']}' not found in data")
                    return False
                
                if not isinstance(value, list):
                    logger.error(f"Attribute '{attrib['name']}' value is not a list")
                    return False
                
                if len(value) != expected_dim:
                    logger.error(f"Attribute '{attrib['name']}' dimension {len(value)} does not match expected dimension {expected_dim}")
                    return False
                
                if not all(isinstance(e, (int, float)) for e in value):
                    logger.error(f"Attribute '{attrib['name']}' contains non-numeric entries")
                    return False
        
        logger.info("Array with cosine similarity validation passed")
        return True
    
    except Exception as e:
        logger.exception(f"Error occurred during array validation with cosine similarity: {e}")
        return False