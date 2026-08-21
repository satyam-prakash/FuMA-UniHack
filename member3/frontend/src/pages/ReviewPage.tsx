/**
 * Human review queue. Decisions POST to the API and update the row in place
 * rather than refetching the whole queue, so the operator never loses scroll
 * position mid-triage.
 */

import { useEffect, useMemo, useState } from 'react';
import { getReviewQueue, submitReview } from '../api/client';
import { PageHeader } from '../components/AppShell';
import Button from '../components/Button';
import ReviewFilters, {
  FILTER_ORDER,
  FILTER_LABELS,
  matchesFilter,
  type FilterKey,
} from '../components/ReviewFilters';
import StatChip, { StatusChip } from '../components/StatChip';
import type { ReviewAction, ReviewRow } from '../types';

const ACTIONS: { action: ReviewAction; label: string }[] = [
  { action: 'approve', label: 'Approve' },
  { action: 'override', label: 'Override' },
  { action: 'mark_reviewed', label: 'Mark reviewed' },
];

const CATEGORIES: FilterKey[] = FILTER_ORDER;

export default function ReviewPage({
  jobId,
  onOpenRow,
}: {
  jobId: string;
  onOpenRow: (rowId: number) => void;
}) {
  const [rows, setRows] = useState<ReviewRow[]>([]);
  const [category, setCategory] = useState<FilterKey>('all');
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState<number | null>(null);

  useEffect(() => {
    let live = true;
    getReviewQueue(jobId)
      .then((data) => live && setRows(data.rows))
      .catch((cause) => live && setError(String(cause)));
    return () => {
      live = false;
    };
  }, [jobId]);

  const counts = useMemo(() => {
    const tally = {} as Record<FilterKey, number>;
    for (const option of CATEGORIES) {
      tally[option] = rows.filter((row) => matchesFilter(row, option)).length;
    }
    return tally;
  }, [rows]);

  const visible = rows.filter((row) => matchesFilter(row, category));

  async function decide(row: ReviewRow, action: ReviewAction) {
    setPending(row.row_id);
    setError(null);
    try {
      const response = await submitReview(jobId, row.row_id, action);
      setRows((current) =>
        current.map((candidate) =>
          candidate.row_id === row.row_id ? { ...candidate, decision: response.review.decision } : candidate,
        ),
      );
    } catch (cause) {
      setError(String(cause));
    } finally {
      setPending(null);
    }
  }

  return (
    <>
      <PageHeader
        title="Review Queue"
        meta={[
          { label: 'job', value: jobId },
          { label: 'flagged', value: rows.length.toLocaleString() },
          { label: 'filter', value: FILTER_LABELS[category].toUpperCase() },
        ]}
      />

      <ReviewFilters active={category} counts={counts} onChange={setCategory} />

      {error && (
        <div className="mb-4 border border-error bg-error-container px-4 py-2 font-data-mono text-data-mono text-on-error-container">
          {error}
        </div>
      )}

      <div className="border border-border-subtle bg-surface-bright overflow-x-auto">
        <table className="w-full border-collapse">
          <thead>
            <tr className="border-b border-ink-graphite">
              {['MPN', 'Confidence', 'Reasons', 'Status', 'Decision', 'Actions'].map((heading) => (
                <th
                  key={heading}
                  className="text-left font-label-caps text-label-caps text-secondary uppercase px-4 py-3 whitespace-nowrap"
                >
                  {heading}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {visible.map((row) => (
              <tr key={row.row_id} className="border-b border-border-subtle last:border-b-0 align-top">
                <td className="px-4 py-3">
                  <button
                    type="button"
                    onClick={() => onOpenRow(row.row_id)}
                    className="font-data-mono text-data-mono text-ink-graphite underline decoration-border-subtle hover:decoration-primary hover:text-primary transition-colors text-left"
                  >
                    {row.mpn || `ROW-${row.row_id}`}
                  </button>
                </td>
                <td className="px-4 py-3 font-data-mono text-data-mono text-ink-graphite">
                  {row.confidence_score.toFixed(1)}
                </td>
                <td className="px-4 py-3 max-w-[26rem]">
                  <div className="flex flex-col gap-1">
                    {row.reasons.length === 0 ? (
                      <span className="font-data-mono text-annotation text-secondary uppercase">
                        —
                      </span>
                    ) : (
                      row.reasons.map((reason) => (
                        <span
                          key={reason}
                          className="font-data-mono text-annotation text-ink-graphite border-l-2 border-l-primary pl-2"
                        >
                          {reason}
                        </span>
                      ))
                    )}
                  </div>
                </td>
                <td className="px-4 py-3">
                  <StatusChip status={row.status} />
                </td>
                <td className="px-4 py-3">
                  {row.decision ? (
                    <StatChip tone="accent">{row.decision.action.replace('_', ' ')}</StatChip>
                  ) : (
                    <StatChip tone="neutral">pending</StatChip>
                  )}
                </td>
                <td className="px-4 py-3">
                  <div className="flex flex-wrap gap-2">
                    {ACTIONS.map(({ action, label }) => (
                      <Button
                        key={action}
                        size="sm"
                        variant={action === 'approve' ? 'primary' : 'ghost'}
                        disabled={pending === row.row_id}
                        onClick={() => void decide(row, action)}
                      >
                        {label}
                      </Button>
                    ))}
                  </div>
                </td>
              </tr>
            ))}

            {visible.length === 0 && (
              <tr>
                <td
                  colSpan={6}
                  className="px-4 py-8 text-center font-data-mono text-data-mono text-secondary uppercase"
                >
                  Nothing flagged in this category
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </>
  );
}
