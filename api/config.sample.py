# Add configuration and rename as config.py
aws = {
    "host": 'domain.eu-west-1.es.amazonaws.com',
    "region": 'eu-west-1',
    "access_key":   'ACCESS_KEY',
    "secret_key": 'SECRET_KEY_HERE'
}

# For Local Development Use the docker-compose up command
# Make sure this is set to True for local development
is_dev = True

# Third-party APIs
# use_vectoriser end-point should be callable using post request 
# with body "{'text': text}" and should return a 512-dimensional vector representation of the text
# use_vectoriser = None # for non USE
use_vectoriser = "http://cloodcbr-other-use:4100/dev/vectorise"