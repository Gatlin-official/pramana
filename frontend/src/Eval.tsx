import { useEffect, useMemo, useState, type ReactNode } from 'react';
import { chartUrl, getEvalSummary, type EvalSummary } from './api';

const COLUMNS = [
  'run', 'config', 'mode', 'rerank', 'n_questions',
  'recall@5', 'recall@10', 'mrr', 'ndcg@10',
  'recall@5_single', 'recall@5_multi', 'recall@5_paraphrase',
  'retrieval_p50_ms', 'retrieval_p95_ms',
  'citation_precision', 'faithfulness', 'abstention_accuracy', 'false_abstention_rate',
  'e2e_p50_ms', 'e2e_p95_ms', 'first_token_p50_ms', 'invalid_citation_markers',
];
const TEXT_COLS = new Set(['run', 'config', 'mode', 'rerank']);
const RATE_COLS = new Set([
  'recall@5', 'recall@10', 'mrr', 'ndcg@10', 'recall@5_single', 'recall@5_multi', 'recall@5_paraphrase',
  'citation_precision', 'faithfulness', 'abstention_accuracy', 'false_abstention_rate',
]);

function fmt(col: string, v: string | undefined): string {
  if (v == null || v === '') return '—';
  const n = Number(v);
  if (TEXT_COLS.has(col) || Number.isNaN(n)) return v;
  if (RATE_COLS.has(col)) return `${(n * 100).toFixed(1)}%`;
  if (col.endsWith('_ms')) return String(Math.round(n));
  return String(n);
}

