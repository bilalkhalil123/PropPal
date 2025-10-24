from __future__ import annotations

from functools import lru_cache
from typing import List


@lru_cache(maxsize=1)
def get_model():
    # Lazy import so base app can start without these deps until needed
    from sentence_transformers import SentenceTransformer

    # Default local free model; dims=384
    return SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")


def embed_text(text: str) -> List[float]:
    model = get_model()
    vector = model.encode(text, normalize_embeddings=True)
    return [float(x) for x in vector.tolist()]


def embed_batch(texts: List[str]) -> List[List[float]]:
    model = get_model()
    vectors = model.encode(texts, normalize_embeddings=True, convert_to_numpy=True)
    return [[float(x) for x in row.tolist()] for row in vectors]


