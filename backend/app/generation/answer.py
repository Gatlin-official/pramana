"""Cited answer generation: prompt, abstention, citation validation, timed event stream."""

import json
import re
import time
from collections.abc import Callable, Iterator

from sqlalchemy.orm import Session

from app.core.config import CHUNK_CONFIG, ROOT
from app.generation.llm import stream_chat
from app.retrieval import search
from app.retrieval.search import Hit

NOT_FOUND = "Not found in the documents."
SENTINEL = "NOT_FOUND"
# Below these top scores we skip the LLM and abstain. `make eval` calibrates them for the
# best chunk config (5th percentile of answerable questions' top score) into thresholds.json.
MIN_SCORE = {"dense": 0.0, "rerank": 0.0}
_cal = ROOT / "eval" / "results" / "thresholds.json"
if _cal.exists() and (t := json.loads(_cal.read_text()))["config"] == CHUNK_CONFIG:
    MIN_SCORE.update(dense=t["dense"], rerank=t["rerank"])

SYSTEM = (
    "You answer questions about documentation using ONLY the numbered sources provided. "
    "Cite every claim with the source number in square brackets, like [1] or [2][3]. "
    "Never use outside knowledge. Keep the answer short and direct. "
    f"If the sources do not contain the answer, reply with exactly: {SENTINEL}"
)

MARKER = re.compile(r"\[(\d+(?:\s*,\s*\d+)*)\]")
ABSTAIN = re.compile(r"NOT_FOUND|not found in the (provided )?(documents|sources)|do(es)? not contain", re.I)


REMINDER = "\n\nAnswer from the sources only, and end every sentence with its source number like [1]."
# A small local model needs to *see* the format: one cited answer and one abstention, then the real question.
# Picked over zero-shot variants on a 7-question probe (zero-shot: bare "[1] [2]" or no citations).
FEW_SHOT = [
    {
        "role": "user",
        "content": "Sources:\n[1] (tutorial/body.md)\nTo declare a request body, you use Pydantic models.\n\n"
        "[2] (tutorial/cookies.md)\nYou can define Cookie parameters the same way you define Query parameters."
        f"\n\nQuestion: How do I read a cookie and a request body?{REMINDER}",
    },
    {
        "role": "assistant",
        "content": "Declare a Cookie parameter the same way you declare a Query parameter [2]. "
        "For the request body, declare a Pydantic model [1].",
    },
    {
        "role": "user",
        "content": "Sources:\n[1] (tutorial/body.md)\nTo declare a request body, you use Pydantic models."
        f"\n\nQuestion: How do I send email?{REMINDER}",
    },
    {"role": "assistant", "content": SENTINEL},
]


def build_messages(question: str, hits: list[Hit]) -> list[dict]:
    sources = "\n\n".join(f"[{i}] ({h.source})\n{h.text}" for i, h in enumerate(hits, 1))
    user = f"Sources:\n{sources}\n\nQuestion: {question}{REMINDER}"
    return [{"role": "system", "content": SYSTEM}, *FEW_SHOT, {"role": "user", "content": user}]


def validate_citations(answer: str, hits: list[Hit]) -> tuple[str, list[dict], list[int]]:
    """Keep markers that map to a retrieved chunk, strip the rest. Returns (answer, citations, invalid)."""
    used: list[int] = []
    invalid: list[int] = []

    def fix(m: re.Match) -> str:
        nums = [int(n) for n in re.findall(r"\d+", m.group(1))]
        good = [n for n in nums if 1 <= n <= len(hits)]
        invalid.extend(n for n in nums if n not in good)
        used.extend(n for n in good if n not in used)
        return "".join(f"[{n}]" for n in good)

    clean = MARKER.sub(fix, answer)
    citations = [
        {
            "n": n,
            "chunk_id": hits[n - 1].chunk_id,
            "doc_id": hits[n - 1].doc_id,
            "source": hits[n - 1].source,
            "char_start": hits[n - 1].char_start,
            "char_end": hits[n - 1].char_end,
            "page": hits[n - 1].page,
        }
        for n in sorted(used)
    ]
    return re.sub(r"[ \t]+([.,;:])", r"\1", clean).strip(), citations, invalid


def low_confidence(hits: list[Hit], mode: str, rerank: bool) -> bool:
    if not hits:
        return True
    if rerank:
        return hits[0].score < MIN_SCORE["rerank"]
    if mode == "dense":
        return hits[0].score < MIN_SCORE["dense"]
    return False  # keyword / RRF scores are not calibrated; rely on the model's own abstention


def is_abstention(text: str) -> bool:
    return bool(ABSTAIN.search(text))


def answer_stream(
    db: Session,
    question: str,
    mode: str,
    config: str,
    rerank: bool = False,
    k: int = 5,
    llm: Callable[[list[dict]], Iterator[str]] = stream_chat,
) -> Iterator[dict]:
    """Yields {'type': 'retrieval'|'token'|'done', ...}. The 'done' event carries the validated result."""
    t0 = time.perf_counter()
    lat: dict[str, float] = {}
    pool = search.RERANK_POOL if rerank else k
    hits = {"dense": search.dense, "keyword": search.keyword, "hybrid": search.hybrid}[mode](db, question, config, pool)
    lat["retrieve_ms"] = (time.perf_counter() - t0) * 1000
    if rerank:
        t = time.perf_counter()
        hits = search.rerank(question, hits, k)
        lat["rerank_ms"] = (time.perf_counter() - t) * 1000
    yield {"type": "retrieval", "hits": [h.__dict__ for h in hits]}

    raw = ""
    if low_confidence(hits, mode, rerank):
        abstained, answer, citations, invalid = True, NOT_FOUND, [], []
    else:
        t = time.perf_counter()
        for tok in llm(build_messages(question, hits)):
            if not raw:
                lat["first_token_ms"] = (time.perf_counter() - t0) * 1000
            raw += tok
            yield {"type": "token", "text": tok}
        lat["generate_ms"] = (time.perf_counter() - t) * 1000
        answer, citations, invalid = validate_citations(raw, hits)
        abstained = is_abstention(raw)
        if abstained:
            answer, citations = NOT_FOUND, []
    lat["total_ms"] = (time.perf_counter() - t0) * 1000
    yield {
        "type": "done",
        "answer": answer,
        "raw": raw,
        "abstained": abstained,
        "citations": citations,
        "invalid_citations": invalid,
        "mode": mode,
        "rerank": rerank,
        "config": config,
        "chunk_ids": [h.chunk_id for h in hits],
        "latency_ms": {k_: round(v, 1) for k_, v in lat.items()},
    }
