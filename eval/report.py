"""Build charts + report.md from eval/results. Every number is read from input files; missing -> "—"."""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

EVAL = Path(__file__).resolve().parent
RESULTS = EVAL / "results"
CHARTS = RESULTS / "charts"
MODES = ["dense", "keyword", "hybrid"]
MODE_COLOR = {"dense": "#2a78d6", "keyword": "#eb6834", "hybrid": "#1baf7a"}  # dataviz reference slots 1-3
INK, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#e6e5e0", "#fcfcfb"
TYPES = ["single", "multi", "paraphrase"]
RETR = ["recall@5", "recall@10", "mrr", "ndcg@10", "recall@5_single", "recall@5_multi", "recall@5_paraphrase"]
GEN = ["citation_precision", "faithfulness", "abstention_accuracy", "false_abstention_rate"]
GEN_MS = ["e2e_p50_ms", "e2e_p95_ms", "first_token_p50_ms"]
DASH = "—"

Row = dict[str, object]

plt.rcParams.update(
    {
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "axes.edgecolor": GRID,
        "axes.labelcolor": MUTED,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "text.color": INK,
        "font.size": 10,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "axes.grid.axis": "y",
        "grid.color": GRID,
        "axes.axisbelow": True,
    }
)


def num(v: str) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def load_runs() -> list[Row]:
    path = RESULTS / "summary.csv"
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        rows: list[Row] = []
        for r in csv.DictReader(f):
            row: Row = {k: num(v) for k, v in r.items()}
            row.update(run=r["run"], config=r["config"], mode=r["mode"], rerank=r["rerank"] == "True")
            rows.append(row)
    return rows


def pct(v: object) -> str:
    return DASH if v is None else f"{float(v) * 100:.1f}%"  # type: ignore[arg-type]


def ms(v: object) -> str:
    return DASH if v is None else str(round(float(v)))  # type: ignore[arg-type]


def table(headers: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    return "\n".join(lines + ["| " + " | ".join(r) + " |" for r in rows])


def find(runs: list[Row], config: object, mode: str, rerank: bool) -> Row | None:
    return next((r for r in runs if r["config"] == config and r["mode"] == mode and r["rerank"] == rerank), None)


def get(r: Row | None, key: str) -> float:
    v = None if r is None else r.get(key)
    return float(v) if v is not None else 0.0  # type: ignore[arg-type]


def config_key(c: str) -> tuple[int, int, str]:
    parts = c.split("-")
    return (0, int(parts[1]), parts[2]) if parts[0] == "fixed" else (1, 0, c)


def bar_labels(ax: plt.Axes, bars: object, vals: list[float | None], fmt: str = "{:.1%}") -> None:
    for b, v in zip(bars, vals, strict=True):  # type: ignore[call-overload]
        if v is not None:
            ax.annotate(fmt.format(v), (b.get_x() + b.get_width() / 2, b.get_height()), xytext=(0, 3),
                        textcoords="offset points", ha="center", fontsize=8, color=MUTED)  # fmt: skip


def save(fig: plt.Figure, name: str) -> None:
    fig.tight_layout()
    fig.savefig(CHARTS / name, dpi=150, facecolor=SURFACE)
    plt.close(fig)


RERANK_LEGEND = [Patch(facecolor="#bbbbbb", alpha=0.5, hatch="///", label="rerank off"),
                 Patch(facecolor="#888888", label="rerank on")]  # fmt: skip


def chart_recall_by_mode(runs: list[Row], best: Row) -> None:
    fig, ax = plt.subplots(figsize=(5.4, 3.4))
    for i, m in enumerate(MODES):
        for j, rr in enumerate([False, True]):
            r = find(runs, best["config"], m, rr)
            v = r["recall@5"] if r else None
            b = ax.bar(i + (j - 0.5) * 0.38, get(r, "recall@5"), 0.36, color=MODE_COLOR[m], alpha=1 if rr else 0.5,
                       hatch=None if rr else "///", edgecolor=SURFACE, linewidth=2)  # fmt: skip
            bar_labels(ax, b, [v])  # type: ignore[list-item]
    ax.set_xticks(range(3), MODES)
    ax.set_ylim(0, 1.08)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f"{y:.0%}"))
    ax.set_title(f"Recall@5 by mode — {best['config']}", loc="left", fontsize=11)
    ax.legend(handles=RERANK_LEGEND, frameon=False, fontsize=8, loc="upper left")
    save(fig, "recall_by_mode.png")


