"""Run the experiment grid. One JSON per run in eval/results/runs/, combined eval/results/summary.csv.

    python eval/run_eval.py [--force] [--retrieval-only]

Runs are cached: a run is skipped when its JSON exists for the same question-set hash.
"""

import argparse
import csv
import hashlib
import json
import random
import sys
import time
from collections import namedtuple
from pathlib import Path

import yaml

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE.parent / "backend"))

from metrics import citation_precision, mean, mrr, ndcg_at, percentile, recall_at  # noqa: E402

from app.core.config import JUDGE_MODEL  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.generation import answer as answer_mod  # noqa: E402
from app.generation.llm import chat_json, stream_chat  # noqa: E402
from app.retrieval import search  # noqa: E402

RESULTS = HERE / "results"
RUNS = RESULTS / "runs"
Span = namedtuple("Span", "source char_start char_end")


def load_questions(path: Path = HERE / "questions.jsonl") -> list[dict]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return [r for r in rows if not r.get("drop")]


def qhash(qs: list[dict]) -> str:
    return hashlib.sha256(json.dumps(qs, sort_keys=True).encode()).hexdigest()[:12]


def run_name(config: str, mode: str, rerank: bool) -> str:
    return f"{config}__{mode}__{'rerank' if rerank else 'norerank'}"


# ---------- retrieval ----------


def retrieval_run(db, qs: list[dict], config: str, mode: str, rerank: bool, k: int = 10) -> dict:
    per = []
    for q in qs:
        t = time.perf_counter()
        hits = search.retrieve(db, q["question"], mode, config, k=k, use_rerank=rerank)
        ms = (time.perf_counter() - t) * 1000
        row = {
            "id": q["id"],
            "type": q["type"],
            "answerable": q["answerable"],
            "latency_ms": round(ms, 1),
            "top_score": hits[0].score if hits else None,
            "hits": [[h.source, h.char_start, h.char_end] for h in hits],
        }
        if q["answerable"]:
            row |= score_hits(hits, q["gold"])
        per.append(row)
    return {
        "config": config,
        "mode": mode,
        "rerank": rerank,
        "k": k,
        "metrics": aggregate(per),
        "questions": per,
    }


def score_hits(hits, gold: list[dict]) -> dict:
    return {
        "recall@5": recall_at(hits, gold, 5),
        "recall@10": recall_at(hits, gold, 10),
        "mrr": mrr(hits, gold, 10),
        "ndcg@10": ndcg_at(hits, gold, 10),
    }


def aggregate(per: list[dict]) -> dict:
    ans = [r for r in per if r["answerable"]]
    out = {m: mean([r[m] for r in ans]) for m in ("recall@5", "recall@10", "mrr", "ndcg@10")}
    for t in ("single", "multi", "paraphrase"):
        out[f"recall@5_{t}"] = mean([r["recall@5"] for r in ans if r["type"] == t])
    lat = [r["latency_ms"] for r in per]
    out |= {"n_questions": len(per), "n_answerable": len(ans)}
    out |= {"retrieval_p50_ms": percentile(lat, 50), "retrieval_p95_ms": percentile(lat, 95)}
    return out


# ---------- generation ----------

JUDGE_SCHEMA = {
    "type": "object",
    "properties": {"faithful": {"type": "boolean"}, "reason": {"type": "string"}},
    "required": ["faithful", "reason"],
}


def judge(question: str, answer: str, sources: list[str]) -> dict:
    src = "\n\n".join(f"[{i}] {s}" for i, s in enumerate(sources, 1))
    prompt = (
        "You check answers for faithfulness. An answer is faithful only if EVERY factual claim in it is "
        "directly supported by the SOURCES. Ignore citation formatting and style; unsupported or contradicted "
        f"claims make it unfaithful.\n\nSOURCES:\n{src}\n\nQUESTION: {question}\n\nANSWER: {answer}"
    )
    return chat_json([{"role": "user", "content": prompt}], JUDGE_SCHEMA, JUDGE_MODEL)


