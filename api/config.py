from os import environ as env


aws = {
    "host": env.get('CLOOD_AWS_HOST', 'domain.eu-west-1.es.amazonaws.com'),
    "region": env.get('CLOOD_AWS_REGION', 'eu-west-1'),
    "access_key":   env.get('CLOOD_AWS_ACCESS_KEY', ''),
    "secret_key": env.get('CLOOD_AWS_SECRET_KEY_HERE', '')
}

# For Local Development Use the docker-compose up command
# Make sure this is set to True for local development
is_dev = env.get('CLOOD_IS_DEV', True)

# Third-party APIs
# use_vectoriser end-point should be callable using post request 
# with body "{'text': text}" and should return a 512-dimensional vector representation of the text
# use_vectoriser = None # for non USE
use_vectoriser = env.get('CLOOD_USE_VECTORISER_URL', "http://cloodcbr-other-use:4100/dev/vectorise")
ontology_sim = env.get('CLOOD_ONTOLOGY_SIM_URL', "http://cloodcbr-other-ontology-sim:3000/dev")
sbert_vectoriser = env.get('CLOOD_SBERT_VECTORISER_URL', None)
sbert_similarity = env.get('CLOOD_SBERT_SIM_URL', None)
angle_vectoriser_matching = env.get('CLOOD_ANGLE_VECTORISER_MATCHING_URL', None)
angle_vectoriser_retrieval = env.get('CLOOD_ANGLE_VECTORISER_RETRIEVAL_URL', None)
angle_similarity_matching = env.get('CLOOD_ANGLE_SIM_MATCHING_URL', None)
angle_similarity_retrieval = env.get('CLOOD_ANGLE_SIM_RETRIEVAL_URL', None)

vectoriser_access_key = env.get('CLOOD_SBERT_VECTORISER_ACCESS_KEY', None)

DEFAULT_USERNAME = env['CLOOD_ADMIN_USERNAME']
DEFAULT_PASSWORD = env['CLOOD_ADMIN_PASSWORD']
SECRET = env['CLOOD_AUTH_SECRET']

# LLM configuration for CBR-RAG endpoint
llm = {
    "provider": env.get('CLOOD_LLM_PROVIDER', 'openai'),
    "api_key": env.get('CLOOD_LLM_API_KEY', ''),
    "model": env.get('CLOOD_LLM_MODEL', 'gpt-4o-mini'),
    "url": env.get('CLOOD_LLM_API_URL', 'https://api.openai.com/v1/chat/completions'),
    # prompt template placeholders: {query_case}, {cases}, {attributes}
    "prompt_template": env.get('CLOOD_CBR_RAG_PROMPT', "You are an expert assistant. Based on the query features and retrieved cases, create a new case (JSON object) that represents the best solution.\n\nThe query case is provided as a list of feature objects. In each feature object, 'name' is the attribute name and 'value' is the value for that attribute.\n\nRetrieved cases are standard case objects where each entry is in the form attribute_name: attribute_value.\n\nThe generated solution must use the same case-object structure as the retrieved cases and must follow the expected attributes specification.\n\nThe retrieved cases should directly influence the generated solution. Use the retrieved cases as the primary evidence for choosing attribute values, and prefer values supported by the best-matching retrieved cases rather than inventing unsupported values.\n\nQuery features:\n{query_case}\n\nRetrieved cases:\n{cases}\n\nExpected case attributes:\n{attributes}\n\nRespond with ONLY a valid JSON object (no markdown, no extra text) that matches the case structure with all required attributes filled:")
}