def chart_heatmap(runs: list[Row], configs: list[str]) -> None:
    cols = [(m, rr) for m in MODES for rr in (False, True)]
    grid = [[find(runs, c, m, rr) for m, rr in cols] for c in configs]
    vals = [[float(r["recall@5"]) if r and r["recall@5"] is not None else float("nan") for r in row] for row in grid]  # type: ignore[arg-type]
    fig, ax = plt.subplots(figsize=(6.4, 0.45 * len(configs) + 1.6))
    im = ax.imshow(vals, cmap="Blues", vmin=0, vmax=1, aspect="auto")
    for i, row in enumerate(vals):
        for j, v in enumerate(row):
            txt, col = (DASH, MUTED) if v != v else (f"{v:.1%}", "white" if v > 0.6 else INK)
            ax.text(j, i, txt, ha="center", va="center", fontsize=8, color=col)
    ax.set_xticks(range(len(cols)), [f"{m}\n{'rerank' if rr else 'no rerank'}" for m, rr in cols], fontsize=8)
    ax.set_yticks(range(len(configs)), configs, fontsize=8)
    ax.grid(False)
    ax.set_title("Recall@5 by chunk config", loc="left", fontsize=11)
    fig.colorbar(im, ax=ax, fraction=0.03, format=plt.FuncFormatter(lambda y, _: f"{y:.0%}"))
    save(fig, "chunking_heatmap.png")


def chart_by_type(runs: list[Row], best: Row) -> None:
    fig, ax = plt.subplots(figsize=(5.8, 3.4))
    for j, m in enumerate(MODES):
        r = find(runs, best["config"], m, True)
        vals = [r.get(f"recall@5_{t}") if r else None for t in TYPES]
        b = ax.bar([i + (j - 1) * 0.27 for i in range(3)], [get(r, f"recall@5_{t}") for t in TYPES], 0.25,
                   color=MODE_COLOR[m], label=m, edgecolor=SURFACE, linewidth=2)  # fmt: skip
        bar_labels(ax, b, vals)  # type: ignore[arg-type]
    ax.set_xticks(range(3), TYPES)
    ax.set_ylim(0, 1.1)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f"{y:.0%}"))
    ax.set_title(f"Recall@5 by question type — {best['config']}, rerank on", loc="left", fontsize=11)
    ax.legend(frameon=False, fontsize=8, ncol=3, loc="upper right")
    save(fig, "recall_by_type.png")


def chart_latency(runs: list[Row], best: Row) -> None:
    panels = [
        ("retrieval", f"Retrieval latency — {best['config']}", [r for r in runs if r["config"] == best["config"]])
    ]
    gen = [r for r in runs if r.get("e2e_p50_ms") is not None]
    if gen:
        panels.append(("e2e", "End-to-end latency (runs with generation)", gen))
    fig, axes = plt.subplots(len(panels), 1, figsize=(6.4, 3.2 * len(panels)), squeeze=False)
    for ax, (key, title, rows) in zip(axes[:, 0], panels, strict=True):
        rows = sorted(rows, key=lambda r: (config_key(str(r["config"])), MODES.index(str(r["mode"])), r["rerank"]))
        for i, r in enumerate(rows):
            c, on = MODE_COLOR[str(r["mode"])], bool(r["rerank"])
            p50, p95 = get(r, f"{key}_p50_ms"), get(r, f"{key}_p95_ms")
            ax.plot([i, i], [p50, p95], color=c, linewidth=2, alpha=1 if on else 0.5)
            ax.plot(i, p50, "o", color=c, markersize=8, markeredgecolor=SURFACE, markeredgewidth=2)
            ax.plot(i, p95, "D", color=c, markersize=7, markeredgecolor=SURFACE, markeredgewidth=2)
        labels = [f"{r['mode']}\n{'rerank' if r['rerank'] else 'no rr'}" for r in rows]
        if key == "e2e":
            labels = [f"{r['config']}\n{lab}" for r, lab in zip(rows, labels, strict=True)]
        ax.set_xticks(range(len(rows)), labels, fontsize=7)
        ax.set_ylabel("ms")
        ax.set_ylim(bottom=0)
        ax.set_title(title, loc="left", fontsize=11)
    axes[0, 0].legend(handles=[plt.Line2D([], [], marker="o", ls="", color=MUTED, label="p50"),
                               plt.Line2D([], [], marker="D", ls="", color=MUTED, label="p95")],
                      frameon=False, fontsize=8)  # fmt: skip
    save(fig, "latency.png")


