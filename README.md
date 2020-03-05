<img src="https://raw.githubusercontent.com/RGU-Computing/clood/master/images/CloodV2.png" width="400">

*Clood CBR: Towards Microservices Oriented Case-Based Reasoning*

# What is Clood? 
*(its **Cloud** in Scottish dialect)*


Case-based Reasoning (CBR) applications have been deployed in a wide range of sectors, from pharmaceuticals; to defence and aerospace to IoT and transportation, to poetry and music generation; for example. However, a majority of CBR applications have been built using monolithic architectures which impose size and complexity constraints. As such these applications have a barrier to adopting new technologies and remain prohibitively expensive in both time and cost because changes in frameworks or languages affect the application directly. To address this challenge, we developed a distributed and highly scalable generic CBR system, Clood, which is based on a microservices architecture. This splits the application into a set of smaller, interconnected services that scale to meet varying demands. Microservices are cloud-native architectures and with the rapid increase in cloud-computing adoption, it is timely for the CBR community to have access to such a framework.

## Project Components

### Implementation Architecture


## Clood Structure and Technologies
- API - REST API for communication from client apps (Serverless Framework with Python functions)
- Client - This is the demonstration dashboard (AngularJS)
- Elasticsearch - Managed ES service used as casebase 

### Serverless Functions

### Elasticsearch

### Dashboard

## Start Using Clood? 🚀

### Elasticsearch 
Follow the guide [Here](https://docs.aws.amazon.com/elasticsearch-service/latest/developerguide/es-createupdatedomains.html) on getting started with Elasticsearch in AWS. All you need next is the ES url and the AWS access keys.

### API - Serverless functions

We have built Clood with the [serverless](https://serverless.com/) framework which is a used deploy and test serverless apps across different cloud providers. The example installation here will be for AWS.

1. Make sure you have installed and setup serverless framework globally. [Guide](https://serverless.com/framework/docs/getting-started/)

2. Install Dependenices from CLI
```
npm install
```

3. Update the serverless.yml file as required. (Eg. region, service name..)

4. Add a conf.py file with the following structure

```python
aws = {
    "host": 'ELASTIC SEARCH AWS URL',
    "region": 'eu-west-1',
    "access_key":   '',
    "secret_key": ''
}
```

4. Simply deploy now, it will package and run in CLI
```
serverless deploy
```

### Client Dashboard
<img src="https://raw.githubusercontent.com/RGU-Computing/clood/master/images/screenshots/client_projects.png">




### Examples

----
