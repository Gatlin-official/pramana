import json

from fastapi.testclient import TestClient

from app import main
from app.ingest.embed import OllamaDown

client = TestClient(main.app)


def test_ask_validates_mode():
    assert client.post("/ask", json={"question": "x", "mode": "magic"}).status_code == 422


def test_ask_reports_ollama_down_as_sse_error(monkeypatch):
    def boom(*a, **kw):
        raise OllamaDown("connection refused")
        yield  # pragma: no cover

    monkeypatch.setattr(main, "answer_stream", boom)
    r = client.post("/ask", json={"question": "hi"})
    assert r.status_code == 200
    ev = [json.loads(line[6:]) for line in r.text.splitlines() if line.startswith("data: ")]
    assert ev[-1]["type"] == "error" and "Ollama" in ev[-1]["detail"]


def test_upload_rejects_unknown_type():
    r = client.post("/documents", files={"file": ("x.exe", b"MZ", "application/octet-stream")})
    assert r.status_code == 415


def test_upload_ollama_down_is_503(monkeypatch):
    def down(*a, **kw):
        raise OllamaDown("refused")

    monkeypatch.setattr(main, "ingest", down)
    r = client.post("/documents", files={"file": ("notes.txt", b"hello", "text/plain")})
    assert r.status_code == 503 and "Ollama" in r.json()["detail"]


def test_rate_limit(monkeypatch):
    monkeypatch.setattr(main, "RATE_LIMIT_PER_MIN", 2)
    main._hits.clear()
    codes = [client.post("/documents", files={"file": ("x.exe", b"", "x")}).status_code for _ in range(3)]
    assert codes == [415, 415, 429]
    main._hits.clear()


def test_missing_document_404():
    assert client.get("/documents/999999999").status_code == 404
