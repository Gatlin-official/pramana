"""Draft eval/questions.jsonl from sampled chunks with the local judge model, then write a review checklist.

Every answerable row stores gold *evidence spans* (exact char offsets into the source document),
verified by locating the model's verbatim quote in the passage. Rows whose quote cannot be found
are discarded, never patched.

    python eval/build_questions.py      (needs the corpus ingested and JUDGE_MODEL pulled)
"""

import json
import random
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent / "backend"))

from sqlalchemy import select  # noqa: E402

from app.core.config import JUDGE_MODEL  # noqa: E402
from app.db.models import Chunk, Document  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.generation.llm import chat_json  # noqa: E402

SEED = 42
COUNTS = {"single": 65, "multi": 20, "paraphrase": 20}
SAMPLE_CONFIG = "heading-512"
SKIP = re.compile(
    r"release-notes|_llm-test|management|contributing|fastapi-people|external-links|newsletter|"
    r"help-fastapi|translation|sponsor"
)
STOP = set(
    "what when where which with from that this does have your about into they them then than there "
    "their will would should could using used make need want just like also only some more most such "
    "each other over very".split()
)

UNANSWERABLE = [  # hand-written; each topic's terms were checked to be absent from the corpus
    ("How do I deploy a FastAPI app to AWS Lambda using Mangum?", ["mangum"]),
    ("How do I authenticate users against an LDAP directory in FastAPI?", ["ldap"]),
    ("How do I enable HTTP/3 support in FastAPI?", ["http/3"]),
    ("How do I expose Prometheus metrics from a FastAPI application?", ["prometheus"]),
    ("Can I define gRPC services alongside my REST endpoints in FastAPI?", ["grpc"]),
    ("How do I deploy a FastAPI app to Vercel?", ["vercel"]),
    ("How do I send push notifications with Firebase Cloud Messaging from FastAPI?", ["firebase"]),
    ("How do I run a FastAPI app inside a Jupyter notebook?", ["jupyter"]),
    ("How do I stream live video to the browser with WebRTC in FastAPI?", ["webrtc"]),
    ("How do I provision the infrastructure for a FastAPI deployment with Terraform?", ["terraform"]),
    ("How do I deploy FastAPI as an Azure Functions app?", ["azure functions"]),
    ("What is the recommended way to store FastAPI data in DynamoDB?", ["dynamodb"]),
    ("How do I implement GraphQL subscriptions in FastAPI?", ["graphql subscription"]),
    ("How do I index documents into Elasticsearch from a FastAPI endpoint?", ["elasticsearch"]),
    ("How do I verify Stripe webhook signatures in a FastAPI route?", ["stripe"]),
]

Q_SCHEMA = {
    "type": "object",
    "properties": {
        "question": {"type": "string"},
        "evidence": {"type": "string"},
        "answer": {"type": "string"},
    },
    "required": ["question", "evidence", "answer"],
}
MULTI_SCHEMA = {
    "type": "object",
    "properties": {
        "question": {"type": "string"},
        "evidence_a": {"type": "string"},
        "evidence_b": {"type": "string"},
        "answer": {"type": "string"},
    },
    "required": ["question", "evidence_a", "evidence_b", "answer"],
}
PARA_SCHEMA = {"type": "object", "properties": {"question": {"type": "string"}}, "required": ["question"]}

RULES = (
    "The question must be self-contained (never mention 'the passage', 'the text' or 'the documentation') "
    "and phrased the way a developer would ask it. The evidence must be copied VERBATIM from the passage: "
    "one to three consecutive sentences or code lines, at least 6 words."
)


def find_span(text: str, lo: int, hi: int, quote: str) -> tuple[int, int] | None:
    """Locate a verbatim quote inside text[lo:hi], tolerant of whitespace and markdown emphasis."""
    toks = [t.strip("`*_") for t in quote.split()]
    toks = [t for t in toks if t]
    if len(toks) < 6:
        return None
    pat = r"\s+".join(r"[`*_]*" + re.escape(t) + r"[`*_]*" for t in toks)
    m = re.search(pat, text[lo:hi])
    return (lo + m.start(), lo + m.end()) if m else None


def words(s: str) -> set[str]:
    return {w for w in re.findall(r"[a-z_]{4,}", s.lower()) if w not in STOP}


def overlap(question: str, passage: str) -> float:
    q = words(question)
    return round(len(q & words(passage)) / len(q), 3) if q else 0.0


def ask(prompt: str, schema: dict) -> dict | None:
    try:
        return chat_json([{"role": "user", "content": prompt}], schema, JUDGE_MODEL)
    except (json.JSONDecodeError, KeyError):
        return None


def single(c: Chunk, text: str) -> dict | None:
    out = ask(
        f"Passage from the FastAPI documentation ({c.source}):\n\n{c.text}\n\n"
        f"Write ONE question whose answer is clearly stated in this passage. {RULES} "
        "Also give a one-sentence reference answer.",
        Q_SCHEMA,
    )
    span = out and find_span(text, c.char_start, c.char_end, out["evidence"])
    if not span:
        return None
    return {
        "question": out["question"].strip(),
        "answer": out["answer"].strip(),
        "gold": [{"source": c.source, "start": span[0], "end": span[1]}],
        "evidence": [text[span[0] : span[1]]],
    }


