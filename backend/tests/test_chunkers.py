from app.ingest.chunkers import TOKEN, chunk, fixed, heading


def test_fixed_spans_cover_text_with_overlap():
    text = " ".join(f"w{i}" for i in range(100))
    spans = fixed(text, 30, 0.15)
    assert spans[0][0] == 0 and spans[-1][1] == len(text)
    assert all(n <= 30 for _, _, n in spans)
    # step is 30 - 4 = 26 tokens, so consecutive chunks share 4 words
    assert text[spans[1][0] : spans[1][0] + 3] == "w26"


def test_fixed_no_overlap_partitions():
    text = " ".join(f"w{i}" for i in range(90))
    spans = fixed(text, 30)
    assert [n for *_, n in spans] == [30, 30, 30]


def test_heading_respects_code_fences_and_merges_small():
    text = "# A\nintro\n```\n# not a heading\n```\n## B\nshort\n## C\n" + "x " * 50
    spans = heading(text, 20)
    first = text[spans[0][0] : spans[0][1]]
    assert "# not a heading" in first and "## B" in first  # fence kept, B merged into A
    assert all(n <= 20 for *_, n in spans)


def test_chunk_dispatch_and_offsets_exact():
    text = "hello world. " * 40
    for cfg in ("fixed-16-0", "fixed-16-15", "heading-16"):
        for s, e, n in chunk(text, cfg):
            assert len(TOKEN.findall(text[s:e])) == n
