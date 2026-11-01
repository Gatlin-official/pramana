"""Retrieval and answer metrics.

Gold labels are evidence *spans* (source, start, end) in the original document text, not chunk ids,
so one question set scores every chunking. A retrieved chunk "covers" a gold span when they share
the same source and overlap by at least half of the shorter of the two.
"""

import math
import statistics
from collections.abc import Sequence
from typing import Protocol


class Span(Protocol):
    source: str
    char_start: int
    char_end: int


Gold = dict  # {"source": str, "start": int, "end": int}


def covers(chunk: Span, gold: Gold, min_frac: float = 0.5) -> bool:
    if chunk.source != gold["source"]:
        return False
    inter = min(chunk.char_end, gold["end"]) - max(chunk.char_start, gold["start"])
    shorter = min(chunk.char_end - chunk.char_start, gold["end"] - gold["start"])
    return inter > 0 and inter >= min_frac * max(shorter, 1)


def _gains(hits: Sequence[Span], golds: list[Gold], k: int) -> list[int]:
    """Binary gain per rank: 1 if the hit covers a gold span not already covered higher up."""
    seen: set[int] = set()
    out = []
    for h in hits[:k]:
        new = [i for i, g in enumerate(golds) if i not in seen and covers(h, g)]
        seen.update(new)
        out.append(1 if new else 0)
    return out


def recall_at(hits: Sequence[Span], golds: list[Gold], k: int) -> float:
    """Fraction of gold spans covered by the top-k hits."""
    if not golds:
        return 0.0
    return sum(any(covers(h, g) for h in hits[:k]) for g in golds) / len(golds)


def mrr(hits: Sequence[Span], golds: list[Gold], k: int = 10) -> float:
    for rank, h in enumerate(hits[:k], 1):
        if any(covers(h, g) for g in golds):
            return 1 / rank
    return 0.0


def ndcg_at(hits: Sequence[Span], golds: list[Gold], k: int = 10) -> float:
    dcg = sum(g / math.log2(r + 1) for r, g in enumerate(_gains(hits, golds, k), 1))
    ideal = sum(1 / math.log2(r + 1) for r in range(1, min(len(golds), k) + 1))
    return dcg / ideal if ideal else 0.0


def citation_precision(cited: Sequence[Span], golds: list[Gold]) -> float | None:
    """Share of cited chunks that cover some gold span. None when nothing was cited."""
    if not cited:
        return None
    return sum(any(covers(c, g) for g in golds) for c in cited) / len(cited)


def percentile(values: Sequence[float], p: int) -> float:
    if not values:
        return float("nan")
    if len(values) == 1:
        return float(values[0])
    return statistics.quantiles(values, n=100, method="inclusive")[p - 1]


def mean(values: Sequence[float | None]) -> float | None:
    vals = [v for v in values if v is not None]
    return sum(vals) / len(vals) if vals else None
