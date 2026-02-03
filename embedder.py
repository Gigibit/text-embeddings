import os
from functools import lru_cache
from typing import List

from dotenv import load_dotenv
from fastapi import Depends, FastAPI
from pydantic import BaseModel, Field

load_dotenv()

MODEL_NAME = os.getenv("TEXT_EMBEDDINGS_MODEL", "hf-internal-testing/tiny-random-bert")

app = FastAPI(title="Text Embeddings API")


class EmbedRequest(BaseModel):
    texts: List[str] = Field(..., min_length=1, description="Texts to embed")


class EmbedResponse(BaseModel):
    model: str
    embeddings: List[List[float]]


class EmbeddingModel:
    def __init__(self, model_name: str) -> None:
        import torch
        from transformers import AutoModel, AutoTokenizer

        self.model_name = model_name
        self.torch = torch
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name)
        self.model.eval()

    def embed(self, texts: List[str]) -> List[List[float]]:
        inputs = self.tokenizer(
            texts,
            padding=True,
            truncation=True,
            return_tensors="pt",
        )
        with self.torch.no_grad():
            outputs = self.model(**inputs)
        token_embeddings = outputs.last_hidden_state
        attention_mask = inputs["attention_mask"].unsqueeze(-1)
        masked_embeddings = token_embeddings * attention_mask
        sum_embeddings = masked_embeddings.sum(dim=1)
        token_counts = attention_mask.sum(dim=1).clamp(min=1)
        mean_embeddings = sum_embeddings / token_counts
        return mean_embeddings.cpu().tolist()


@lru_cache(maxsize=1)
def get_model() -> EmbeddingModel:
    return EmbeddingModel(MODEL_NAME)


@app.get("/health")
def health_check() -> dict:
    return {"status": "ok", "model": MODEL_NAME}


@app.post("/embed", response_model=EmbedResponse)
def embed_texts(
    request: EmbedRequest, model: EmbeddingModel = Depends(get_model)
) -> EmbedResponse:
    embeddings = model.embed(request.texts)
    return EmbedResponse(model=model.model_name, embeddings=embeddings)