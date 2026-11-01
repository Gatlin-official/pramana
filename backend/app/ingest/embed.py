import hashlib

import httpx
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.config import EMBED_MODEL, OLLAMA_URL
from app.db.models import EmbeddingCache

# nomic-embed-text expects task prefixes
PREFIX = {"document": "search_document: ", "query": "search_query: "}


class OllamaDown(RuntimeError):
    pass


def _ollama_embed(texts: list[str]) -> list[list[float]]:
    try:
        r = httpx.post(
            f"{OLLAMA_URL}/api/embed",
            json={"model": EMBED_MODEL, "input": texts, "options": {"num_ctx": 8192}},
            timeout=300,
        )
        r.raise_for_status()
    except httpx.HTTPError as e:
        raise OllamaDown(f"Ollama embedding failed at {OLLAMA_URL}: {e}") from e
    return r.json()["embeddings"]


def embed(db: Session, texts: list[str], kind: str = "document", batch: int = 64) -> list[list[float]]:
    """Embed with a content-hash cache, so re-ingesting unchanged text costs no model calls."""
    full = [PREFIX[kind] + t for t in texts]
    keys = [hashlib.sha256(f"{EMBED_MODEL}\0{t}".encode()).hexdigest() for t in full]
    found: dict[str, list[float]] = {}
    for i in range(0, len(keys), 1000):
        rows = db.execute(select(EmbeddingCache).where(EmbeddingCache.hash.in_(keys[i : i + 1000])))
        found |= {r.hash: list(r.embedding) for r in rows.scalars()}
    todo = list(dict.fromkeys(k for k in keys if k not in found))
    text_of = dict(zip(keys, full, strict=True))
    for i in range(0, len(todo), batch):
        part = todo[i : i + batch]
        vecs = _ollama_embed([text_of[k] for k in part])
        found |= dict(zip(part, vecs, strict=True))
        db.execute(
            insert(EmbeddingCache)
            .values([{"hash": k, "embedding": v} for k, v in zip(part, vecs, strict=True)])
            .on_conflict_do_nothing()
        )
    db.commit()
    return [found[k] for k in keys]


def embed_query(db: Session, q: str) -> list[float]:
    # not cached: queries rarely repeat, and caching would hide real latency in the eval
    return _ollama_embed([PREFIX["query"] + q])[0]
