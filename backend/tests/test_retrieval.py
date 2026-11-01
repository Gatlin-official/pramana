from app.retrieval import search
from app.retrieval.search import Hit, rerank, retrieve, rrf
from tests.conftest import onehot


def h(cid: int) -> Hit:
    return Hit(cid, 0.0, 1, "s", f"t{cid}", 0, 1, None)


def test_rrf_scores_and_order():
    fused = rrf([[h(1), h(2), h(3)], [h(3), h(1)]], k=60)
    assert [x.chunk_id for x in fused] == [1, 3, 2]
    assert abs(fused[0].score - (1 / 61 + 1 / 62)) < 1e-12
    assert abs(fused[2].score - 1 / 62) < 1e-12


def test_rrf_ties_break_by_id_and_empty():
    assert [x.chunk_id for x in rrf([[h(5)], [h(4)]])] == [4, 5]
    assert rrf([[], []]) == []


def test_rerank_uses_scorer_order():
    out = rerank("q", [h(1), h(2), h(3)], k=2, scorer=lambda q, ts: [0.1, 0.9, 0.5])
    assert [x.chunk_id for x in out] == [2, 3] and out[0].score == 0.9


def test_keyword_ranks_matching_chunk_first(db, toy):
    hits = retrieve(db, "how do I declare dependencies?", "keyword", "toy", k=3)
    assert hits[0].chunk_id == toy[1]
    assert hits[0].text[: hits[0].char_end - hits[0].char_start] == hits[0].text


def test_dense_orders_by_cosine(db, toy, monkeypatch):
    monkeypatch.setattr(search, "embed_query", lambda db, q: onehot(2))
    hits = retrieve(db, "anything", "dense", "toy", k=3)
    assert hits[0].chunk_id == toy[2] and abs(hits[0].score - 1.0) < 1e-6


def test_hybrid_fuses_both(db, toy, monkeypatch):
    monkeypatch.setattr(search, "embed_query", lambda db, q: onehot(0))
    hits = retrieve(db, "CORS middleware origin", "hybrid", "toy", k=3)
    # dense ranks chunk 0 first, keyword ranks chunk 2 first; both appear on top
    assert {hits[0].chunk_id, hits[1].chunk_id} == {toy[0], toy[2]}
