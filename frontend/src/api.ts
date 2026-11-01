export type Mode = 'dense' | 'keyword' | 'hybrid';
export type Id = number | string;

export interface Hit {
  chunk_id: Id;
  score: number;
  doc_id: Id;
  source: string;
  text: string;
  char_start: number;
  char_end: number;
  page: number | null;
}

export interface Citation {
  n: number;
  chunk_id: Id;
  doc_id: Id;
  source: string;
  char_start: number;
  char_end: number;
  page: number | null;
}

export interface Latency {
  retrieve_ms: number;
  rerank_ms?: number;
  first_token_ms?: number;
  generate_ms?: number;
  total_ms: number;
}

export interface Done {
  answer: string;
  raw: string;
  abstained: boolean;
  citations: Citation[];
  invalid_citations: number[];
  mode: Mode;
  rerank: boolean;
  chunk_ids: Id[];
  latency_ms: Latency;
}

export interface DocSummary {
  id: Id;
  source: string;
  title: string;
  kind: string;
  created_at: string;
  chunks: number;
}

export interface DocFull {
  id: Id;
  source: string;
  title: string;
  kind: string;
  text: string;
  pages: number[] | null;
}

export interface EvalSummary {
  rows: Record<string, string>[];
  charts: string[];
  report: string | null;
}

async function detailOf(res: Response): Promise<string> {
  try {
    const body = await res.json();
    const d = body?.detail;
    if (typeof d === 'string') return d;
    if (Array.isArray(d)) return d.map((e) => e?.msg ?? String(e)).join('; ');
    return res.statusText || `HTTP ${res.status}`;
  } catch {
    return res.statusText || `HTTP ${res.status}`;
  }
}

async function json<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, init);
  if (!res.ok) throw new Error(await detailOf(res));
  return res.json() as Promise<T>;
}

export interface AskHandlers {
  retrieval: (hits: Hit[]) => void;
  token: (text: string) => void;
  done: (d: Done) => void;
  error: (detail: string) => void;
}

/** POST /ask and parse the SSE frames by hand (EventSource can't POST). */
export async function askStream(
  body: { question: string; mode: Mode; rerank: boolean; k?: number },
  on: AskHandlers,
  signal: AbortSignal,
): Promise<void> {
  const res = await fetch('/api/ask', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
    body: JSON.stringify(body),
    signal,
  });
  if (res.status === 429) throw new Error('Too many questions at once. Wait a few seconds and ask again.');
  if (res.status === 422) throw new Error(`The question was rejected: ${await detailOf(res)}`);
  if (!res.ok || !res.body) throw new Error(await detailOf(res));

  const reader = res.body.pipeThrough(new TextDecoderStream()).getReader();
  let buf = '';
  const handle = (frame: string) => {
    let event = '';
    const data: string[] = [];
    for (const line of frame.split('\n')) {
      if (line.startsWith('event:')) event = line.slice(6).trim();
      else if (line.startsWith('data:')) data.push(line.slice(5).replace(/^ /, ''));
    }
    if (!data.length) return;
    const msg = JSON.parse(data.join('\n'));
    switch (event || msg.type) {
      case 'retrieval': return on.retrieval(msg.hits ?? []);
      case 'token': return on.token(msg.text ?? '');
      case 'done': return on.done(msg as Done);
      case 'error': return on.error(msg.detail ?? 'The answer could not be generated.');
    }
  };
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buf = (buf + value).replace(/\r\n/g, '\n');
    let i: number;
    while ((i = buf.indexOf('\n\n')) >= 0) {
      handle(buf.slice(0, i));
      buf = buf.slice(i + 2);
    }
  }
  if (buf.trim()) handle(buf);
}

const docCache = new Map<string, Promise<DocFull>>();

export function getDocument(id: Id): Promise<DocFull> {
  const key = String(id);
  let p = docCache.get(key);
  if (!p) {
    p = json<DocFull>(`/documents/${encodeURIComponent(key)}`);
    p.catch(() => docCache.delete(key));
    docCache.set(key, p);
  }
  return p;
}

export const listDocuments = () => json<DocSummary[]>('/documents');

export async function uploadDocument(file: File): Promise<{ id: Id; source: string; title: string }> {
  const form = new FormData();
  form.append('file', file);
  const res = await fetch('/api/documents', { method: 'POST', body: form });
  if (res.ok) return res.json();
  const d = await detailOf(res);
  const prefix: Record<number, string> = {
    413: 'File is larger than 20 MB',
    415: 'Unsupported file type (use .pdf, .md, .markdown or .txt)',
    503: 'The indexing service is unavailable',
  };
  throw new Error(prefix[res.status] ? `${prefix[res.status]}: ${d}` : d);
}

export async function deleteDocument(id: Id): Promise<void> {
  const res = await fetch(`/api/documents/${encodeURIComponent(String(id))}`, { method: 'DELETE' });
  if (!res.ok) throw new Error(await detailOf(res));
  docCache.delete(String(id));
}

export const getEvalSummary = () => json<EvalSummary>('/eval/summary');
export const chartUrl = (name: string) => `/api/eval/charts/${encodeURIComponent(name)}`;
