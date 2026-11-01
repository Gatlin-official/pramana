import { Fragment, useCallback, useEffect, useRef, useState, type ReactNode } from 'react';
import { askStream, getDocument, type Citation, type DocFull, type Done, type Hit, type Id, type Mode } from './api';

const MODES: Mode[] = ['dense', 'keyword', 'hybrid'];
const COMBOS = MODES.flatMap((m) => [false, true].map((r) => ({ mode: m, rerank: r })));
const keyOf = (mode: Mode, rerank: boolean) => `${mode}|${rerank}`;
const label = (mode: Mode, rerank: boolean) => `${mode}${rerank ? ' + rerank' : ''}`;

interface Run {
  mode: Mode;
  rerank: boolean;
  status: 'streaming' | 'done' | 'error';
  hits: Hit[];
  text: string;
  done?: Done;
  error?: string;
}

/** The span a citation chip or source card points at. */
export interface Span {
  doc_id: Id;
  source: string;
  char_start: number;
  char_end: number;
  page: number | null;
  tag: string;
}

export default function Ask() {
  const [question, setQuestion] = useState('');
  const [mode, setMode] = useState<Mode>('hybrid');
  const [rerank, setRerank] = useState(false);
  const [asked, setAsked] = useState('');
  const [runs, setRuns] = useState<Record<string, Run>>({});
  const [current, setCurrent] = useState<string | null>(null);
  const [compare, setCompare] = useState(false);
  const [span, setSpan] = useState<Span | null>(null);
  const abort = useRef<AbortController | null>(null);
  const closeSpan = useCallback(() => setSpan(null), []);

  useEffect(() => () => abort.current?.abort(), []);

  const busy = Object.values(runs).some((r) => r.status === 'streaming');
  const run = current ? runs[current] : undefined;

  async function start(q: string, m: Mode, r: boolean) {
    q = q.trim();
    if (!q || busy) return;
    const key = keyOf(m, r);
    const fresh: Run = { mode: m, rerank: r, status: 'streaming', hits: [], text: '' };
    if (q !== asked) {
      setAsked(q);
      setRuns({ [key]: fresh });
    } else {
      setRuns((rs) => ({ ...rs, [key]: fresh }));
    }
    setCurrent(key);
    const patch = (f: (r: Run) => Partial<Run>) =>
      setRuns((rs) => (rs[key] ? { ...rs, [key]: { ...rs[key], ...f(rs[key]) } } : rs));

    const ac = new AbortController();
    abort.current = ac;
    try {
      await askStream(
        { question: q, mode: m, rerank: r },
        {
          retrieval: (hits) => patch(() => ({ hits })),
          token: (t) => patch((x) => ({ text: x.text + t })),
          done: (d) => patch(() => ({ status: 'done', done: d, text: d.answer })),
          error: (detail) => patch(() => ({ status: 'error', error: friendly(detail) })),
        },
        ac.signal,
      );
      patch((x) => (x.status === 'streaming' ? { status: 'error', error: 'The answer stream ended before it finished. Try asking again.' } : {}));
    } catch (e) {
      if (ac.signal.aborted) return;
      patch(() => ({ status: 'error', error: friendly(e instanceof Error ? e.message : String(e)) }));
    }
  }

  const compared = COMBOS.filter((c) => runs[keyOf(c.mode, c.rerank)]);

  return (
    <div className={`ask ${span ? 'has-panel' : ''}`}>
      <form
        className="query"
        onSubmit={(e) => {
          e.preventDefault();
          start(question, mode, rerank);
        }}
      >
        <label htmlFor="q" className="query-label">Ask a question about your documents</label>
        <textarea
          id="q"
          rows={3}
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              start(question, mode, rerank);
            }
          }}
          placeholder="What does the warranty cover after the first year?"
        />
        <div className="controls">
          <fieldset className="segmented">
            <legend>Retrieval</legend>
            {MODES.map((m) => (
              <label key={m}>
                <input type="radio" name="mode" value={m} checked={mode === m} onChange={() => setMode(m)} />
                <span>{m}</span>
              </label>
            ))}
          </fieldset>
          <button type="button" role="switch" aria-checked={rerank} className="switch" onClick={() => setRerank(!rerank)}>
            <span className="switch-track" aria-hidden="true" />
            Rerank
          </button>
          <button className="primary" type="submit" disabled={busy || !question.trim()}>
            {busy ? 'Answering…' : 'Ask'}
          </button>
        </div>
        <p className="hint">Enter to ask, Shift+Enter for a new line.</p>
      </form>

      {asked && (
        <div className="result-bar">
          <p className="asked">“{asked}”</p>
          <button
            type="button"
            className="ghost"
            aria-pressed={compare}
            onClick={() => setCompare(!compare)}
          >
            {compare ? 'Show single answer' : `Compare modes (${compared.length}/6)`}
          </button>
        </div>
      )}

      {compare && asked ? (
        <section className="compare" aria-label="Answers by retrieval mode">
          {COMBOS.map((c) => {
            const r = runs[keyOf(c.mode, c.rerank)];
            return (
              <article key={keyOf(c.mode, c.rerank)} className="compare-cell">
                <h3>{label(c.mode, c.rerank)}</h3>
                {r ? (
                  <>
                    <Answer run={r} onCite={setSpan} />
                    {r.done && <p className="meta">{Math.round(r.done.latency_ms.total_ms)} ms total · {r.hits.length} sources</p>}
                  </>
                ) : (
                  <button type="button" className="ghost" disabled={busy} onClick={() => start(asked, c.mode, c.rerank)}>
                    Run in {label(c.mode, c.rerank)}
                  </button>
                )}
              </article>
            );
          })}
        </section>
      ) : (
        run && (
          <section className="answer-block" aria-live="polite" aria-busy={run.status === 'streaming'}>
            <h2 className="answer-heading">Answer <span className="meta">{label(run.mode, run.rerank)}</span></h2>
            <Answer run={run} onCite={setSpan} />
            {run.done && <LatencyTable l={run.done.latency_ms} />}
            {run.hits.length > 0 && <Sources run={run} onOpen={setSpan} />}
          </section>
        )
      )}

      {!asked && (
        <p className="empty">
          Every claim in an answer links to the passage it came from. Upload files under Documents, then ask here.
        </p>
      )}

      {span && <Evidence span={span} onClose={closeSpan} />}
    </div>
  );
}

