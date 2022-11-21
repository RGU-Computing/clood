from os import environ as env


# SBERT Model Name should be added
# https://www.sbert.net/docs/pretrained_models.html#model-overview
# all-mpnet-base-v2 , all-MiniLM-L12-v2 , all-MiniLM-L6-v2
model_name = "all-mpnet-base-v2"
access_key = env.get('SECRET_KEY', '')  # CHANGE THIS ON PRODUCTION
