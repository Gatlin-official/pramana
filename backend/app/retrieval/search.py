"""Three retrieval modes behind one function: dense, keyword, hybrid (RRF), with optional rerank."""

from dataclasses import dataclass, replace
from functools import lru_cache

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import RERANK_MODEL
from app.ingest.embed import embed_query

MODES = ("dense", "keyword", "hybrid")
RRF_K = 60
RERANK_POOL = 30


@dataclass(frozen=True)
class Hit:
    chunk_id: int
    score: float
    doc_id: int
    source: str
    text: str
    char_start: int
    char_end: int
    page: int | None


_COLS = "c.id, c.doc_id, d.source, c.text, c.char_start, c.char_end, c.page"


def _hits(rows) -> list[Hit]:
    return [Hit(r.id, float(r.score), r.doc_id, r.source, r.text, r.char_start, r.char_end, r.page) for r in rows]


def dense(db: Session, q: str, config: str, k: int) -> list[Hit]:
    # ponytail: exact scan (no HNSW index); add one when chunks per config pass ~100k
    vec = str(embed_query(db, q))
    sql = text(f"""
        SELECT {_COLS}, 1 - (c.embedding <=> CAST(:v AS vector)) AS score
        FROM chunks c JOIN documents d ON d.id = c.doc_id
        WHERE c.config = :cfg ORDER BY c.embedding <=> CAST(:v AS vector) LIMIT :k""")
    return _hits(db.execute(sql, {"v": vec, "cfg": config, "k": k}))


def keyword(db: Session, q: str, config: str, k: int) -> list[Hit]:
    # OR the stemmed terms: plainto_tsquery ANDs everything, which misses most natural questions
    sql = text(f"""
        WITH tq AS (SELECT NULLIF(replace(plainto_tsquery('english', :q)::text, '&', '|'), '')::tsquery AS q)
        SELECT {_COLS}, ts_rank_cd(c.tsv, tq.q) AS score
        FROM chunks c JOIN documents d ON d.id = c.doc_id, tq
        WHERE c.config = :cfg AND c.tsv @@ tq.q ORDER BY score DESC, c.id LIMIT :k""")
    return _hits(db.execute(sql, {"q": q, "cfg": config, "k": k}))


def rrf(lists: list[list[Hit]], k: int = RRF_K) -> list[Hit]:
    """Reciprocal Rank Fusion: score = sum over lists of 1 / (k + rank), rank starting at 1."""
    scores: dict[int, float] = {}
    first: dict[int, Hit] = {}
    for hits in lists:
        for rank, h in enumerate(hits, 1):
            scores[h.chunk_id] = scores.get(h.chunk_id, 0.0) + 1 / (k + rank)
            first.setdefault(h.chunk_id, h)
    order = sorted(scores, key=lambda cid: (-scores[cid], cid))
    return [replace(first[cid], score=scores[cid]) for cid in order]


def hybrid(db: Session, q: str, config: str, k: int) -> list[Hit]:
    pool = max(k, 50)
    return rrf([dense(db, q, config, pool), keyword(db, q, config, pool)])[:k]


@lru_cache(maxsize=1)
def _cross_encoder():
    from sentence_transformers import CrossEncoder  # heavy import, only when rerank is used

    return CrossEncoder(RERANK_MODEL)


def rerank(q: str, hits: list[Hit], k: int, scorer=None) -> list[Hit]:
    """Re-score with a cross-encoder. `scorer(q, texts) -> scores` is injectable for tests."""
    if not hits:
        return []
    scores = scorer(q, [h.text for h in hits]) if scorer else _cross_encoder().predict([(q, h.text) for h in hits])
    ranked = sorted(zip(hits, scores, strict=True), key=lambda p: -float(p[1]))
    return [replace(h, score=float(s)) for h, s in ranked[:k]]


def retrieve(db: Session, q: str, mode: str, config: str, k: int = 5, use_rerank: bool = False) -> list[Hit]:
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}")
    fn = {"dense": dense, "keyword": keyword, "hybrid": hybrid}[mode]
    if not use_rerank:
        return fn(db, q, config, k)
    return rerank(q, fn(db, q, config, RERANK_POOL), k)