function friendly(detail: string): string {
  if (/ollama|connect|refused|unreachable/i.test(detail))
    return `The local language model isn't reachable. Check that Ollama is running, then ask again. (${detail})`;
  return detail;
}

function Answer({ run, onCite }: { run: Run; onCite: (s: Span) => void }) {
  if (run.status === 'error') return <p className="notice error" role="alert">{run.error}</p>;
  if (run.done?.abstained)
    return (
      <div className="notice abstain">
        <strong>Not found in the documents.</strong>
        <p>None of the retrieved passages support an answer. Try rephrasing, another retrieval mode, or uploading the source.</p>
      </div>
    );
  if (run.status === 'streaming' && !run.text)
    return <p className="pending">{run.hits.length ? `Read ${run.hits.length} passages, writing…` : 'Searching documents…'}</p>;

  const cites = new Map<number, Citation | Hit>();
  if (run.done) run.done.citations.forEach((c) => cites.set(c.n, c));
  else run.hits.forEach((h, i) => cites.set(i + 1, h));

  const parts = run.text.split(/(\[\d+\])/g);
  return (
    <div className={`answer ${run.status === 'streaming' ? 'streaming' : ''}`}>
      {parts.map((p, i) => {
        const m = /^\[(\d+)\]$/.exec(p);
        const c = m ? cites.get(Number(m[1])) : undefined;
        if (!m || !c) return <Fragment key={i}>{p}</Fragment>;
        return (
          <button
            key={i}
            type="button"
            className="cite"
            aria-label={`Citation ${m[1]}: ${c.source}${c.page != null ? `, page ${c.page}` : ''}`}
            onClick={() => onCite({ doc_id: c.doc_id, source: c.source, char_start: c.char_start, char_end: c.char_end, page: c.page, tag: m[1] })}
          >
            {m[1]}
          </button>
        );
      })}
    </div>
  );
}

