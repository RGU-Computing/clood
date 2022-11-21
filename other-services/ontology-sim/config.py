from os import environ as env


aws = {
    "host": env.get('AWS_HOST', 'domain.eu-west-1.es.amazonaws.com'),
    "region": env.get('AWS_REGION', 'eu-west-1'),
    "access_key":   env.get('AWS_ACCESS_KEY', ''),
    "secret_key": env.get('AWS_SECRET_KEY_HERE','')
}

# For Local Development Use the docker-compose up command
# Make sure this is set to True for local development
is_dev = env.get('IS_DEV', True)
