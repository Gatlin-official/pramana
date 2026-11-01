"""CI smoke eval: 10-question fixture over a toy corpus, stubbed embeddings, LLM and judge."""

import hashlib
import json
import math
import re
from pathlib import Path

import pytest
import run_eval

from app.db.models import Chunk, Document
from app.ingest.chunkers import chunk
from app.retrieval import search
from tests.conftest import db  # noqa: F401  (rolled-back session fixture)

FIX = json.loads((Path(__file__).parent / "fixtures" / "smoke.json").read_text())
CFG = "fixed-24-0"


def bow(text: str) -> list[float]:
    """Hashed bag-of-words vector: a deterministic stand-in for the embedding model."""
    v = [0.0] * 768
    for w in re.findall(r"[a-z]+", text.lower()):
        v[int(hashlib.md5(w.encode()).hexdigest(), 16) % 768] += 1
    n = math.sqrt(sum(x * x for x in v)) or 1
    return [x / n for x in v]


def stub_llm(messages):
    user = messages[-1]["content"]
    yield ("NOT_FOUND" if re.search(r"Kafka|Peru", user) else "Here is the answer [1] and a bogus one [9].")


@pytest.fixture
def smoke(db, monkeypatch):  # noqa: F811
    monkeypatch.setattr(search, "embed_query", lambda db, q: bow(q))
    for src, text in FIX["docs"].items():
        doc = Document(source=f"smoke/{src}", title=src, kind="md", text=text)
        db.add(doc)
        db.flush()
        for i, (s, e, n) in enumerate(chunk(text, CFG)):
            db.add(Chunk(doc_id=doc.id, config=CFG, ordinal=i, text=text[s:e], token_count=n,
                         char_start=s, char_end=e, embedding=bow(text[s:e])))  # fmt: skip
    db.flush()
    qs = []
    for q in FIX["questions"]:
        gold = []
        for ev in q["evidence"]:
            src = next(s for s, t in FIX["docs"].items() if ev in t)
            start = FIX["docs"][src].index(ev)
            gold.append({"source": f"smoke/{src}", "start": start, "end": start + len(ev)})
        qs.append({**q, "gold": gold})
    return db, qs


def test_smoke_retrieval(smoke):
    s, qs = smoke
    for mode in search.MODES:
        m = run_eval.retrieval_run(s, qs, CFG, mode, False, k=10)["metrics"]
        assert m["n_questions"] == 10 and m["n_answerable"] == 8
        assert 0.5 <= m["recall@5"] <= 1 and 0 < m["mrr"] <= 1 and 0 < m["ndcg@10"] <= 1
    keyword = run_eval.retrieval_run(s, qs, CFG, "keyword", False)["metrics"]
    assert keyword["recall@5_single"] == 1.0  # literal questions; the paraphrase one is meant to miss


def test_smoke_generation(smoke):
    s, qs = smoke
    g = run_eval.generation_run(s, qs, CFG, "hybrid", False, k=3, llm=stub_llm,
                                judge_fn=lambda q, a, s: {"faithful": True, "reason": "stub"})  # fmt: skip
    m = g["metrics"]
    assert m["abstention_accuracy"] == 1.0 and m["false_abstention_rate"] == 0.0
    assert m["invalid_citation_markers"] == 8  # every answer's [9] was stripped
    assert 0 <= m["citation_precision"] <= 1 and m["faithfulness"] == 1.0 and m["n_judged"] == 8