export default function Eval() {
  const [data, setData] = useState<EvalSummary | null>(null);
  const [error, setError] = useState('');
  const [sort, setSort] = useState<{ col: string; desc: boolean }>({ col: 'recall@5', desc: true });
  const [mode, setMode] = useState('all');
  const [rerank, setRerank] = useState('all');

  useEffect(() => {
    getEvalSummary().then(setData, (e) => setError(e instanceof Error ? e.message : String(e)));
  }, []);

  const rows = data?.rows ?? [];
  const modes = useMemo(() => [...new Set(rows.map((r) => r.mode).filter(Boolean))], [rows]);
  const reranks = useMemo(() => [...new Set(rows.map((r) => r.rerank).filter(Boolean))], [rows]);
  const best = useMemo(() => {
    let b: Record<string, string> | null = null;
    for (const r of rows) if (r['recall@5'] !== '' && (!b || Number(r['recall@5']) > Number(b['recall@5']))) b = r;
    return b;
  }, [rows]);

  const shown = useMemo(() => {
    const f = rows.filter((r) => (mode === 'all' || r.mode === mode) && (rerank === 'all' || r.rerank === rerank));
    const { col, desc } = sort;
    return [...f].sort((a, b) => {
      const x = a[col] ?? '', y = b[col] ?? '';
      if (x === '' || y === '') return x === y ? 0 : x === '' ? 1 : -1; // blanks last
      const nx = Number(x), ny = Number(y);
      const c = Number.isNaN(nx) || Number.isNaN(ny) ? x.localeCompare(y) : nx - ny;
      return desc ? -c : c;
    });
  }, [rows, mode, rerank, sort]);

  if (error) return <div className="page"><h1>Eval</h1><p className="notice error" role="alert">Couldn't load evaluation results: {error}</p></div>;
  if (!data) return <div className="page"><h1>Eval</h1><p className="pending">Loading results…</p></div>;

  const cols = COLUMNS.filter((c) => rows.some((r) => c in r));

  return (
    <div className="page wide">
      <h1>Eval</h1>
      {rows.length === 0 ? (
        <p className="empty">
          No evaluation results yet. Run <code>make eval</code> in the project root, then reload this page.
        </p>
      ) : (
        <>
          <p className="lede">
            Retrieval and answer quality per configuration. The highlighted row has the best recall@5. Select a column header to sort.
          </p>
          <div className="filters">
            <Select label="Mode" value={mode} onChange={setMode} options={modes} />
            <Select label="Rerank" value={rerank} onChange={setRerank} options={reranks} />
            <span className="meta">{shown.length} of {rows.length} runs</span>
          </div>
          <div className="table-wrap" tabIndex={0} role="region" aria-label="Evaluation results">
            <table className="results">
              <thead>
                <tr>
                  {cols.map((c) => (
                    <th key={c} scope="col" aria-sort={sort.col === c ? (sort.desc ? 'descending' : 'ascending') : 'none'} className={TEXT_COLS.has(c) ? '' : 'num'}>
                      <button type="button" onClick={() => setSort({ col: c, desc: sort.col === c ? !sort.desc : !TEXT_COLS.has(c) })}>
                        {c.replace(/_/g, ' ')}
                        <span className="sort-ind" aria-hidden="true">{sort.col === c ? (sort.desc ? '↓' : '↑') : ''}</span>
                      </button>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {shown.map((r, i) => (
                  <tr key={i} className={r === best ? 'best' : ''}>
                    {cols.map((c) => (
                      <td key={c} className={TEXT_COLS.has(c) ? '' : 'num'}>
                        {fmt(c, r[c])}
                        {r === best && c === 'recall@5' && <span className="visually-hidden"> (best)</span>}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {data.charts.length > 0 && (
        <section>
          <h2>Charts</h2>
          <div className="charts">
            {data.charts.map((c) => (
              <figure key={c}>
                <a href={chartUrl(c)} target="_blank" rel="noreferrer">
                  <img src={chartUrl(c)} alt={`Chart: ${c.replace(/\.png$/i, '').replace(/[_-]/g, ' ')}`} loading="lazy" />
                </a>
                <figcaption>{c}</figcaption>
              </figure>
            ))}
          </div>
        </section>
      )}

      {data.report && (
        <section className="report">
          <h2>Report</h2>
          <Markdown src={data.report} />
        </section>
      )}
    </div>
  );
}

function Select({ label, value, onChange, options }: { label: string; value: string; onChange: (v: string) => void; options: string[] }) {
  return (
    <label className="select">
      {label}
      <select value={value} onChange={(e) => onChange(e.target.value)}>
        <option value="all">All</option>
        {options.map((o) => <option key={o} value={o}>{o}</option>)}
      </select>
    </label>
  );
}

/** Tiny markdown: headings, paragraphs, lists, fenced code, tables, **bold**, `code`. */
function inline(s: string): ReactNode[] {
  return s.split(/(`[^`]+`|\*\*[^*]+\*\*)/g).map((p, i) =>
    p.length > 2 && p.startsWith('`') && p.endsWith('`') ? <code key={i}>{p.slice(1, -1)}</code>
    : p.length > 4 && p.startsWith('**') && p.endsWith('**') ? <strong key={i}>{p.slice(2, -2)}</strong>
    : p,
  );
}

const LIST = /^\s*([-*+]|\d+[.)])\s+/;
const cellsOf = (l: string) => l.trim().replace(/^\|/, '').replace(/\|$/, '').split('|').map((c) => c.trim());

export function Markdown({ src }: { src: string }) {
  const lines = src.replace(/\r\n/g, '\n').split('\n');
  const out: ReactNode[] = [];
  let i = 0;
  while (i < lines.length) {
    const l = lines[i];
    const k = out.length;
    if (!l.trim()) { i++; continue; }
    if (l.startsWith('```')) {
      const buf: string[] = [];
      for (i++; i < lines.length && !lines[i].startsWith('```'); i++) buf.push(lines[i]);
      i++;
      out.push(<pre key={k}>{buf.join('\n')}</pre>);
      continue;
    }
    const h = /^(#{1,6})\s+(.*)$/.exec(l);
    if (h) {
      const Tag = `h${Math.min(h[1].length + 2, 6)}` as 'h3';
      out.push(<Tag key={k}>{inline(h[2])}</Tag>);
      i++;
      continue;
    }
    if (l.trim().startsWith('|')) {
      const rows: string[][] = [];
      for (; i < lines.length && lines[i].trim().startsWith('|'); i++) rows.push(cellsOf(lines[i]));
      const [head, ...rest] = rows;
      const body = rest.filter((r) => !r.every((c) => /^:?-+:?$/.test(c)));
      out.push(
        <div className="table-wrap" key={k} tabIndex={0} role="region" aria-label="Report table">
          <table>
            <thead><tr>{head.map((c, j) => <th key={j}>{inline(c)}</th>)}</tr></thead>
            <tbody>{body.map((r, j) => <tr key={j}>{r.map((c, n) => <td key={n}>{inline(c)}</td>)}</tr>)}</tbody>
          </table>
        </div>,
      );
      continue;
    }
    if (LIST.test(l)) {
      const ordered = /^\s*\d/.test(l);
      const items: string[] = [];
      for (; i < lines.length && LIST.test(lines[i]); i++) items.push(lines[i].replace(LIST, ''));
      const List = ordered ? 'ol' : 'ul';
      out.push(<List key={k}>{items.map((t, j) => <li key={j}>{inline(t)}</li>)}</List>);
      continue;
    }
    const para = [l.trim()]; // always consume the current line so the loop advances
    for (i++; i < lines.length && lines[i].trim() && !/^(#{1,6}\s|```|\|)/.test(lines[i].trim()) && !LIST.test(lines[i]); i++) para.push(lines[i].trim());
    out.push(<p key={k}>{inline(para.join(' '))}</p>);
  }
  return <div className="md">{out}</div>;
}
