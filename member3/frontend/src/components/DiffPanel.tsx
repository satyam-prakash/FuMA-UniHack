/**
 * Field-by-field comparison column. RAW INPUT | GENERATED | GROUND TRUTH.
 *
 * A changed field takes a 2px terracotta left rule, so what the pipeline
 * actually altered is visible without reading both columns character by
 * character.
 */

export interface DiffField {
  label: string;
  value: string;
  /** True when this value differs from the raw/source column. */
  changed?: boolean;
  note?: string;
}

interface DiffPanelProps {
  idx: number;
  heading: string;
  subheading?: string;
  fields: DiffField[];
  emphasis?: boolean;
}

export default function DiffPanel({
  idx,
  heading,
  subheading,
  fields,
  emphasis = false,
}: DiffPanelProps) {
  return (
    <div
      className={[
        'relative flex flex-col bg-surface-bright border h-full',
        emphasis
          ? 'border-ink-graphite shadow-[2px_2px_0px_0px_#171715]'
          : 'border-border-subtle',
      ].join(' ')}
    >
      <div
        className={[
          'absolute top-3 right-4 font-annotation text-annotation',
          emphasis ? 'text-ink-graphite font-bold' : 'text-secondary',
        ].join(' ')}
      >
        IDX-{String(idx).padStart(2, '0')}
      </div>

      <div
        className={[
          'px-6 pt-5 pb-4 border-b',
          emphasis
            ? 'border-ink-graphite bg-background'
            : 'border-border-subtle bg-surface-container-low',
        ].join(' ')}
      >
        <h2 className="font-label-caps text-label-caps text-secondary uppercase tracking-widest pr-16">
          {heading}
        </h2>
        {subheading && (
          <div className="font-data-mono text-data-mono text-ink-graphite mt-1 truncate">
            {subheading}
          </div>
        )}
      </div>

      <div className="p-6 flex flex-col gap-4">
        {fields.map((field) => (
          <div
            key={field.label}
            className={[
              'flex flex-col border-b border-border-subtle pb-2 last:border-b-0',
              // 2px terracotta rule marks a value the pipeline changed.
              field.changed ? 'border-l-2 border-l-primary pl-3' : '',
            ].join(' ')}
          >
            <span className="font-label-caps text-annotation text-secondary uppercase mb-1">
              {field.label}
            </span>
            <span className="font-data-mono text-data-mono text-ink-graphite break-words">
              {field.value || '\u2014'}
            </span>
            {field.note && (
              <span className="font-annotation text-annotation text-primary uppercase mt-1">
                {field.note}
              </span>
            )}
          </div>
        ))}

        {fields.length === 0 && (
          <span className="font-data-mono text-data-mono text-secondary uppercase">
            No data for this column
          </span>
        )}
      </div>
    </div>
  );
}