def generation_run(db, qs, config, mode, rerank, k=5, llm=stream_chat, judge_fn=judge) -> dict:
    per = []
    for q in qs:
        events = list(answer_mod.answer_stream(db, q["question"], mode, config, rerank, k, llm=llm))
        hits = {h["chunk_id"]: h for h in events[0]["hits"]}
        done = events[-1]
        cited = [hits[c["chunk_id"]] for c in done["citations"]]
        row = {
            "id": q["id"],
            "type": q["type"],
            "answerable": q["answerable"],
            "answer": done["answer"],
            "raw": done["raw"],
            "abstained": done["abstained"],
            "invalid_citations": done["invalid_citations"],
            "cited": [[h["source"], h["char_start"], h["char_end"]] for h in cited],
            "latency_ms": done["latency_ms"],
        }
        if q["answerable"]:
            row["citation_precision"] = citation_precision([Span(*c) for c in row["cited"]], q["gold"])
            if not done["abstained"] and cited:
                row["judge"] = judge_fn(q["question"], done["answer"], [h["text"] for h in cited])
        per.append(row)
    return generation_metrics(per)


def generation_metrics(per: list[dict]) -> dict:
    ans = [r for r in per if r["answerable"]]
    una = [r for r in per if not r["answerable"]]
    judged = [r for r in ans if "judge" in r]
    total = [r["latency_ms"]["total_ms"] for r in per]
    ft = [r["latency_ms"]["first_token_ms"] for r in per if "first_token_ms" in r["latency_ms"]]
    n_markers = sum(len(r["invalid_citations"]) for r in per)
    m = {
        "citation_precision": mean([r.get("citation_precision") for r in ans]),
        "faithfulness": mean([float(r["judge"]["faithful"]) for r in judged]),
        "n_judged": len(judged),
        "abstention_accuracy": mean([float(r["abstained"]) for r in una]),
        "false_abstention_rate": mean([float(r["abstained"]) for r in ans]),
        "answered_with_citation": mean([float(bool(r["cited"])) for r in ans if not r["abstained"]]),
        "invalid_citation_markers": n_markers,
        "e2e_p50_ms": percentile(total, 50),
        "e2e_p95_ms": percentile(total, 95),
        "first_token_p50_ms": percentile(ft, 50),
    }
    return {"metrics": m, "questions": per}


# ---------- abstention threshold calibration ----------


def calibrate(run: dict) -> float:
    """Top-score threshold that keeps 95% of answerable questions above it (fit on answerables only)."""
    scores = [r["top_score"] for r in run["questions"] if r["answerable"] and r["top_score"] is not None]
    return round(percentile(scores, 5), 4)


# ---------- driver ----------


