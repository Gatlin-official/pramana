import bisect
import re
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models import Chunk, Document
from app.ingest.chunkers import chunk
from app.ingest.embed import embed
from app.ingest.loaders import load


def _title(text: str, source: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return re.sub(r"\s*\{\s*#[^}]*\}\s*$", "", line[2:]).strip()  # drop mkdocs {#anchor}
    return Path(source).stem


def ingest(db: Session, source: str, data: bytes, configs: list[str]) -> Document:
    """Create or replace a document and its chunks for each chunk config."""
    kind, text, pages = load(source, data)
    doc = db.scalar(select(Document).where(Document.source == source))
    if doc is None:
        doc = Document(source=source)
        db.add(doc)
    doc.title, doc.kind, doc.text, doc.pages = _title(text, source), kind, text, pages
    db.flush()
    db.execute(delete(Chunk).where(Chunk.doc_id == doc.id, Chunk.config.in_(configs)))
    for cfg in configs:
        spans = [s for s in chunk(text, cfg) if text[s[0] : s[1]].strip()]
        vecs = embed(db, [text[s:e] for s, e, _ in spans])
        db.add_all(
            Chunk(
                doc_id=doc.id,
                config=cfg,
                ordinal=i,
                text=text[s:e],
                token_count=n,
                char_start=s,
                char_end=e,
                page=bisect.bisect_right(pages, s) if pages else None,
                embedding=v,
            )
            for i, ((s, e, n), v) in enumerate(zip(spans, vecs, strict=True))
        )
    db.commit()
    return doc
