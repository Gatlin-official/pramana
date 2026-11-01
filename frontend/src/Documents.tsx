import { useEffect, useRef, useState } from 'react';
import { deleteDocument, listDocuments, uploadDocument, type DocSummary, type Id } from './api';

const ACCEPT = ['.pdf', '.md', '.markdown', '.txt'];
const MAX_BYTES = 20 * 1024 * 1024;

export default function Documents() {
  const [docs, setDocs] = useState<DocSummary[] | null>(null);
  const [loadError, setLoadError] = useState('');
  const [uploading, setUploading] = useState<string | null>(null);
  const [status, setStatus] = useState<{ ok: boolean; text: string } | null>(null);
  const [drag, setDrag] = useState(false);
  const [confirming, setConfirming] = useState<Id | null>(null);
  const [deleting, setDeleting] = useState<Id | null>(null);
  const input = useRef<HTMLInputElement>(null);

  const refresh = () =>
    listDocuments().then(
      (d) => {
        setDocs(d);
        setLoadError('');
      },
      (e) => setLoadError(e instanceof Error ? e.message : String(e)),
    );

  useEffect(() => {
    refresh();
  }, []);

  async function upload(files: FileList | null) {
    const file = files?.[0];
    if (!file || uploading) return;
    const ext = file.name.slice(file.name.lastIndexOf('.')).toLowerCase();
    if (!ACCEPT.includes(ext)) return setStatus({ ok: false, text: `${file.name} isn't a supported type. Use ${ACCEPT.join(', ')}.` });
    if (file.size > MAX_BYTES) return setStatus({ ok: false, text: `${file.name} is larger than 20 MB.` });
    setUploading(file.name);
    setStatus(null);
    try {
      const r = await uploadDocument(file);
      setStatus({ ok: true, text: `Added “${r.title || r.source}”. It's ready to cite.` });
      await refresh();
    } catch (e) {
      setStatus({ ok: false, text: `Couldn't add ${file.name}. ${e instanceof Error ? e.message : String(e)}` });
    } finally {
      setUploading(null);
      if (input.current) input.current.value = '';
    }
  }

  async function remove(d: DocSummary) {
    setDeleting(d.id);
    try {
      await deleteDocument(d.id);
      setStatus({ ok: true, text: `Deleted “${d.title || d.source}”.` });
      setConfirming(null);
      await refresh();
    } catch (e) {
      setStatus({ ok: false, text: `Couldn't delete “${d.title || d.source}”. ${e instanceof Error ? e.message : String(e)}` });
    } finally {
      setDeleting(null);
    }
  }

  return (
    <div className="page">
      <h1>Documents</h1>
      <p className="lede">The library Pramana cites from. Files are chunked and embedded locally when you add them.</p>

      <div
        className={`dropzone ${drag ? 'over' : ''} ${uploading ? 'busy' : ''}`}
        onDragOver={(e) => {
          e.preventDefault();
          setDrag(true);
        }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDrag(false);
          upload(e.dataTransfer.files);
        }}
      >
        {uploading ? (
          <p role="status">
            <span className="spinner" aria-hidden="true" />
            Indexing {uploading}. Large files can take a minute while passages are embedded.
          </p>
        ) : (
          <>
            <p>Drop a PDF, Markdown or text file here, up to 20 MB.</p>
            <button type="button" className="primary" onClick={() => input.current?.click()}>
              Choose file
            </button>
          </>
        )}
        <input
          ref={input}
          type="file"
          accept={ACCEPT.join(',')}
          className="visually-hidden"
          tabIndex={-1}
          aria-label="Choose a document to add"
          onChange={(e) => upload(e.target.files)}
        />
      </div>
      {status && (
        <p className={`notice ${status.ok ? 'ok' : 'error'}`} role={status.ok ? 'status' : 'alert'}>
          {status.text}
        </p>
      )}

      {loadError && <p className="notice error" role="alert">Couldn't load the library: {loadError}</p>}
      {docs && docs.length === 0 && <p className="empty">No documents yet. Add one above to start asking questions.</p>}
      {docs && docs.length > 0 && (
        <ul className="doc-list">
          {docs.map((d) => (
            <li key={String(d.id)}>
              <div className="doc-main">
                <h2>{d.title || d.source}</h2>
                <p className="path">{d.source}</p>
              </div>
              <p className="doc-meta">
                <span className="kind">{d.kind}</span>
                <span>{d.chunks} passages</span>
                <time dateTime={d.created_at}>{new Date(d.created_at).toLocaleDateString()}</time>
              </p>
              <div className="doc-actions">
                {confirming === d.id ? (
                  <>
                    <button type="button" className="danger" disabled={deleting === d.id} onClick={() => remove(d)}>
                      {deleting === d.id ? 'Deleting…' : 'Delete for good'}
                    </button>
                    <button type="button" className="ghost" onClick={() => setConfirming(null)}>
                      Keep
                    </button>
                  </>
                ) : (
                  <button type="button" className="ghost" onClick={() => setConfirming(d.id)} aria-label={`Delete ${d.title || d.source}`}>
                    Delete
                  </button>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
