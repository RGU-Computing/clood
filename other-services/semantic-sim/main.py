import json
from fastapi import FastAPI,HTTPException
from sentence_transformers import SentenceTransformer, util

from pydantic import BaseModel

import config


class Text(BaseModel):
    text: str
    access_key: str

class TextExt(BaseModel):
    text1: str
    text2: str
    access_key: str

# print("Using Model = " + config.model_name)
model = SentenceTransformer(config.model_name)

app = FastAPI()

@app.get("/")
async def root():
    return "SentenceTransformer"

@app.post("/vectorise")
async def vectorise(input: Text):
    # Sentences are encoded by calling model.encode()
    if(config.access_key != input.access_key):
        raise HTTPException(status_code=403, detail="Invalid Access Key")

    # print("API Call Incoming - ", input.text )
    embeddings = model.encode([input.text])
    return {
                "message": 'Vector representation using lite Universal Sentence Encoder',
                "vectors": embeddings.tolist()[0],
                "inputText": input.text
            }
    raise HTTPException(status_code=404, detail="Text not found")

@app.post("/similarity")
async def similarity(input: TextExt):
    # Sentences are encoded by calling model.encode()
    if(config.access_key != input.access_key):
        raise HTTPException(status_code=403, detail="Invalid Access Key")

    # print("API Call Incoming - ", input.text1, "and", input.text2)
    embeddings1 = model.encode([input.text1])
    embeddings2 = model.encode([input.text2])
    
    return {
                "message": 'Similarity using lite Universal Sentence Encoder',
                "similarity": util.cos_sim(embeddings1, embeddings2).tolist()[0][0],
                "inputText 1": input.text1,
                "inputText 2": input.text2
            }