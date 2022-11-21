from os import environ as env


aws = {
    "host": env.get('CLOOD_AWS_HOST', 'domain.eu-west-1.es.amazonaws.com'),
    "region": env.get('CLOOD_AWS_REGION', 'eu-west-1'),
    "access_key":   env.get('CLOOD_AWS_ACCESS_KEY', ''),
    "secret_key": env.get('CLOOD_AWS_SECRET_KEY','')
}

# For Local Development Use the docker-compose up command
# Make sure this is set to True for local development
is_dev = env.get('CLOOD_IS_DEV', True)
