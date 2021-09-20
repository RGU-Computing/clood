This is to keep few code snippets that you will find useful when managing CloodCBR

### Making the API's Secure with AWS API KEYS

In the serverless.yml file set the API Key name. After adding Key authorisation you will need to update the HTTP requests done to CloodCBR API with header ```x-api-key```
```yml
provider:
  name: aws
  runtime: python3.7
  region: eu-west-1
  stage: dev
  apiKeys:
    - DEV_KEY_NAME <----
```

In the HTTP method add ```private: true```
```yml
  get_project:
    handler: handler.get_project
    timeout: 10
    events:
      - http:
          path: project/{id}
          method: get
          cors: true
          private: true <----
```

### View all the documents in the ES index

```python
# proj['casebase'] is the casebase name

query = {'query': {'bool': {'should': [{'match_all': {}}]}}, 'size': 1000}
res = es.search(index=proj['casebase'], body=query)
```

### Delete all the documents in the ES index

```python
# proj['casebase'] is the casebase name

query = {'query': {'bool': {'should': [{'match_all': {}}]}}, 'size': 1000}
res = es.delete_by_query(index=proj['casebase'], body=query)
```
