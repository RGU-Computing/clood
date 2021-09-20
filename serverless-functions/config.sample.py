# Add configuration and rename as config.py
aws = {
    "host": 'domain.eu-west-1.es.amazonaws.com',
    "region": 'eu-west-1',
    "access_key":   'ACCESS_KEY',
    "secret_key": 'SECRET_KEY_HERE'
}

# Third-party APIs
# use_vectoriser end-point should be callable using post request 
# with body "{'text': text}" and should return a 512-dimensional vector representation of the text
use_vectoriser = None # "https://link-to-endpoint-that-returns-vectors"