def read_json(path: Path) -> dict | None:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def main() -> None:
    runs = load_runs()
    if not runs:
        print("summary.csv missing or empty; nothing to report")
        return
    CHARTS.mkdir(parents=True, exist_ok=True)
    best = max(runs, key=lambda r: get(r, "recall@5"))
    configs = sorted({str(r["config"]) for r in runs}, key=config_key)
    chart_recall_by_mode(runs, best)
    chart_heatmap(runs, configs)
    chart_by_type(runs, best)
    chart_latency(runs, best)

    man = read_json(EVAL / "corpus_manifest.json") or {}
    qs = [json.loads(line) for line in (EVAL / "questions.jsonl").read_text(encoding="utf-8").splitlines() if line]
    counts = Counter(q["type"] for q in qs if not q.get("drop"))
    thr = read_json(RESULTS / "thresholds.json") or {}
    spot_path = RESULTS / "judge_spotcheck.jsonl"
    spot = (
        [json.loads(x) for x in spot_path.read_text(encoding="utf-8").splitlines() if x] if spot_path.exists() else []
    )
    labelled = [s for s in spot if s.get("human_faithful") is not None]
    agree = sum(s["human_faithful"] == s["judge_faithful"] for s in labelled)
    base = find(runs, best["config"], "dense", False)

    def name(r: Row) -> str:
        return f"{r['config']} / {r['mode']} / {'rerank' if r['rerank'] else 'no rerank'}"

    def retr_row(r: Row) -> list[str]:
        lat = [ms(r["retrieval_p50_ms"]), ms(r["retrieval_p95_ms"])]
        return [name(r), ms(r["n_questions"])] + [pct(r[c]) for c in RETR] + lat

    retr_hdr = ["Run", "n", *RETR, "p50 ms", "p95 ms"]
    ordered = sorted(runs, key=lambda r: (config_key(str(r["config"])), MODES.index(str(r["mode"])), r["rerank"]))
    gen_runs = [r for r in ordered if any(r.get(c) is not None for c in GEN)]
    gen_tbl = table(["Run", *GEN, *GEN_MS, "invalid markers"],
                    [[name(r)] + [pct(r[c]) for c in GEN] + [ms(r[c]) for c in GEN_MS]
                     + [ms(r["invalid_citation_markers"])] for r in gen_runs])  # fmt: skip
    thr_txt = (
        f"config `{thr.get('config', DASH)}`, dense `{thr.get('dense', DASH)}`, rerank `{thr.get('rerank', DASH)}`"
    )
    md = [
        "# Pramana retrieval eval",
        f"Corpus: {man.get('source', DASH)} @ `{str(man.get('commit', DASH))[:12]}`, "
        f"`{man.get('subdir', DASH)}`, {man.get('file_count', DASH)} files.",
        f"Runs in summary: {len(runs)} of 42.",
        "## Question set",
        table(
            ["Type", "Count"],
            [[t, str(counts.get(t, 0))] for t in [*TYPES, "unanswerable"]] + [["total", str(sum(counts.values()))]],
        ),  # fmt: skip
        "## Best run",
        f"Highest recall@5: **{name(best)}**.",
        table(retr_hdr, [retr_row(best)]),
        "## Charts",
        "Recall@5 per mode at the best config, rerank off vs on.\n\n![](charts/recall_by_mode.png)",
        "Recall@5 per chunk config and mode/rerank.\n\n![](charts/chunking_heatmap.png)",
        "Recall@5 per question type at the best config, rerank on.\n\n![](charts/recall_by_type.png)",
        "Latency p50/p95.\n\n![](charts/latency.png)",
        "## Top 10 runs by recall@5",
        table(retr_hdr, [retr_row(r) for r in sorted(runs, key=lambda r: -get(r, "recall@5"))[:10]]),
        "## All runs",
        table(retr_hdr, [retr_row(r) for r in ordered]),
        "## Generation",
        gen_tbl if gen_runs else "[generation] pending",
        "## Calibrated abstention thresholds",
        thr_txt if thr else "[thresholds] pending",
        "## Judge agreement (faithfulness spot-check)",
        f"{agree}/{len(labelled)} agree ({pct(agree / len(labelled))}); {len(labelled)} of {len(spot)} rows labelled."
        if labelled
        else f"[human labels] pending ({len(spot)} rows to label).",
    ]
    (RESULTS / "report.md").write_text("\n\n".join(md) + "\n", encoding="utf-8")
    print(f"runs: {len(runs)}/42")
    print(f"best: {name(best)}")
    print(f"best recall@5: {pct(best['recall@5'])}")
    print(f"baseline dense/no-rerank recall@5 @ {best['config']}: {pct(base['recall@5'] if base else None)}")
    print(f"wrote {RESULTS / 'report.md'} and 4 charts in {CHARTS}")


if __name__ == "__main__":
    main()
