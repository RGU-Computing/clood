from os import environ as env


aws = {
    "host": env.get('AWS_HOST', 'domain.eu-west-1.es.amazonaws.com'),
    "region": env.get('AWS_REGION', 'eu-west-1'),
    "access_key":   env.get('AWS_ACCESS_KEY', ''),
    "secret_key": env.get('AWS_SECRET_KEY_HERE', '')
}

# For Local Development Use the docker-compose up command
# Make sure this is set to True for local development
is_dev = env.get('IS_DEV', True)

# Third-party APIs
# use_vectoriser end-point should be callable using post request 
# with body "{'text': text}" and should return a 512-dimensional vector representation of the text
# use_vectoriser = None # for non USE
use_vectoriser = "http://cloodcbr-other-use:4100/dev/vectorise"
ontology_sim = "http://cloodcbr-other-ontology-sim:3000/dev"
sbert_vectoriser = "http://35.178.248.172/vectorise"
vectoriser_access_key = env['SECRET_KEY']

DEFAULT_USERNAME = env['CLOOD_ADMIN_USERNAME']
DEFAULT_PASSWORD = env['CLOOD_ADMIN_PASSWORD']
SECRET = env['CLOOD_ACCESS_SECRET']
