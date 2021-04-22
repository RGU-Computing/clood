<img src="https://raw.githubusercontent.com/RGU-Computing/clood/master/images/CloodV2.png" width="400">

*Clood CBR: Towards Microservices Oriented Case-Based Reasoning*

# What is Clood? 
*(its **Cloud** in Scottish dialect)*


Case-based Reasoning (CBR) applications have been deployed in a wide range of sectors, from pharmaceuticals; to defence and aerospace to IoT and transportation, to poetry and music generation; for example. However, a majority of CBR applications have been built using monolithic architectures which impose size and complexity constraints. As such these applications have a barrier to adopting new technologies and remain prohibitively expensive in both time and cost because changes in frameworks or languages affect the application directly. To address this challenge, we developed a distributed and highly scalable generic CBR system, Clood, which is based on a microservices architecture. This splits the application into a set of smaller, interconnected services that scale to meet varying demands. Microservices are cloud-native architectures and with the rapid increase in cloud-computing adoption, it is timely for the CBR community to have access to such a framework.

[CloodCBR Paper Published at ICCBR 2020](https://rgu-repository.worktribe.com/output/895530/clood-cbr-towards-microservices-oriented-case-based-reasoning) 📄 

[CloodCBR Presentation and Demo from ICCBR 2020](https://www.dropbox.com/s/i4vadj9c0dkwrsn/Clood%20CBR%20Final%20-%20ICCBR%202020.mp4?dl=0) ▶️ 

## Project Components

### Implementation Architecture

<img src="https://raw.githubusercontent.com/RGU-Computing/clood/master/images/clood_architecture.jpg">

## Clood Structure and Technologies
- Serverless Functions - REST API for communication from client apps (Serverless Framework with Python functions)
- Client - This is the demonstration dashboard (AngularJS)
- Elasticsearch - Managed ES service used as casebase 

### Serverless Functions

Project is available in the ```serverless-functions``` folder

### Elasticsearch
For the Clood implementation we have used [AWS Elasticsearch service](https://aws.amazon.com/elasticsearch-service/).

### Dashboard
Project is available in the ```dashboard``` folder. 


## Start Using Clood? 🚀

### Elasticsearch 
Follow the guide [Here](https://docs.aws.amazon.com/elasticsearch-service/latest/developerguide/es-createupdatedomains.html) on getting started with Elasticsearch in AWS. All you need next is the ES url and the AWS access keys.

### Serverless functions (API)

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

Guide to install and use the Clood Dashboard is available in the /dashboard folder. [Clood Dashboard](https://github.com/RGU-Computing/clood/tree/master/dashboard)


## License

<p xmlns:cc="http://creativecommons.org/ns#" xmlns:dct="http://purl.org/dc/terms/"><a property="dct:title" rel="cc:attributionURL" href="https://github.com/RGU-Computing/clood">Clood CBR: Towards Microservices Oriented Case-Based Reasoning</a> by <span property="cc:attributionName">Nkisi-Orji, Ikechukwu; Wiratunga, Nirmalie; Palihawadana, Chamath; Recio-García, Juan A.; Corsar, David; Robert Gordon University Aberdeen</span> is licensed under <a href="http://creativecommons.org/licenses/by/4.0/?ref=chooser-v1" target="_blank" rel="license noopener noreferrer" style="display:inline-block;">Attribution 4.0 International<br><img width="22px" style="height:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/cc.svg?ref=chooser-v1"><img width="22px" style="width:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/by.svg?ref=chooser-v1"></a></p>

----
Repo Maintained by [Ikechukwu Nkisi-Orji (RGU)](https://github.com/ike01) and [Chamath Palihawadana (RGU)](https://github.com/chamathpali)
