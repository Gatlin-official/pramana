from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, Computed, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.config import EMBED_DIM


class Base(DeclarativeBase):
    pass


class Document(Base):
    __tablename__ = "documents"
    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String, unique=True)  # relative path or upload name
    title: Mapped[str] = mapped_column(String)
    kind: Mapped[str] = mapped_column(String)  # md | txt | pdf
    text: Mapped[str] = mapped_column(Text)  # full extracted text; chunk offsets index into it
    pages: Mapped[list | None] = mapped_column(JSON)  # pdf: char offset where each page starts
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Chunk(Base):
    __tablename__ = "chunks"
    id: Mapped[int] = mapped_column(primary_key=True)
    doc_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    config: Mapped[str] = mapped_column(String, index=True)  # e.g. fixed-512-0, so chunkings coexist
    ordinal: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    token_count: Mapped[int] = mapped_column(Integer)
    char_start: Mapped[int] = mapped_column(Integer)
    char_end: Mapped[int] = mapped_column(Integer)
    page: Mapped[int | None] = mapped_column(Integer)
    embedding = mapped_column(Vector(EMBED_DIM))
    tsv = mapped_column(TSVECTOR, Computed("to_tsvector('english', text)", persisted=True))
    __table_args__ = (Index("ix_chunks_tsv", "tsv", postgresql_using="gin"),)


class EmbeddingCache(Base):
    __tablename__ = "embedding_cache"
    hash: Mapped[str] = mapped_column(String(64), primary_key=True)  # sha256(model + text)
    embedding = mapped_column(Vector(EMBED_DIM))


class QueryLog(Base):
    __tablename__ = "queries_log"
    id: Mapped[int] = mapped_column(primary_key=True)
    question: Mapped[str] = mapped_column(Text)
    mode: Mapped[str] = mapped_column(String)
    rerank: Mapped[bool]
    answer: Mapped[str | None] = mapped_column(Text)
    chunk_ids: Mapped[list | None] = mapped_column(JSON)
    latency_ms: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