def multi(a: Chunk, b: Chunk, text: str) -> dict | None:
    out = ask(
        f"Two passages from the same FastAPI documentation page ({a.source}).\n\nPASSAGE A:\n{a.text}\n\n"
        f"PASSAGE B:\n{b.text}\n\nWrite ONE question that can only be answered fully by combining information "
        f"from BOTH passages. {RULES} Give evidence_a from passage A and evidence_b from passage B, "
        "plus a one-sentence reference answer.",
        MULTI_SCHEMA,
    )
    if not out:
        return None
    sa = find_span(text, a.char_start, a.char_end, out["evidence_a"])
    sb = find_span(text, b.char_start, b.char_end, out["evidence_b"])
    if not (sa and sb):
        return None
    return {
        "question": out["question"].strip(),
        "answer": out["answer"].strip(),
        "gold": [{"source": a.source, "start": s, "end": e} for s, e in (sa, sb)],
        "evidence": [text[s:e] for s, e in (sa, sb)],
    }


def paraphrase(c: Chunk, text: str) -> dict | None:
    row = single(c, text)
    if not row:
        return None
    out = ask(
        f"Rewrite this developer question so it asks for exactly the same information, but as a beginner who "
        f"does not know the technical vocabulary: avoid the key terms, identifiers and phrases used in the "
        f"passage below; use plain everyday words instead.\n\nQUESTION: {row['question']}\n\nPASSAGE:\n{c.text}",
        PARA_SCHEMA,
    )
    if not out:
        return None
    before, after = overlap(row["question"], c.text), overlap(out["question"], c.text)
    if after > 0.35 or after >= before:  # must be measurably keyword-poor
        return None
    return row | {"question": out["question"].strip(), "original_question": row["question"], "overlap": after}


def main() -> None:
    rng = random.Random(SEED)
    with SessionLocal() as db:
        docs = {d.source: d.text for d in db.scalars(select(Document))}
        rows = db.execute(
            select(Chunk.id, Chunk.text, Chunk.char_start, Chunk.char_end, Chunk.token_count, Document.source)
            .join(Document)
            .where(Chunk.config == SAMPLE_CONFIG)
            .order_by(Chunk.id)
        ).all()
        missing = [q for q, terms in UNANSWERABLE if any(t in txt.lower() for txt in docs.values() for t in terms)]
    if missing:
        sys.exit(f"unanswerable topics found in corpus, fix list: {missing}")

    pool = [r for r in rows if r.token_count >= 120 and not SKIP.search(r.source)]
    rng.shuffle(pool)
    by_doc: dict[str, list] = {}
    for r in pool:
        by_doc.setdefault(r.source, []).append(r)

    out: list[dict] = []
    used: set[int] = set()

    def take(kind: str, make, candidates) -> None:
        got = 0
        for cand in candidates:
            if got == COUNTS[kind]:
                break
            ids = {c.id for c in cand}
            if ids & used:
                continue
            row = make(*cand, docs[cand[0].source])
            print(
                f"  {kind:<10} {got + (row is not None):>3}/{COUNTS[kind]}  {'ok ' if row else 'skip'} {cand[0].source}"
            )
            if row:
                used.update(ids)
                out.append({"type": kind, "answerable": True, **row})
                got += 1
        if got < COUNTS[kind]:
            print(f"WARNING: only {got}/{COUNTS[kind]} {kind} questions")

    # spread singles across documents first: one chunk per doc, then any remaining chunks
    firsts = [v[0] for v in by_doc.values()]
    rng.shuffle(firsts)
    take("single", single, [(c,) for c in firsts + pool])
    pairs = [(v[i], v[j]) for v in by_doc.values() if len(v) >= 3 for i, j in [(0, len(v) // 2), (1, len(v) - 1)]]
    rng.shuffle(pairs)
    take("multi", multi, pairs)
    take("paraphrase", paraphrase, [(c,) for c in reversed(pool)])
    out += [
        {"type": "unanswerable", "answerable": False, "question": q, "gold": [], "evidence": []}
        for q, _ in UNANSWERABLE
    ]

    for i, row in enumerate(out, 1):
        row["id"] = f"q{i:03d}"
        row["reviewed"] = False
    with (HERE / "questions.jsonl").open("w", encoding="utf-8") as f:
        for row in out:
            f.write(json.dumps({"id": row["id"]} | row, ensure_ascii=False) + "\n")
    write_checklist(out, random.Random(7))
    print(f"wrote {len(out)} questions -> eval/questions.jsonl, review sheet -> eval/REVIEW_CHECKLIST.md")


def write_checklist(rows: list[dict], rng: random.Random) -> None:
    sample = sorted(rng.sample(rows, round(len(rows) * 0.3)), key=lambda r: r["id"])
    lines = [
        "# Eval set review checklist (random 30%)",
        "",
        "Questions were drafted by a local LLM. Check each row below, then edit `eval/questions.jsonl`:",
        'fix the `question` text if needed, set `"reviewed": true`, or set `"drop": true` to exclude it.',
        "Gold spans are char offsets into the document text; if the evidence is wrong, drop the row rather",
        "than editing offsets by hand. Re-run `make eval` afterwards (results are cached per question set hash).",
        "",
    ]
    for r in sample:
        lines += [f"## {r['id']} · {r['type']}", "", f"**Q:** {r['question']}", ""]
        if r["answerable"]:
            lines += [f"**Reference answer:** {r['answer']}", ""]
            for g, ev in zip(r["gold"], r["evidence"], strict=True):
                lines += [
                    f"Evidence from `{g['source']}` (chars {g['start']}-{g['end']}):",
                    "",
                    "> " + ev.replace("\n", "\n> "),
                    "",
                ]
            lines += [
                "- [ ] Question is clear and self-contained",
                "- [ ] Evidence actually answers it",
                "- [ ] Reference answer is correct",
                "",
            ]
        else:
            lines += ["- [ ] FastAPI docs truly do not answer this", ""]
    (HERE / "REVIEW_CHECKLIST.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
