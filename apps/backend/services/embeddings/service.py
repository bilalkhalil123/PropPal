"""
Embedding service: local (sentence-transformers), Hugging Face Inference API, or OpenAI.

Use EMBEDDING_PROVIDER=openai or huggingface on Render to avoid loading torch/sentence-transformers
and stay within 512MB. All backends return 384-dim vectors for compatibility with Qdrant.
"""
from __future__ import annotations

from functools import lru_cache
from typing import List

# Same dimension as all-MiniLM-L6-v2; required for existing Qdrant collections
EMBEDDING_DIM = 384

_HF_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
_HF_URL = f"https://api-inference.huggingface.co/pipeline/feature-extraction/{_HF_MODEL}"


def _get_settings():
    from common.config import get_settings
    return get_settings()


@lru_cache(maxsize=1)
def _get_local_model():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(_HF_MODEL)


def _embed_local_cached(text: str) -> List[float]:
    model = _get_local_model()
    vector = model.encode(text, normalize_embeddings=True)
    return [float(x) for x in vector.tolist()]


def _embed_batch_local_cached(texts: List[str]) -> List[List[float]]:
    model = _get_local_model()
    vectors = model.encode(texts, normalize_embeddings=True, convert_to_numpy=True)
    return [[float(x) for x in row.tolist()] for row in vectors]


def _embed_huggingface(text: str) -> List[float]:
    import httpx
    settings = _get_settings()
    if not settings.HF_TOKEN:
        raise RuntimeError("HF_TOKEN is required when EMBEDDING_PROVIDER=huggingface")
    with httpx.Client(timeout=30.0) as client:
        r = client.post(
            _HF_URL,
            headers={"Authorization": f"Bearer {settings.HF_TOKEN}"},
            json={"inputs": text, "options": {"wait_for_model": True}},
        )
        r.raise_for_status()
        out = r.json()
    # API returns list of vectors; single string -> one vector
    if isinstance(out, list) and len(out) == 1:
        vec = out[0]
    else:
        vec = out
    if isinstance(vec, list) and len(vec) == EMBEDDING_DIM and isinstance(vec[0], (int, float)):
        return [float(x) for x in vec]
    # Sometimes returns list of token vectors (list of lists); take mean
    if isinstance(vec, list) and vec and isinstance(vec[0], list):
        n = len(vec[0])
        mean_vec = [sum(v[i] for v in vec) / len(vec) for i in range(n)]
        return [float(x) for x in mean_vec]
    if isinstance(vec, list) and vec and isinstance(vec[0], (int, float)):
        return [float(x) for x in vec]
    raise ValueError(f"Unexpected HF embedding shape: {type(out)}, len={len(out) if isinstance(out, (list, tuple)) else 'n/a'}")


def _embed_batch_huggingface(texts: List[str]) -> List[List[float]]:
    import httpx
    settings = _get_settings()
    if not settings.HF_TOKEN:
        raise RuntimeError("HF_TOKEN is required when EMBEDDING_PROVIDER=huggingface")
    with httpx.Client(timeout=60.0) as client:
        r = client.post(
            _HF_URL,
            headers={"Authorization": f"Bearer {settings.HF_TOKEN}"},
            json={"inputs": texts, "options": {"wait_for_model": True}},
        )
        r.raise_for_status()
        out = r.json()
    if not isinstance(out, list):
        raise ValueError(f"HF API returned non-list: {type(out)}")
    result: List[List[float]] = []
    for item in out:
        if isinstance(item, list):
            if item and isinstance(item[0], (int, float)):
                result.append([float(x) for x in item])
            elif item and isinstance(item[0], list):
                n = len(item[0])
                mean_vec = [sum(v[i] for v in item) / len(item) for i in range(n)]
                result.append([float(x) for x in mean_vec])
            else:
                result.append([float(x) for x in item])
        else:
            raise ValueError(f"Unexpected item type: {type(item)}")
    return result


def _embed_openai(text: str) -> List[float]:
    import httpx
    settings = _get_settings()
    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is required when EMBEDDING_PROVIDER=openai")
    with httpx.Client(timeout=30.0) as client:
        r = client.post(
            "https://api.openai.com/v1/embeddings",
            headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}", "Content-Type": "application/json"},
            json={"model": "text-embedding-3-small", "input": text, "dimensions": EMBEDDING_DIM},
        )
        r.raise_for_status()
        data = r.json()
    emb = data["data"][0]["embedding"]
    return [float(x) for x in emb]


def _embed_batch_openai(texts: List[str]) -> List[List[float]]:
    import httpx
    settings = _get_settings()
    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is required when EMBEDDING_PROVIDER=openai")
    with httpx.Client(timeout=60.0) as client:
        r = client.post(
            "https://api.openai.com/v1/embeddings",
            headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}", "Content-Type": "application/json"},
            json={"model": "text-embedding-3-small", "input": texts, "dimensions": EMBEDDING_DIM},
        )
        r.raise_for_status()
        data = r.json()
    return [[float(x) for x in item["embedding"]] for item in sorted(data["data"], key=lambda x: x["index"])]


def embed_text(text: str) -> List[float]:
    provider = _get_settings().EMBEDDING_PROVIDER.strip().lower()
    if provider == "openai":
        return _embed_openai(text)
    if provider == "huggingface":
        return _embed_huggingface(text)
    return _embed_local_cached(text)


def embed_batch(texts: List[str]) -> List[List[float]]:
    if not texts:
        return []
    provider = _get_settings().EMBEDDING_PROVIDER.strip().lower()
    if provider == "openai":
        return _embed_batch_openai(texts)
    if provider == "huggingface":
        return _embed_batch_huggingface(texts)
    return _embed_batch_local_cached(texts)
