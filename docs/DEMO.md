# 90-second demo script

Setup before recording: `docker compose up -d`, `make dev`, browser at http://localhost:5173, window ~1280x800,
one question already asked once so the reranker and LLM are warm.

| Time | Screen | Say |
|------|--------|-----|
| 0:00–0:10 | Ask page, empty | "This is Pramana, a fully local RAG assistant. Everything runs on my laptop: Postgres with pgvector, Ollama, a 3B model. Every answer has to cite the exact passage." |
| 0:10–0:30 | Type *"How do I declare an optional query parameter?"*, mode **hybrid**, rerank **on**, Ask | "Answers stream in with inline citations. Below are the retrieved chunks and the latency breakdown: retrieval, rerank, first token." |
| 0:30–0:42 | Click citation chip `[1]` | "Clicking a citation opens the source document with the exact cited span highlighted, using the character offsets stored at ingestion." |
| 0:42–0:57 | Switch mode to **keyword**, then **dense**, re-ask; open **Compare modes** | "I can rerun the same question in each retrieval mode and compare the answers side by side." |
| 0:57–1:07 | Ask *"How do I deploy FastAPI to AWS Lambda with Mangum?"* | "If the docs don't cover it, it says so instead of making something up." |
| 1:07–1:22 | Eval page: table, sort by recall@5, scroll charts | "None of the design choices are guesses. A 120-question eval set, 42 retrieval configs: chunk size, overlap, mode, rerank. This table is where the hybrid + rerank choice comes from." |
| 1:22–1:30 | Documents page, drag in a PDF | "I can also upload my own PDFs, Markdown or text, and ask questions about them the same way." |

Tips: hide the bookmarks bar, zoom the browser to 110%, record at 30 fps, and trim dead air while the LLM loads.