def grid(cfg: dict) -> list[tuple[str, str, bool]]:
    r = cfg["retrieval"]
    configs = [f"fixed-{s}-{o}" for s in r["chunk_size"] for o in r["overlap"]] + r.get("extra_configs", [])
    return [(c, m, rr) for c in configs for m in r["mode"] for rr in r["rerank"]]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--retrieval-only", action="store_true")
    args = ap.parse_args()
    cfg = yaml.safe_load((HERE / "experiments.yaml").read_text())
    qs = load_questions()
    h = qhash(qs)
    RUNS.mkdir(parents=True, exist_ok=True)
    runs: dict[str, dict] = {}

    with SessionLocal() as db:
        for config, mode, rerank in grid(cfg):
            name = run_name(config, mode, rerank)
            f = RUNS / f"{name}.json"
            prev = json.loads(f.read_text()) if f.exists() else None
            if prev and prev.get("questions_hash") == h and not args.force:
                runs[name] = prev
                continue
            t = time.perf_counter()
            res = retrieval_run(db, qs, config, mode, rerank, cfg["retrieval"]["k"])
            res |= {"name": name, "questions_hash": h}
            f.write_text(json.dumps(res, indent=1))
            runs[name] = res
            m = res["metrics"]
            print(f"{name:<40} R@5={m['recall@5']:.3f} MRR={m['mrr']:.3f}  ({time.perf_counter() - t:.0f}s)")

        best = max(runs.values(), key=lambda r: r["metrics"]["recall@5"])
        print(f"best retrieval run: {best['name']}  recall@5={best['metrics']['recall@5']:.3f}")
        if not args.retrieval_only:
            gen = cfg["generation"]
            gconfig = best["config"] if gen["chunk_config"] == "best" else gen["chunk_config"]
            thresholds = {
                "config": gconfig,
                "dense": calibrate(runs[run_name(gconfig, "dense", False)]),
                "rerank": calibrate(runs[run_name(gconfig, "hybrid", True)]),
            }
            (RESULTS / "thresholds.json").write_text(json.dumps(thresholds, indent=2) + "\n")
            answer_mod.MIN_SCORE.update(dense=thresholds["dense"], rerank=thresholds["rerank"])
            for mode in gen["mode"]:
                for rerank in gen["rerank"]:
                    name = run_name(gconfig, mode, rerank)
                    run = runs[name]
                    if run.get("generation", {}).get("questions_hash") == h and not args.force:
                        continue
                    t = time.perf_counter()
                    g = generation_run(db, qs, gconfig, mode, rerank, gen["k"])
                    run["generation"] = g | {"questions_hash": h, "k": gen["k"], "thresholds": thresholds}
                    (RUNS / f"{name}.json").write_text(json.dumps(run, indent=1))
                    gm = g["metrics"]
                    print(
                        f"GEN {name:<36} cite_p={gm['citation_precision']} faith={gm['faithfulness']} "
                        f"abst={gm['abstention_accuracy']}  ({time.perf_counter() - t:.0f}s)"
                    )
    write_summary(runs)
    write_spotcheck(runs)


COLUMNS = ["recall@5", "recall@10", "mrr", "ndcg@10", "recall@5_single", "recall@5_multi",
           "recall@5_paraphrase", "retrieval_p50_ms", "retrieval_p95_ms"]  # fmt: skip
GEN_COLUMNS = ["citation_precision", "faithfulness", "abstention_accuracy", "false_abstention_rate",
               "e2e_p50_ms", "e2e_p95_ms", "first_token_p50_ms", "invalid_citation_markers"]  # fmt: skip


def write_summary(runs: dict[str, dict]) -> None:
    with (RESULTS / "summary.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["run", "config", "mode", "rerank", "n_questions", *COLUMNS, *GEN_COLUMNS])
        for name in sorted(runs):
            r = runs[name]
            g = r.get("generation", {}).get("metrics", {})
            fmt = lambda v: "" if v is None else (round(v, 4) if isinstance(v, float) else v)  # noqa: E731
            w.writerow(
                [name, r["config"], r["mode"], r["rerank"], r["metrics"]["n_questions"]]
                + [fmt(r["metrics"][c]) for c in COLUMNS]
                + [fmt(g.get(c)) for c in GEN_COLUMNS]
            )
    print(f"wrote {RESULTS / 'summary.csv'} ({len(runs)} runs)")


def write_spotcheck(runs: dict[str, dict]) -> None:
    """20 random judged answers for a human to label; report.py computes judge agreement from it."""
    out = RESULTS / "judge_spotcheck.jsonl"
    if out.exists():
        return  # never overwrite human labels
    judged = [
        (name, q)
        for name, r in sorted(runs.items())
        for q in r.get("generation", {}).get("questions", [])
        if "judge" in q
    ]
    if not judged:
        return
    qtext = {q["id"]: q for q in load_questions()}
    with out.open("w", encoding="utf-8") as f:
        for name, q in random.Random(11).sample(judged, min(20, len(judged))):
            row = {
                "run": name,
                "id": q["id"],
                "question": qtext[q["id"]]["question"],
                "answer": q["answer"],
                "cited": q["cited"],
                "judge_faithful": q["judge"]["faithful"],
                "judge_reason": q["judge"]["reason"],
                "human_faithful": None,
            }
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"wrote {out}: set human_faithful true/false on each row, then run eval/report.py")


if __name__ == "__main__":
    main()
