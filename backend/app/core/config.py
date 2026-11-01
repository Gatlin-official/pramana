import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def _env_file() -> dict[str, str]:
    f = ROOT / ".env"
    if not f.exists():
        return {}
    pairs = (ln.split("=", 1) for ln in f.read_text().splitlines() if "=" in ln and not ln.startswith("#"))
    return {k.strip(): v.strip() for k, v in pairs}


_file = _env_file()


def env(key: str, default: str) -> str:
    return os.environ.get(key) or _file.get(key) or default


DATABASE_URL = env("DATABASE_URL", "postgresql+psycopg://pramana:pramana@127.0.0.1:5433/pramana")
OLLAMA_URL = env("OLLAMA_URL", "http://127.0.0.1:11434")
EMBED_MODEL = env("EMBED_MODEL", "nomic-embed-text")
LLM_MODEL = env("LLM_MODEL", "qwen3:8b")
RERANK_MODEL = env("RERANK_MODEL", "BAAI/bge-reranker-base")
CHUNK_CONFIG = env("CHUNK_CONFIG", "fixed-512-0")
RATE_LIMIT_PER_MIN = int(env("RATE_LIMIT_PER_MIN", "30"))
EMBED_DIM = 768
JUDGE_MODEL = env("JUDGE_MODEL", "qwen3:8b")  # drafts eval questions + judges faithfulness (same model as LLM)
