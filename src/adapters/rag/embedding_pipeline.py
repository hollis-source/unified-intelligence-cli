from __future__ import annotations

import os
from typing import List, Optional

import numpy as np


class EmbeddingPipeline:
    """Configurable embedding pipeline supporting local and hosted models.

    Default: sentence-transformers 'all-MiniLM-L6-v2' (local, 384-dim)
    Optional: OpenAI text-embedding-3-small (1536-dim) if OPENAI_API_KEY set
    """

    def __init__(self, model: Optional[str] = None, provider: Optional[str] = None):
        self.provider = provider or ("openai" if os.getenv("OPENAI_API_KEY") else "sentence-transformers")
        self.model = model or ("text-embedding-3-small" if self.provider == "openai" else "all-MiniLM-L6-v2")
        self._client = None
        self._st_model = None

    async def _ensure_initialized(self) -> None:
        if self.provider == "openai" and self._client is None:
            from openai import AsyncOpenAI

            self._client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        elif self.provider == "sentence-transformers" and self._st_model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except Exception as e:  # pragma: no cover
                raise RuntimeError(
                    "sentence-transformers not installed. pip install sentence-transformers"
                ) from e
            self._st_model = SentenceTransformer(self.model)

    async def embed_text(self, text: str) -> np.ndarray:
        await self._ensure_initialized()
        if self.provider == "openai":
            resp = await self._client.embeddings.create(model=self.model, input=text)
            return np.array(resp.data[0].embedding, dtype=np.float32)
        else:
            emb = self._st_model.encode([text], convert_to_numpy=True, normalize_embeddings=True)[0]
            return emb.astype(np.float32)

    async def embed_texts(self, texts: List[str], batch_size: int = 64) -> np.ndarray:
        await self._ensure_initialized()
        if self.provider == "openai":
            # OpenAI can handle multiple inputs; chunk by batch_size
            embs: List[np.ndarray] = []
            for i in range(0, len(texts), batch_size):
                chunk = texts[i : i + batch_size]
                resp = await self._client.embeddings.create(model=self.model, input=chunk)
                embs.extend(np.array([d.embedding for d in resp.data], dtype=np.float32))
            return np.vstack(embs)
        else:
            embs = self._st_model.encode(texts, batch_size=batch_size, convert_to_numpy=True, normalize_embeddings=True)
            return embs.astype(np.float32)

    @property
    def dimension(self) -> int:
        if self.provider == "openai":
            return 1536
        # MiniLM-L6-v2 returns 384-dim
        return 384

    @property
    def model_id(self) -> str:
        return self.model

