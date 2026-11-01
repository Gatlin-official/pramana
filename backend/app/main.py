import csv
import json
import logging
import time
from collections import defaultdict, deque
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.config import CHUNK_CONFIG, RATE_LIMIT_PER_MIN, ROOT
from app.db.models import Chunk, Document, QueryLog
from app.db.session import SessionLocal, get_db
from app.generation.answer import answer_stream
from app.ingest.embed import OllamaDown
from app.ingest.loaders import KINDS
from app.ingest.pipeline import ingest

log = logging.getLogger("pramana")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
RESULTS = ROOT / "eval" / "results"
MAX_UPLOAD = 20 * 1024 * 1024

app = FastAPI(title="Pramana")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_methods=["*"], allow_headers=["*"])
(RESULTS / "charts").mkdir(parents=True, exist_ok=True)
app.mount("/eval/charts", StaticFiles(directory=RESULTS / "charts"), name="charts")

# ponytail: in-memory per-IP limiter, single process only; move to Redis if you run >1 worker
_hits: dict[str, deque] = defaultdict(deque)


def rate_limit(request: Request) -> None:
    now, q = time.monotonic(), _hits[request.client.host if request.client else "?"]
    while q and now - q[0] > 60:
        q.popleft()
    if len(q) >= RATE_LIMIT_PER_MIN:
        raise HTTPException(429, "Rate limit exceeded, try again in a minute.")
    q.append(now)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    t = time.perf_counter()
    resp = await call_next(request)
    log.info(
        "%s %s %s %.0fms",
        request.method,
        request.url.path,
        resp.status_code,
        (time.perf_counter() - t) * 1000,
    )
    return resp


@app.exception_handler(OllamaDown)
async def ollama_down(_: Request, e: OllamaDown):
    return JSONResponse({"detail": f"Model server unavailable. Is Ollama running? ({e})"}, status_code=503)


@app.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("select 1"))
    return {"status": "ok"}


class AskIn(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    mode: Literal["dense", "keyword", "hybrid"] = "hybrid"
    rerank: bool = True
    k: int = Field(5, ge=1, le=10)


def _sse(event: dict) -> str:
    return f"event: {event['type']}\ndata: {json.dumps(event)}\n\n"


@app.post("/ask", dependencies=[Depends(rate_limit)])
def ask(body: AskIn):
    def events():
        with SessionLocal() as db:
            try:
                for ev in answer_stream(db, body.question, body.mode, CHUNK_CONFIG, body.rerank, body.k):
                    yield _sse(ev)
                    if ev["type"] == "done":
                        db.add(
                            QueryLog(
                                question=body.question,
                                mode=body.mode,
                                rerank=body.rerank,
                                answer=ev["answer"],
                                chunk_ids=ev["chunk_ids"],
                                latency_ms=ev["latency_ms"],
                            )
                        )
                        db.commit()
            except OllamaDown as e:
                yield _sse({"type": "error", "detail": f"Model server unavailable. Is Ollama running? ({e})"})

    return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


@app.get("/documents")
def list_documents(db: Session = Depends(get_db)):
    n = func.count(Chunk.id).filter(Chunk.config == CHUNK_CONFIG)
    rows = db.execute(
        select(
            Document.id,
            Document.source,
            Document.title,
            Document.kind,
            Document.created_at,
            n.label("chunks"),
        )
        .outerjoin(Chunk)
        .group_by(Document.id)
        .order_by(Document.created_at.desc(), Document.source)
    )
    return [r._asdict() for r in rows]


@app.get("/documents/{doc_id}")
def get_document(doc_id: int, db: Session = Depends(get_db)):
    doc = db.get(Document, doc_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    return {
        "id": doc.id,
        "source": doc.source,
        "title": doc.title,
        "kind": doc.kind,
        "text": doc.text,
        "pages": doc.pages,
    }


@app.post("/documents", dependencies=[Depends(rate_limit)], status_code=201)
async def upload(file: UploadFile, db: Session = Depends(get_db)):
    name = (file.filename or "").replace("\\", "/").split("/")[-1]
    if not any(name.lower().endswith(ext) for ext in KINDS):
        raise HTTPException(415, f"Unsupported file type. Allowed: {', '.join(KINDS)}")
    data = await file.read(MAX_UPLOAD + 1)
    if len(data) > MAX_UPLOAD:
        raise HTTPException(413, "File larger than 20 MB")
    try:
        doc = ingest(db, f"uploads/{name}", data, [CHUNK_CONFIG])
    except OllamaDown:
        raise
    except Exception as e:  # pypdf raises many types on broken files
        raise HTTPException(422, f"Could not read file: {e}") from e
    return {"id": doc.id, "source": doc.source, "title": doc.title}


@app.delete("/documents/{doc_id}", status_code=204)
def delete_document(doc_id: int, db: Session = Depends(get_db)):
    doc = db.get(Document, doc_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    db.delete(doc)
    db.commit()


@app.get("/eval/summary")
def eval_summary():
    f = RESULTS / "summary.csv"
    if not f.exists():
        return {"rows": [], "charts": [], "report": None}
    rows = list(csv.DictReader(f.open(encoding="utf-8")))
    charts = sorted(p.name for p in (RESULTS / "charts").glob("*.png"))
    report = RESULTS / "report.md"
    return {
        "rows": rows,
        "charts": charts,
        "report": report.read_text(encoding="utf-8") if report.exists() else None,
    }
