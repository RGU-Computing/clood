# CloodCBR Ontology Based Similarity Support

## Endpoints

### Preload API

```
curl --location --request POST 'http://localhost:4200/dev/preload' \
--header 'Content-Type: application/json' \
--data-raw '{
    "ontologyId": "pizza",
    "sources": [
        {
            "source": "https://protege.stanford.edu/ontologies/pizza/pizza.owl",
            "format": "xml"
        }
    ]
}'
```

### Query API

```
curl --location --request POST 'http://localhost:4200/dev/query' \
--header 'Content-Type: application/json' \
--data-raw '{
    "ontologyId": "pizza",
    "key": "http://www.co-ode.org/ontologies/pizza/pizza.owl#PrinceCarlo"
}'
```

### Count/Status Check API

```
curl --location --request POST 'http://localhost:4200/dev/status' \
--header 'Content-Type: application/json' \
--data-raw '{
    "ontologyId": "pizza"
}'
```