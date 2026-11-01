from app.generation.answer import NOT_FOUND, answer_stream, is_abstention, validate_citations
from app.retrieval import search
from app.retrieval.search import Hit
from tests.conftest import onehot

HITS = [Hit(i, 1.0, 1, "a.md", f"text {i}", i * 10, i * 10 + 5, None) for i in (11, 22)]


def test_validate_keeps_valid_strips_invalid():
    ans, cites, invalid = validate_citations("Use Depends [1]. Also CORS [2, 7]. Bogus [9].", HITS)
    assert ans == "Use Depends [1]. Also CORS [2]. Bogus."
    assert [c["chunk_id"] for c in cites] == [11, 22]
    assert invalid == [7, 9]
    assert cites[0]["char_start"] == 110


def test_abstention_detection():
    assert is_abstention("NOT_FOUND")
    assert is_abstention("The sources do not contain this information.")
    assert not is_abstention("Use Depends [1].")


def test_answer_stream_with_stub_llm(db, toy, monkeypatch):
    monkeypatch.setattr(search, "embed_query", lambda db, q: onehot(1))
    events = list(
        answer_stream(db, "dependencies?", "dense", "toy", k=2, llm=lambda m: iter(["Use ", "Depends [1][5]."]))
    )
    done = events[-1]
    assert [e["type"] for e in events] == ["retrieval", "token", "token", "done"]
    assert done["answer"] == "Use Depends [1]." and done["invalid_citations"] == [5]
    assert done["citations"][0]["chunk_id"] == toy[1]
    assert {"retrieve_ms", "generate_ms", "total_ms"} <= done["latency_ms"].keys()


def test_answer_stream_abstains(db, toy, monkeypatch):
    monkeypatch.setattr(search, "embed_query", lambda db, q: onehot(0))
    done = list(answer_stream(db, "weather?", "dense", "toy", llm=lambda m: iter(["NOT_FOUND"])))[-1]
    assert done["abstained"] and done["answer"] == NOT_FOUND and done["citations"] == []
