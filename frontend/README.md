# Pramana frontend
React 18 + TypeScript + Vite UI for the local cited-RAG backend.
`npm install` then `npm run dev` → http://localhost:5173 (proxies `/api/*` to `http://127.0.0.1:8000`).
`npm run build` type-checks and builds to `dist/`; `npm run preview` serves it.
Pages: Ask (streamed cited answers + compare modes), Documents (upload/delete), Eval (metrics, charts, report).
