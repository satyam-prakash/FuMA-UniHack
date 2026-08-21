/**
 * Paginated results table. Server-side page/page_size/status/search so the
 * 252-column payload never reaches the browser wholesale; 7 columns max.
 *
 * Horizontal hairlines only, `label-caps` mono headers, mono cells.
 */

import { useEffect, useState } from 'react';
import { ChevronLeft, ChevronRight, Search } from './icons';
import { getResults } from '../api/client';
import Button from './Button';
import { StatusChip } from './StatChip';
import { enrichedOf, type RowResult, type RowStatus } from '../types';

const PAGE_SIZE = 25;
const STATUSES: (RowStatus | 'all')[] = ['all', 'success', 'review', 'error'];

export default function ResultsTable({
  jobId,
  onOpenRow,
}: {
  jobId: string;
  onOpenRow: (rowId: number) => void;
}) {
  const [rows, setRows] = useState<RowResult[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState<RowStatus | 'all'>('all');
  const [search, setSearch] = useState('');
  const [query, setQuery] = useState('');
  const [error, setError] = useState<string | null>(null);

  // Debounce so typing does not fire a request per keystroke.
  useEffect(() => {
    const timer = window.setTimeout(() => {
      setSearch(query);
      setPage(1);
    }, 250);
    return () => window.clearTimeout(timer);
  }, [query]);

  useEffect(() => {
    let live = true;
    getResults(jobId, { page, pageSize: PAGE_SIZE, status, search })
      .then((data) => {
        if (!live) return;
        setRows(data.rows);
        setTotal(data.total);
        setError(null);
      })
      .catch((cause) => live && setError(String(cause)));
    return () => {
      live = false;
    };
  }, [jobId, page, status, search]);

  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const from = total === 0 ? 0 : (page - 1) * PAGE_SIZE + 1;
  const to = Math.min(total, page * PAGE_SIZE);

  return (
    <div>
      {/* Controls */}
      <div className="flex flex-wrap items-center gap-4 mb-4">
        <div className="flex items-center border border-ink-graphite bg-surface-bright h-8 px-3 w-72 focus-within:border-2 focus-within:border-primary">
          <Search size={14} strokeWidth={1.75} className="text-secondary mr-2 shrink-0" />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="SEARCH MPN / BRAND / CLASSPATH"
            className="w-full bg-transparent outline-none font-data-mono text-annotation uppercase text-ink-graphite placeholder:text-secondary"
          />
        </div>

        <div className="flex items-center gap-2">
          {STATUSES.map((option) => (
            <button
              key={option}
              type="button"
              onClick={() => {
                setStatus(option);
                setPage(1);
              }}
              className={[
                'h-8 px-3 border font-label-caps text-annotation uppercase transition-colors active:scale-95',
                status === option
                  ? 'bg-ink-graphite text-surface-container-lowest border-ink-graphite'
                  : 'bg-transparent text-secondary border-border-subtle hover:border-ink-graphite hover:text-ink-graphite',
              ].join(' ')}
            >
              {option}
            </button>
          ))}
        </div>

        <span className="ml-auto font-data-mono text-annotation text-secondary uppercase">
          {from}&ndash;{to} of {total.toLocaleString()}
        </span>
      </div>

      {error && (
        <div className="mb-4 border border-error bg-error-container px-4 py-2 font-data-mono text-data-mono text-on-error-container">
          {error}
        </div>
      )}

      <div className="border border-border-subtle bg-surface-bright overflow-x-auto">
        <table className="w-full border-collapse">
          <thead>
            <tr className="border-b border-ink-graphite">
              {['MPN', 'Part description', 'Brand', 'Product type', 'Classpath', 'Confidence', 'Status'].map(
                (heading) => (
                  <th
                    key={heading}
                    className="text-left font-label-caps text-label-caps text-secondary uppercase px-4 py-3 whitespace-nowrap"
                  >
                    {heading}
                  </th>
                ),
              )}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const enriched = enrichedOf(row);
              return (
                <tr
                  key={row.row_id}
                  onClick={() => onOpenRow(row.row_id)}
                  className="border-b border-border-subtle last:border-b-0 cursor-pointer hover:bg-surface-variant transition-colors"
                >
                  <td className="px-4 py-3 font-data-mono text-data-mono text-ink-graphite whitespace-nowrap">
                    {row.mpn || enriched.mfg_part_num || '\u2014'}
                  </td>
                  <td className="px-4 py-3 font-body-md text-body-md text-ink-graphite max-w-[22rem] truncate">
                    {row.part_desc || enriched.part_desc_raw || '\u2014'}
                  </td>
                  <td className="px-4 py-3 font-data-mono text-data-mono text-ink-graphite whitespace-nowrap">
                    {enriched.brand_name || '\u2014'}
                  </td>
                  <td className="px-4 py-3 font-data-mono text-data-mono text-ink-graphite max-w-[14rem] truncate">
                    {enriched.product_name || '\u2014'}
                  </td>
                  <td className="px-4 py-3 font-data-mono text-annotation text-secondary max-w-[18rem] truncate">
                    {enriched.classpath || '\u2014'}
                  </td>
                  <td className="px-4 py-3 font-data-mono text-data-mono text-ink-graphite">
                    {row.confidence.toFixed(1)}
                  </td>
                  <td className="px-4 py-3">
                    <StatusChip status={row.status} />
                  </td>
                </tr>
              );
            })}

            {rows.length === 0 && (
              <tr>
                <td
                  colSpan={7}
                  className="px-4 py-8 text-center font-data-mono text-data-mono text-secondary uppercase"
                >
                  No rows match this filter
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between mt-4">
        <span className="font-data-mono text-annotation text-secondary uppercase">
          Page {page} / {pages}
        </span>
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            disabled={page <= 1}
            onClick={() => setPage((current) => Math.max(1, current - 1))}
          >
            <ChevronLeft size={14} strokeWidth={2} /> Prev
          </Button>
          <Button
            variant="ghost"
            size="sm"
            disabled={page >= pages}
            onClick={() => setPage((current) => Math.min(pages, current + 1))}
          >
            Next <ChevronRight size={14} strokeWidth={2} />
          </Button>
        </div>
      </div>
    </div>
  );
}
