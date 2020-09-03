# Add configuration and rename as config.py
aws = {
    "host": '',
    "region": '',
    "access_key":   '',
    "secret_key": ''
}

# Third-party APIs
# use_vectoriser end-point should be callable using post request 
# with body "{'text': text}" and should return a 512-dimensional vector representation of the text
use_vectoriser = None # "https://link-to-endpoint-that-returns-vectors"