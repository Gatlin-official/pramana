import io
from pathlib import Path

from pypdf import PdfReader

KINDS = {".md": "md", ".markdown": "md", ".txt": "txt", ".pdf": "pdf"}


def load(name: str, data: bytes) -> tuple[str, str, list[int] | None]:
    """Return (kind, text, page_starts). page_starts[i] = char offset where page i+1 begins (pdf only)."""
    kind = KINDS.get(Path(name).suffix.lower())
    if kind is None:
        raise ValueError(f"unsupported file type: {name}")
    if kind != "pdf":
        return kind, data.decode("utf-8", errors="replace").replace("\r\n", "\n"), None
    text, starts = "", []
    for page in PdfReader(io.BytesIO(data)).pages:
        starts.append(len(text))
        text += (page.extract_text() or "") + "\n\n"
    return kind, text, starts
