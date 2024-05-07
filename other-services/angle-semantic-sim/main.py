import json
import config
import torch

from fastapi import FastAPI,HTTPException
from pydantic import BaseModel
from transformers import AutoTokenizer, AutoModel
from angle_emb import AnglE, Prompts
from transformers import AutoModelForCausalLM, AutoTokenizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

class Text(BaseModel):
    text: str
    access_key: str

class TextExt(BaseModel):
    text1: str
    text2: str
    access_key: str

retrieval_prompt = "Represent this sentence for searching relevant passages: {text}"
matching_prompt = "{text}"

model_id = config.model_name
tokenizer = AutoTokenizer.from_pretrained(model_id)
model = AutoModel.from_pretrained(model_id)
app = FastAPI()

@app.get("/")
async def root():
    return "Angle Semantic Similarity"

@app.post("/vectorise/matching")
async def vectorise(input: Text):
    if(config.access_key != input.access_key):
        raise HTTPException(status_code=403, detail="Invalid Access Key")

    embeddings = get_angle_bert_embeddings(input.text, matching_prompt)
    return {
                "message": 'Vector representation using AnglE - matching model',
                "vectors": embeddings,
                "inputText": input.text
            }
    raise HTTPException(status_code=404, detail="Text not found")

@app.post("/vectorise/retrieval")
async def vectorise(input: Text):
    if(config.access_key != input.access_key):
        raise HTTPException(status_code=403, detail="Invalid Access Key")
    
    embeddings = get_angle_bert_embeddings(input.text, retrieval_prompt)
    return {
                "message": 'Vector representation using AnglE - retrieval model',
                "vectors": embeddings,
                "inputText": input.text
            }
    raise HTTPException(status_code=404, detail="Text not found")

@app.post("/similarity/matching")
async def similarity(input: TextExt):
    if(config.access_key != input.access_key):
        raise HTTPException(status_code=403, detail="Invalid Access Key")

    embeddings_1 = get_angle_bert_embeddings(input.text1, matching_prompt)
    embeddings_2 = get_angle_bert_embeddings(input.text2, matching_prompt)

    return {
                "message": 'Similarity using lite Universal Sentence Encoder',
                "similarity": calculate_cosine_similarity(embeddings_1, embeddings_2),
                "inputText 1": input.text1,
                "inputText 2": input.text2
            }

@app.post("/similarity/retrieval")
async def similarity(input: TextExt):
    if(config.access_key != input.access_key):
        raise HTTPException(status_code=403, detail="Invalid Access Key")

    embeddings1 = get_angle_bert_embeddings(input.text1, retrieval_prompt)
    embeddings2 = get_angle_bert_embeddings(input.text2, retrieval_prompt)
    
    return {
                "message": 'Similarity using lite Universal Sentence Encoder',
                "similarity": calculate_cosine_similarity(embeddings_1, embeddings_2),
                "inputText 1": input.text1,
                "inputText 2": input.text2
            }


# Utilities
def get_angle_bert_embeddings(sentence, prompt):
    text = prompt.format(text=sentence)
    input_ids = tokenizer([text], return_tensors='pt', truncation=True, max_length=512)
    for k, v in input_ids.items():
      input_ids[k] = v
    with torch.no_grad():
        hidden_state = model(**input_ids).last_hidden_state
    vec = (hidden_state[:, 0] + torch.mean(hidden_state, dim=1)) / 2.0
    return vec[0].tolist()

def calculate_cosine_similarity(vector1, vector2):
    vector1 = np.array(vector1).reshape(1, -1)
    vector2 = np.array(vector2).reshape(1, -1)
    similarity = cosine_similarity(vector1, vector2)
    return similarity[0][0]
