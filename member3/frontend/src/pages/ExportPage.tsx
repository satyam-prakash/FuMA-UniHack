/**
 * Delivery export center. The 252-column validation result gates both download
 * buttons: a FAIL means the mapper produced a row that is not exactly the
 * delivery schema, and shipping that file would be worse than shipping nothing.
 */

import { useEffect, useState } from 'react';
import { AlertTriangle, Check, FileSpreadsheet, FileText } from '../components/icons';
import { ApiError, downloadExport, getExportStatus } from '../api/client';
import { PageHeader } from '../components/AppShell';
import Button from '../components/Button';
import Plate from '../components/Plate';
import type { ExportStatus } from '../types';

export default function ExportPage({ jobId }: { jobId: string }) {
  const [status, setStatus] = useState<ExportStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<'csv' | 'xlsx' | null>(null);

  useEffect(() => {
    let live = true;
    getExportStatus(jobId)
      .then((data) => live && setStatus(data))
      .catch((cause) => live && setError(String(cause)));
    return () => {
      live = false;
    };
  }, [jobId]);

  async function download(format: 'csv' | 'xlsx') {
    setBusy(format);
    setError(null);
    try {
      await downloadExport(jobId, format);
    } catch (cause) {
      setError(
        cause instanceof ApiError ? [cause.message, ...cause.details].join(' \u00b7 ') : String(cause),
      );
    } finally {
      setBusy(null);
    }
  }

  if (error && !status) {
    return (
      <div className="border border-error bg-error-container px-4 py-3 font-data-mono text-data-mono text-on-error-container">
        {error}
      </div>
    );
  }

  if (!status) {
    return <div className="h-48 border border-border-subtle bg-surface-container-low" />;
  }

  const valid = status.valid;

  return (
    <>
      <PageHeader
        title="Delivery Export"
        meta={[
          { label: 'job', value: jobId },
          { label: 'schema', value: `${status.delivery_columns} COLUMNS` },
          { label: 'validation', value: valid ? 'PASS' : 'FAIL' },
        ]}
      />

      {/* Validation banner: the loudest element on the screen when it fails. */}
      <div
        className={[
          'flex flex-wrap items-center gap-4 border px-6 py-5 mb-gutter',
          valid
            ? 'border-ink-graphite bg-surface-bright shadow-[2px_2px_0px_0px_#171715]'
            : 'border-error bg-error-container',
        ].join(' ')}
      >
        <span
          className={[
            'w-8 h-8 flex items-center justify-center shrink-0 border',
            valid ? 'bg-primary border-primary text-on-primary' : 'bg-error border-error text-on-error',
          ].join(' ')}
        >
          {valid ? <Check size={18} strokeWidth={3} /> : <AlertTriangle size={18} strokeWidth={2.5} />}
        </span>
        <div>
          <div className="font-label-caps text-label-caps text-secondary uppercase mb-1">
            Delivery schema: {status.delivery_columns} columns
          </div>
          <div
            className={[
              'font-data-mono text-headline-md leading-none',
              valid ? 'text-ink-graphite' : 'text-on-error-container',
            ].join(' ')}
          >
            VALIDATION {valid ? 'PASS' : 'FAIL'}
          </div>
        </div>
        <div className="ml-auto flex flex-wrap gap-8">
          <div>
            <div className="font-label-caps text-label-caps text-secondary uppercase mb-1">
              Rows ready
            </div>
            <div className="font-data-mono text-headline-md leading-none text-ink-graphite">
              {status.row_count.toLocaleString()}
            </div>
          </div>
          <div>
            <div className="font-label-caps text-label-caps text-secondary uppercase mb-1">
              Rows needing review
            </div>
            <div className="font-data-mono text-headline-md leading-none text-primary">
              {status.rows_needing_review.toLocaleString()}
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-12 gap-gutter">
        <div className="col-span-12 lg:col-span-6">
          <Plate idx={1} label="Download" title="Delivery files" emphasis>
            <p className="font-body-md text-body-md text-secondary mb-6">
              Both files carry exactly {status.delivery_columns} columns in the reference order. CSV
              is UTF-8 with BOM so Excel preserves &reg; and &trade;.
            </p>
            <div className="flex flex-wrap gap-4">
              <Button variant="primary" disabled={!valid || busy !== null} onClick={() => void download('csv')}>
                <FileText size={14} strokeWidth={2} />
                {busy === 'csv' ? 'Preparing\u2026' : 'Download CSV'}
              </Button>
              <Button
                variant="secondary"
                disabled={!valid || busy !== null}
                onClick={() => void download('xlsx')}
              >
                <FileSpreadsheet size={14} strokeWidth={2} />
                {busy === 'xlsx' ? 'Preparing\u2026' : 'Download XLSX'}
              </Button>
            </div>
            {!valid && (
              <div className="mt-5 font-data-mono text-annotation text-on-error-container uppercase">
                Downloads disabled until delivery validation passes.
              </div>
            )}
            {error && (
              <div className="mt-5 border border-error bg-error-container px-3 py-2 font-data-mono text-annotation text-on-error-container">
                {error}
              </div>
            )}
          </Plate>
        </div>

        <div className="col-span-12 lg:col-span-6">
          <Plate idx={2} label={`Validation log (${status.errors.length})`}>
            {status.errors.length === 0 ? (
              <div className="font-data-mono text-data-mono text-secondary uppercase">
                No validation errors or export warnings
              </div>
            ) : (
              <div className="bg-ink-graphite border border-ink-graphite p-4 max-h-64 overflow-y-auto">
                {status.errors.map((message, index) => (
                  <div
                    key={`${message}-${index}`}
                    className="font-data-mono text-annotation text-surface-container-low"
                  >
                    [{String(index + 1).padStart(3, '0')}] {message}
                  </div>
                ))}
              </div>
            )}
          </Plate>
        </div>
      </div>
    </>
  );
}
