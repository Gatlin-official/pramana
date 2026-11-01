import json
from collections.abc import Iterator

import httpx

from app.core.config import LLM_MODEL, OLLAMA_URL
from app.ingest.embed import OllamaDown

OPTIONS = {"temperature": 0, "num_ctx": 8192}


def stream_chat(messages: list[dict], model: str = LLM_MODEL) -> Iterator[str]:
    # think=False: qwen3 otherwise spends seconds on hidden reasoning before the first answer token
    body = {"model": model, "messages": messages, "stream": True, "think": False, "options": OPTIONS}
    try:
        with httpx.stream("POST", f"{OLLAMA_URL}/api/chat", json=body, timeout=300) as r:
            r.raise_for_status()
            for line in r.iter_lines():
                if line:
                    msg = json.loads(line)
                    if msg.get("error"):
                        raise OllamaDown(msg["error"])
                    yield msg.get("message", {}).get("content", "")
    except httpx.HTTPError as e:
        raise OllamaDown(f"Ollama chat failed at {OLLAMA_URL} ({model}): {e}") from e


def chat(messages: list[dict], model: str = LLM_MODEL) -> str:
    return "".join(stream_chat(messages, model))


def chat_json(messages: list[dict], schema: dict, model: str) -> dict:
    """Non-streaming call constrained to a JSON schema (used by the eval question builder and judge)."""
    body = {"model": model, "messages": messages, "stream": False, "format": schema, "think": False}
    body["options"] = OPTIONS
    try:
        r = httpx.post(f"{OLLAMA_URL}/api/chat", json=body, timeout=600)
        r.raise_for_status()
    except httpx.HTTPError as e:
        raise OllamaDown(f"Ollama chat failed at {OLLAMA_URL} ({model}): {e}") from e
    return json.loads(r.json()["message"]["content"])
