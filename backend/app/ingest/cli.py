"""python -m app.ingest.cli corpus  -> fetch pinned FastAPI docs and ingest every eval chunk config."""

import json
import subprocess
import sys
import time
from pathlib import Path

from sqlalchemy import func, select

from app.core.config import CHUNK_CONFIG, ROOT
from app.db.models import Chunk, Document
from app.db.session import SessionLocal
from app.ingest.pipeline import ingest

REPO = "https://github.com/fastapi/fastapi"
COMMIT = "45cb2252c737906f37544f5ba6bee0295fb81468"  # pinned for reproducible eval
SUBDIR = "docs/en/docs"
DEST = ROOT / "corpus" / "fastapi"
EVAL_CONFIGS = [f"fixed-{s}-{o}" for s in (256, 512, 1024) for o in (0, 15)] + ["heading-512"]


def fetch() -> Path:
    if not (DEST / ".git").exists():
        DEST.mkdir(parents=True, exist_ok=True)
        for cmd in (
            ["git", "init", "-q"],
            ["git", "remote", "add", "origin", REPO],
            ["git", "sparse-checkout", "set", SUBDIR],
            ["git", "fetch", "-q", "--depth", "1", "origin", COMMIT],
            ["git", "checkout", "-q", "FETCH_HEAD"],
        ):
            subprocess.run(cmd, cwd=DEST, check=True)
    return DEST / SUBDIR


def main(target: str) -> None:
    if target != "corpus":
        sys.exit("usage: python -m app.ingest.cli corpus")
    docs = fetch()
    files = sorted(docs.rglob("*.md"))
    manifest = {"source": REPO, "commit": COMMIT, "subdir": SUBDIR, "file_count": len(files)}
    (ROOT / "eval" / "corpus_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    configs = sorted(set(EVAL_CONFIGS + [CHUNK_CONFIG]))
    t0 = time.perf_counter()
    with SessionLocal() as db:
        for i, f in enumerate(files, 1):
            ingest(db, f.relative_to(docs).as_posix(), f.read_bytes(), configs)
            if i % 25 == 0:
                print(f"  {i}/{len(files)} files  {time.perf_counter() - t0:.0f}s", flush=True)
        counts = db.execute(select(Chunk.config, func.count()).group_by(Chunk.config)).all()
        ndocs = db.scalar(select(func.count()).select_from(Document))
    print(f"ingested {len(files)} files ({ndocs} docs in db) in {time.perf_counter() - t0:.1f}s")
    for cfg, n in sorted(counts):
        print(f"  {cfg:>14}: {n} chunks")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "corpus")
