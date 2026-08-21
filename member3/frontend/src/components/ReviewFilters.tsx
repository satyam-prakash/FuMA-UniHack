/**
 * Review category filter chips. Rectangular, mono, active = solid charcoal.
 *
 * Filtering reads `review.categories`, the exact literals the pipeline emits,
 * rather than pattern-matching the human-readable reason strings.
 */

import type { ReviewCategory, RowResult } from '../types';

export type FilterKey = 'all' | ReviewCategory;

export const FILTER_LABELS: Record<FilterKey, string> = {
  all: 'All',
  low_confidence: 'Low confidence',
  schema_failure: 'Schema failure',
  no_attributes: 'No attributes',
  generic_taxonomy: 'Generic taxonomy',
  description_issue: 'Description issue',
  export_issue: 'Export issue',
  processing_error: 'Processing error',
};

export const FILTER_ORDER: FilterKey[] = [
  'all',
  'low_confidence',
  'schema_failure',
  'no_attributes',
  'generic_taxonomy',
  'description_issue',
  'export_issue',
  'processing_error',
];

/** True when a row belongs in the given filter. */
export function matchesFilter(row: RowResult, filter: FilterKey): boolean {
  if (filter === 'all') return true;
  return row.review.categories.includes(filter);
}

export default function ReviewFilters({
  active,
  counts,
  onChange,
}: {
  active: FilterKey;
  counts: Record<FilterKey, number>;
  onChange: (filter: FilterKey) => void;
}) {
  return (
    <div className="flex flex-wrap items-center gap-2 mb-6">
      {FILTER_ORDER.map((filter) => (
        <button
          key={filter}
          type="button"
          onClick={() => onChange(filter)}
          className={[
            'h-8 px-3 border font-label-caps text-annotation uppercase transition-colors active:scale-95',
            active === filter
              ? 'bg-ink-graphite text-surface-container-lowest border-ink-graphite'
              : 'bg-transparent text-secondary border-border-subtle hover:border-ink-graphite hover:text-ink-graphite',
          ].join(' ')}
        >
          {FILTER_LABELS[filter]}
          <span className="ml-2 font-data-mono">{counts[filter] ?? 0}</span>
        </button>
      ))}
    </div>
  );
}
