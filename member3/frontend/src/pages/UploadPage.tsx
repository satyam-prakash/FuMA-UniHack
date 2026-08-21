/**
 * Ingest screen. States: empty | selected | validating | invalid | ready.
 *
 * Header validation runs client-side before upload so a missing column is named
 * immediately instead of after a round trip; the server re-checks regardless.
 */

import { useRef, useState } from 'react';
import { AlertTriangle, Check, FileSpreadsheet, UploadCloud } from '../components/icons';
import { ApiError, loadSample, startEnrichment, uploadFile } from '../api/client';
import Plate from '../components/Plate';
import Button from '../components/Button';
import StatChip from '../components/StatChip';
import { PageHeader } from '../components/AppShell';
import { REQUIRED_INPUT_COLUMNS } from '../types';

type State = 'empty' | 'selected' | 'validating' | 'invalid' | 'ready';

interface Preview {
  file: File;
  rows: number;
  header: string[];
  missing: string[];
}

/** Splits one CSV line honouring double-quoted fields. */
function splitCsvLine(line: string): string[] {
  const cells: string[] = [];
  let cell = '';
  let quoted = false;
  for (let i = 0; i < line.length; i += 1) {
    const char = line[i];
    if (char === '"') {
      if (quoted && line[i + 1] === '"') {
        cell += '"';
        i += 1;
      } else {
        quoted = !quoted;
      }
    } else if (char === ',' && !quoted) {
      cells.push(cell);
      cell = '';
    } else {
      cell += char;
    }
  }
  cells.push(cell);
  return cells.map((value) => value.trim().replace(/^"|"$/g, ''));
}

