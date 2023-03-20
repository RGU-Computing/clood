# Add configuration and rename as config.py
aws = {
    "host": 'domain.eu-west-1.es.amazonaws.com',
    "region": 'eu-west-1',
    "access_key":   'ACCESS_KEY',
    "secret_key": 'SECRET_KEY_HERE'
}

# API Security
DEFAULT_USERNAME = "CHANGE_THIS"
DEFAULT_PASSWORD = "CHANGE_THIS_PASSWORD"
SECRET = "CHANGE_THIS_SECRET"

# For Local Development Use the docker-compose up command
# Make sure this is set to True for local development
is_dev = True

# Third-party APIs
# use_vectoriser end-point should be callable using post request 
# with body "{'text': text}" and should return a 512-dimensional vector representation of the text
# use_vectoriser = None # for non USE
# use_vectoriser = "http://cloodcbr-other-use:4100/dev/vectorise"
use_vectoriser = "http://cloodcbr-other-use:4000/dev/vectorise"
sbert_vectoriser = "http://cloodcbr-other-semantic-sim/vectorise"

vectoriser_access_key = "SECRET_KEY" # Change this to the same key set in other/ontologoy-sim or other/semantic-sim

# service for ontology-based similarity
ontology_sim = "http://cloodcbr-other-ontology-sim:3000/dev"