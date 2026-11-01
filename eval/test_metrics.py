import math
from dataclasses import dataclass

from metrics import citation_precision, covers, mrr, ndcg_at, percentile, recall_at


@dataclass
class C:
    source: str
    char_start: int
    char_end: int


G1 = {"source": "a.md", "start": 100, "end": 200}
G2 = {"source": "b.md", "start": 0, "end": 50}


def test_covers_overlap_rules():
    assert covers(C("a.md", 0, 1000), G1)  # chunk contains span
    assert covers(C("a.md", 150, 400), G1)  # 50/100 overlap = half of the shorter
    assert not covers(C("a.md", 160, 400), G1)  # 40/100 < half
    assert not covers(C("b.md", 100, 200), G1)  # other source
    assert covers(C("a.md", 120, 140), G1)  # tiny chunk fully inside span


def test_recall_mrr_ndcg():
    hits = [C("x.md", 0, 10), C("a.md", 90, 210), C("b.md", 0, 60)]
    assert recall_at(hits, [G1, G2], 1) == 0
    assert recall_at(hits, [G1, G2], 2) == 0.5
    assert recall_at(hits, [G1, G2], 3) == 1
    assert mrr(hits, [G1, G2]) == 0.5
    expected = (1 / math.log2(3) + 1 / math.log2(4)) / (1 + 1 / math.log2(3))
    assert abs(ndcg_at(hits, [G1, G2]) - expected) < 1e-12


def test_ndcg_counts_each_gold_once():
    dup = [C("a.md", 100, 200), C("a.md", 100, 200)]
    assert abs(ndcg_at(dup, [G1]) - 1.0) < 1e-12
    assert ndcg_at([C("z.md", 0, 1)], [G1]) == 0 and mrr([], [G1]) == 0


def test_citation_precision_and_percentile():
    assert citation_precision([C("a.md", 100, 200), C("z.md", 0, 5)], [G1]) == 0.5
    assert citation_precision([], [G1]) is None
    assert percentile([1, 2, 3, 4, 5], 50) == 3
    assert percentile([10], 95) == 10