function LatencyTable({ l }: { l: Done['latency_ms'] }) {
  const items: [string, number | undefined][] = [
    ['retrieve', l.retrieve_ms],
    ['rerank', l.rerank_ms],
    ['first token', l.first_token_ms],
    ['total', l.total_ms],
  ];
  return (
    <dl className="latency" aria-label="Latency">
      {items
        .filter(([, v]) => v != null)
        .map(([k, v]) => (
          <div key={k}>
            <dt>{k}</dt>
            <dd>{Math.round(v!)} ms</dd>
          </div>
        ))}
    </dl>
  );
}

function Sources({ run, onOpen }: { run: Run; onOpen: (s: Span) => void }) {
  const cited = new Set(run.done?.citations.map((c) => String(c.chunk_id)));
  return (
    <section className="sources">
      <h2>Retrieved passages</h2>
      <ol>
        {run.hits.map((h, i) => (
          <li key={String(h.chunk_id)}>
            <button
              type="button"
              className="source-card"
              onClick={() => onOpen({ doc_id: h.doc_id, source: h.source, char_start: h.char_start, char_end: h.char_end, page: h.page, tag: String(i + 1) })}
            >
              <span className="rank">{i + 1}</span>
              <span className="source-head">
                <span className="path">{h.source}{h.page != null && ` · p. ${h.page}`}</span>
                <span className="score">{h.score.toFixed(3)}{cited.has(String(h.chunk_id)) && <em className="cited">cited</em>}</span>
              </span>
              <span className="snippet">{h.text.length > 240 ? `${h.text.slice(0, 240).trimEnd()}…` : h.text}</span>
            </button>
          </li>
        ))}
      </ol>
    </section>
  );
}

function Evidence({ span, onClose }: { span: Span; onClose: () => void }) {
  const [doc, setDoc] = useState<DocFull | null>(null);
  const [error, setError] = useState('');
  const mark = useRef<HTMLElement>(null);
  const close = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    let live = true;
    setDoc(null);
    setError('');
    getDocument(span.doc_id).then(
      (d) => live && setDoc(d),
      (e) => live && setError(e instanceof Error ? e.message : String(e)),
    );
    return () => {
      live = false;
    };
  }, [span.doc_id]);

  useEffect(() => {
    mark.current?.scrollIntoView({ block: 'center', behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
  }, [doc, span]);

  useEffect(() => {
    const prev = document.activeElement as HTMLElement | null;
    close.current?.focus();
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    addEventListener('keydown', onKey);
    return () => {
      removeEventListener('keydown', onKey);
      prev?.focus();
    };
  }, [onClose]);

  let body: ReactNode = <p className="pending">Opening document…</p>;
  if (error) body = <p className="notice error" role="alert">Couldn't open this document: {error}</p>;
  else if (doc)
    body = (
      <pre className="doc-text">
        {doc.text.slice(0, span.char_start)}
        <mark ref={mark}>{doc.text.slice(span.char_start, span.char_end)}</mark>
        {doc.text.slice(span.char_end)}
      </pre>
    );

  return (
    <aside className="evidence" role="dialog" aria-label={`Source for citation ${span.tag}`}>
      <header>
        <span className="cite static" aria-hidden="true">{span.tag}</span>
        <div>
          <h2>{doc?.title || span.source}</h2>
          <p className="path">
            {span.source}
            {span.page != null && ` · page ${span.page}`} · chars {span.char_start}–{span.char_end}
          </p>
        </div>
        <button ref={close} type="button" className="icon" aria-label="Close source panel" onClick={onClose}>
          ×
        </button>
      </header>
      {body}
    </aside>
  );
}