export default function UploadPage({
  onStart,
}: {
  onStart: (jobId: string, filename: string) => void;
}) {
  const [state, setState] = useState<State>('empty');
  const [preview, setPreview] = useState<Preview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const [busy, setBusy] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  async function inspect(file: File) {
    setError(null);
    setPreview(null);
    setState('validating');

    if (!file.name.toLowerCase().endsWith('.csv')) {
      setError(`Unsupported file type "${file.name}". Ingest expects a .csv export.`);
      setState('invalid');
      return;
    }

    const text = await file.text();
    const lines = text.split(/\r?\n/).filter((line) => line.trim().length > 0);
    if (lines.length < 2) {
      setError('File carries a header but no data rows.');
      setState('invalid');
      return;
    }

    const header = splitCsvLine(lines[0]);
    const present = new Set(header.map((name) => name.toLowerCase()));
    const missing = REQUIRED_INPUT_COLUMNS.filter((column) => !present.has(column.toLowerCase()));

    setPreview({ file, rows: lines.length - 1, header, missing });
    if (missing.length > 0) {
      setError(`Missing required column${missing.length > 1 ? 's' : ''}: ${missing.join(', ')}`);
      setState('invalid');
      return;
    }
    setState('ready');
  }

  async function begin(load: () => Promise<{ job_id: string; filename: string }>) {
    setBusy(true);
    setError(null);
    try {
      const job = await load();
      await startEnrichment(job.job_id);
      onStart(job.job_id, job.filename);
    } catch (cause) {
      const detail =
        cause instanceof ApiError
          ? [cause.message, ...cause.details].join(' \u00b7 ')
          : String(cause);
      setError(detail);
      setState('invalid');
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <PageHeader
        title="Supplier Ingest"
        meta={[
          { label: 'pipeline', value: 'M1 \u2192 M2 \u2192 DELIVERY' },
          { label: 'delivery schema', value: '252 COLUMNS' },
          { label: 'state', value: state.toUpperCase() },
        ]}
      />

      <div className="grid grid-cols-12 gap-gutter">
        {/* Drop zone */}
        <div className="col-span-12 lg:col-span-7">
          <div
            onDragOver={(event) => {
              event.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={(event) => {
              event.preventDefault();
              setDragging(false);
              const file = event.dataTransfer.files?.[0];
              if (file) void inspect(file);
            }}
            className={[
              'border border-dashed p-12 flex flex-col items-center text-center transition-colors',
              dragging
                ? 'border-primary bg-primary-fixed/40'
                : 'border-ink-graphite bg-surface-bright',
            ].join(' ')}
          >
            <UploadCloud size={40} strokeWidth={1.5} className="text-ink-graphite mb-4" />
            <div className="font-headline-md text-headline-md text-ink-graphite leading-none mb-2">
              Drop supplier CSV
            </div>
            <p className="font-body-md text-body-md text-secondary max-w-md mb-6">
              Raw manufacturer rows enter here. Every row is normalized, enriched, validated and
              mapped to the fixed 252-column delivery format.
            </p>

            <input
              ref={inputRef}
              type="file"
              accept=".csv"
              className="hidden"
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) void inspect(file);
                event.target.value = '';
              }}
            />

            <div className="flex flex-wrap items-center justify-center gap-4">
              <Button variant="secondary" onClick={() => inputRef.current?.click()} disabled={busy}>
                Browse files
              </Button>
              <Button
                variant="ghost"
                disabled={busy}
                onClick={() => void begin(() => loadSample())}
              >
                Use bundled 1,000-row sample
              </Button>
            </div>
          </div>

          {error && (
            <div className="mt-4 border border-error bg-error-container px-4 py-3 flex items-start gap-2">
              <AlertTriangle size={16} strokeWidth={1.75} className="text-on-error-container mt-[2px] shrink-0" />
              <span className="font-data-mono text-data-mono text-on-error-container">{error}</span>
            </div>
          )}

          {state === 'ready' && preview && (
            <div className="mt-6 flex flex-wrap items-center gap-4">
              <Button
                variant="primary"
                disabled={busy}
                onClick={() => void begin(() => uploadFile(preview.file))}
              >
                {busy ? 'Dispatching\u2026' : 'Start Enrichment'}
              </Button>
              <span className="font-data-mono text-data-mono text-secondary uppercase">
                {preview.rows.toLocaleString()} rows queued
              </span>
            </div>
          )}
        </div>

        {/* Manifest */}
        <div className="col-span-12 lg:col-span-5">
          <Plate idx={1} label="Input manifest" title="Required columns" emphasis>
            {state === 'empty' && (
              <p className="font-body-md text-body-md text-secondary mb-6">
                Awaiting a file. The six columns below must be present.
              </p>
            )}

            {preview && (
              <div className="flex flex-wrap items-center gap-3 mb-6 pb-6 border-b border-border-subtle">
                <FileSpreadsheet size={16} strokeWidth={1.75} className="text-ink-graphite" />
                <span className="font-data-mono text-data-mono text-ink-graphite truncate max-w-[16rem]">
                  {preview.file.name}
                </span>
                <StatChip tone="neutral">{preview.rows.toLocaleString()} ROWS</StatChip>
                <StatChip tone="neutral">{preview.header.length} COLUMNS</StatChip>
              </div>
            )}

            <ul className="flex flex-col">
              {REQUIRED_INPUT_COLUMNS.map((column) => {
                const missing = preview?.missing.includes(column) ?? false;
                const checked = preview !== null && !missing;
                return (
                  <li
                    key={column}
                    className="flex items-center justify-between py-2 border-b border-border-subtle last:border-b-0"
                  >
                    <span className="font-data-mono text-data-mono text-ink-graphite">{column}</span>
                    {preview === null ? (
                      <span className="w-4 h-4 border border-secondary shrink-0" />
                    ) : checked ? (
                      <span className="w-4 h-4 bg-primary text-on-primary flex items-center justify-center shrink-0">
                        <Check size={12} strokeWidth={3} />
                      </span>
                    ) : (
                      <span className="w-4 h-4 border border-error bg-error-container shrink-0" />
                    )}
                  </li>
                );
              })}
            </ul>

            {state === 'validating' && (
              <div className="mt-6 font-data-mono text-data-mono text-secondary uppercase">
                Validating header&hellip;
              </div>
            )}
          </Plate>
        </div>
      </div>
    </>
  );
}
