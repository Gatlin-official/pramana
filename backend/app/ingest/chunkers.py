"""Chunkers return (char_start, char_end, token_count) spans into the source text.

Tokens are approximated with a regex (words and punctuation separately), which tracks
BPE counts closely enough for sizing without pulling in a tokenizer dependency.
"""

import re

TOKEN = re.compile(r"\w+|[^\w\s]")
HEADING = re.compile(r"^#{1,6} ", re.M)
FENCE = re.compile(r"^(```|~~~)", re.M)

Span = tuple[int, int, int]


def fixed(text: str, size: int, overlap: float = 0.0, offset: int = 0) -> list[Span]:
    toks = [m.span() for m in TOKEN.finditer(text)]
    step = max(1, size - int(size * overlap))
    out = []
    for i in range(0, len(toks), step):
        win = toks[i : i + size]
        out.append((offset + win[0][0], offset + win[-1][1], len(win)))
        if i + size >= len(toks):
            break
    return out


def _sections(text: str) -> list[tuple[int, int]]:
    """Split at markdown headings that are not inside code fences."""
    fences = [m.start() for m in FENCE.finditer(text)]

    def in_code(pos: int) -> bool:
        return sum(f < pos for f in fences) % 2 == 1

    cuts = [0] + [m.start() for m in HEADING.finditer(text) if m.start() and not in_code(m.start())]
    return list(zip(cuts, cuts[1:] + [len(text)], strict=True))


def heading(text: str, size: int) -> list[Span]:
    """One chunk per heading section; small neighbours are merged, big ones split with `fixed`."""
    out: list[Span] = []
    cur: Span | None = None
    for s, e in _sections(text):
        n = len(TOKEN.findall(text[s:e]))
        if n == 0:
            continue
        if n > size:
            if cur:
                out.append(cur)
                cur = None
            out += fixed(text[s:e], size, 0.15, offset=s)
        elif cur and cur[2] + n <= size:
            cur = (cur[0], e, cur[2] + n)
        else:
            if cur:
                out.append(cur)
            cur = (s, e, n)
    if cur:
        out.append(cur)
    return out


def chunk(text: str, config: str) -> list[Span]:
    """config: 'fixed-<size>-<overlap%>' or 'heading-<size>'."""
    kind, size, *rest = config.split("-")
    if kind == "fixed":
        return fixed(text, int(size), int(rest[0]) / 100 if rest else 0.0)
    if kind == "heading":
        return heading(text, int(size))
    raise ValueError(f"unknown chunk config {config}")
