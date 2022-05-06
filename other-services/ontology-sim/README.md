# CloodCBR Ontology Based Similarity Support

Ontology-based similarity measures.

Currently, implementations are:
1. Similarity based on Wu & Palmer algorithm (`similarity_method` = 'wup').
2. Similarity based on Sanchez et al. dissimilarity algorithm (`similarity_method` = 'san').

## Endpoints

### Preload API

```json
{
    "ontologyId": "pizza",
    "sources": [
        {
            "source": "https://protege.stanford.edu/ontologies/pizza/pizza.owl",
            "format": "xml"
        }
    ],
    "similarity_method": (OPTIONAL) "wup",
    "root_node": (OPTIONAL) "http://www.co-ode.org/ontologies/pizza/pizza.owl#PizzaBase",
    "relation_type": (OPTIONAL) "rdfs:subClassOf"
}
```
Request

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

### Query API - Preloaded

```
curl --location --request POST 'http://localhost:4200/dev/query' \
--header 'Content-Type: application/json' \
--data-raw '{
    "ontologyId": "pizza",
    "key": "http://www.co-ode.org/ontologies/pizza/pizza.owl#PrinceCarlo"
}'
```

### Query API - Cached

```
curl --location --request POST 'http://localhost:4200/dev/query_cache' \
--header 'Content-Type: application/json' \
--data-raw '{
    "key": "http://www.co-ode.org/ontologies/pizza/pizza.owl#Mushroom",
    "ontologyId": "pizza",
    "sources": [
        {
            "source": "https://protege.stanford.edu/ontologies/pizza/pizza.owl",
            "format": "xml"
        }
    ],
    "similarity_method": "wup",
    "root_node": "http://www.co-ode.org/ontologies/pizza/pizza.owl#Pizza",
    "relation_type": "rdfs:subClassOf"
}'
```

### Query API - Uncached

```
curl --location --request POST 'http://localhost:4200/dev/query_not_cache' \
--header 'Content-Type: application/json' \
--data-raw '{
    "ontologyId": "pizza",
    "key": "http://www.co-ode.org/ontologies/pizza/pizza.owl#PrinceCarlo",
    "sources": [
        {
            "source": "https://protege.stanford.edu/ontologies/pizza/pizza.owl",
            "format": "xml"
        }
    ],
    "similarity_method": "san",
    "root_node": "http://www.co-ode.org/ontologies/pizza/pizza.owl#Pizza",
    "relation_type": "rdfs:subClassOf"
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

### Delete an Ontology API

```
curl --location --request POST 'http://localhost:4200/dev/delete' \
--header 'Content-Type: application/json' \
--data-raw '{
    "ontologyId": "pizza"
}'
```