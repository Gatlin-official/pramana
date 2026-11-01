import { useEffect, useState } from 'react';
import Ask from './Ask';
import Documents from './Documents';
import Eval from './Eval';

const PAGES = [
  { id: 'ask', label: 'Ask' },
  { id: 'documents', label: 'Documents' },
  { id: 'eval', label: 'Eval' },
] as const;
type Page = (typeof PAGES)[number]['id'];

const fromHash = (): Page => {
  const h = location.hash.replace(/^#\/?/, '');
  return PAGES.some((p) => p.id === h) ? (h as Page) : 'ask';
};

export default function App() {
  const [page, setPage] = useState<Page>(fromHash);
  useEffect(() => {
    const on = () => setPage(fromHash());
    addEventListener('hashchange', on);
    return () => removeEventListener('hashchange', on);
  }, []);

  return (
    <>
      <a className="skip" href="#main">Skip to content</a>
      <header className="masthead">
        <a className="wordmark" href="#/ask">
          Pramana<span className="wordmark-tag" aria-hidden="true">[1]</span>
        </a>
        <p className="tagline">Answers with receipts, from your own documents.</p>
        <nav aria-label="Main">
          {PAGES.map((p) => (
            <a key={p.id} href={`#/${p.id}`} aria-current={page === p.id ? 'page' : undefined}>
              {p.label}
            </a>
          ))}
        </nav>
      </header>
      <main id="main" tabIndex={-1}>
        {/* Ask stays mounted so answers survive a trip to Documents. */}
        <div hidden={page !== 'ask'}><Ask /></div>
        {page === 'documents' && <Documents />}
        {page === 'eval' && <Eval />}
      </main>
    </>
  );
}
