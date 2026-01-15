
import os
import logging
from typing import List, Optional, Literal, Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

try:
    from sentence_transformers import SentenceTransformer
except Exception as e:  # pragma: no cover
    # Provide a clearer error if dependencies are missing at runtime
    raise RuntimeError(
        "sentence-transformers is required. Install with: pip install sentence-transformers fastapi uvicorn"
    ) from e

# -------------------------
# Configuration
# -------------------------
DEFAULT_MODEL = os.getenv("EMBEDDINGS_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
DEVICE = os.getenv("EMBEDDINGS_DEVICE", None)  # e.g., "cuda", "cpu" or None for auto
NORMALIZE = os.getenv("EMBEDDINGS_NORMALIZE", "true").lower() in {"1", "true", "yes", "y"}
BATCH_SIZE = int(os.getenv("EMBEDDINGS_BATCH_SIZE", "32"))

# -------------------------
# Logging
# -------------------------
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("embeddings-api")

# -------------------------
# App & Model init
# -------------------------
app = FastAPI(title="Embeddings API",
              version="1.0.0",
              description="FastAPI service that returns sentence embeddings using SentenceTransformer.")

def _resolve_device(device: Optional[str]) -> Optional[str]:
    if device:
        return device
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda"
        # MPS for Apple Silicon
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"
    except Exception:
        pass
    return "cpu"

_device = _resolve_device(DEVICE)
logger.info("Loading model %s on device %s", DEFAULT_MODEL, _device)

try:
    model = SentenceTransformer(DEFAULT_MODEL, device=_device)
except Exception as e:
    logger.exception("Failed to load model: %s", e)
    raise

# -------------------------
# Schemas
# -------------------------
class InputsRequest(BaseModel):
    inputs: List[str] = Field(..., description="List of texts to embed")
    model: Optional[str] = Field(None, description="Override model name; defaults to EMBEDDINGS_MODEL env var")
    normalize: Optional[bool] = Field(None, description="Whether to L2-normalize embeddings; defaults from env")
    batch_size: Optional[int] = Field(None, ge=1, le=1024, description="Batch size for encoding")
    convert_to_numpy: Optional[bool] = Field(True, description="Return numpy arrays (serialized as lists)")
    precision: Optional[Literal['float32','float16']] = Field('float32', description="Dtype for embeddings")

class Embedding(BaseModel):
    object: Literal['embedding'] = 'embedding'
    embedding: List[float]
    index: int

class InputsResponse(BaseModel):
    object: Literal['list'] = 'list'
    model: str
    usage: dict
    data: List[Embedding]

# -------------------------
# Health
# -------------------------
@app.get("/health")
def health() -> dict:
    return {"status": "ok", "model": DEFAULT_MODEL, "device": _device}

# -------------------------
# Embeddings endpoint
# -------------------------
@app.post("/inputs", response_model=InputsResponse)
def create_embeddings(payload: InputsRequest):
    texts = payload.inputs
    if not texts:
        raise HTTPException(status_code=400, detail="'inputs' cannot be empty")

    model_name = payload.model or DEFAULT_MODEL
    if model_name != DEFAULT_MODEL:
        # Lazy-load alternate model if requested
        try:
            alt_model = SentenceTransformer(model_name, device=_device)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to load model '{model_name}': {e}")
        used_model = alt_model
    else:
        used_model = model

    normalize = payload.normalize if payload.normalize is not None else NORMALIZE
    batch_size = payload.batch_size or BATCH_SIZE
    convert_to_numpy = True if payload.convert_to_numpy is None else payload.convert_to_numpy
    precision = payload.precision or 'float32'

    try:
        # Set dtype based on requested precision, if supported
        encode_kwargs: dict[str, Any] = {
            'batch_size': batch_size,
            'normalize_embeddings': normalize,
            'convert_to_numpy': convert_to_numpy,
            'show_progress_bar': False,
        }
        if precision == 'float16':
            try:
                import torch
                encode_kwargs['dtype'] = torch.float16
            except Exception:
                pass

        vectors = used_model.encode(texts, **encode_kwargs)
        # Ensure we have a Python list of lists for JSON serialization
        if hasattr(vectors, 'tolist'):
            vectors = vectors.tolist()

        data = [Embedding(embedding=vectors[i], index=i) for i in range(len(texts))]
        usage = {
            "prompt_tokens": sum(len(t.split()) for t in texts),  # rough proxy
            "total_vectors": len(texts),
            "dimension": len(data[0].embedding) if data else 0,
            "normalized": normalize,
            "model": model_name,
        }
        return InputsResponse(model=model_name, usage=usage, data=data)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Embedding failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

# -------------------------
# Entrypoint for local run
# -------------------------
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "3000"))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run("main:app", host=host, port=port, reload=os.getenv("RELOAD", "false").lower() in {"1","true","yes","y"})
