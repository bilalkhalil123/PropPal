# Replacing sentence-transformers (embedding options)

The backend uses **384-dimensional** embeddings for Qdrant (properties, builder profiles, builder services). The default is **sentence-transformers** (local model `all-MiniLM-L6-v2`), which loads PyTorch and uses ~1GB+ RAM. On Render’s free 512MB tier this causes OOM.

You can switch to an **API-based** embedding provider so the app does not load torch/sentence-transformers.

---

## Options (all 384 dims for existing Qdrant)

| Provider        | Env vars              | Cost              | Notes |
|----------------|------------------------|-------------------|--------|
| **OpenAI**     | `EMBEDDING_PROVIDER=openai`, `OPENAI_API_KEY` | Paid per token    | `text-embedding-3-small` with `dimensions=384`. No re-embed or new Qdrant collection. |
| **Hugging Face** | `EMBEDDING_PROVIDER=huggingface`, `HF_TOKEN` | Free tier + paid  | Same model (`all-MiniLM-L6-v2`) via Inference API. 384 dims. No re-embed. |
| **Local**      | `EMBEDDING_PROVIDER=local` (default) | Free (uses RAM)   | sentence-transformers + torch. Needs ~1GB+ RAM. |

---

## Render (avoid OOM)

1. In Render **Environment** set:
   - **EMBEDDING_PROVIDER** = `openai` **or** `huggingface`
   - **OPENAI_API_KEY** (if openai) **or** **HF_TOKEN** (if huggingface)
2. Optional: use a **lite** runtime image that does **not** install `sentence-transformers` and `torch` (smaller image, faster deploy). If you keep the current image, the app will just use the API and never load the local model when provider is openai/huggingface.

---

## Other providers (need new collection + backfill)

- **Voyage AI** (e.g. voyage-lite-2): 1024 dims → new Qdrant collection and re-run backfill jobs.
- **Cohere** embed-v3: configurable dims; if not 384, same as above.
- **Ollama** (nomic-embed-text): 768 dims → new collection + backfill; only for self-hosted.

---

## Summary

- **OpenAI**: set `EMBEDDING_PROVIDER=openai` and `OPENAI_API_KEY`; no code or Qdrant changes; pay per token.
- **Hugging Face**: set `EMBEDDING_PROVIDER=huggingface` and `HF_TOKEN`; same 384-dim model via API; free tier available.
- **Local**: default; keep for dev or when you have enough RAM (e.g. paid Render instance).
