import json
from fastapi import FastAPI,HTTPException
from sentence_transformers import SentenceTransformer

from pydantic import BaseModel

import config


class Text(BaseModel):
    text: str
    access_key: str

print("Using Model = " + config.model_name)
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

    print("API Call Incoming - ", input.text )
    embeddings = model.encode([input.text])
    return {
                "message": 'Vector representation using lite Universal Sentence Encoder',
                "vectors": embeddings.tolist()[0],
                "inputText": input.text
            }
    raise HTTPException(status_code=404, detail="Text not found")

