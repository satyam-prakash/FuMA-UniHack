/**
 * Headline KPI plates. Key figures carry the terracotta accent; the rest stay
 * charcoal so the accent keeps its meaning (7% of the palette, not 40%).
 */

import Plate from './Plate';
import type { Metrics } from '../types';

interface Kpi {
  label: string;
  value: string;
  note: string;
  accent?: boolean;
}

export default function KpiGrid({ metrics }: { metrics: Metrics }) {
  const kpis: Kpi[] = [
    { label: 'Total rows', value: metrics.total.toLocaleString(), note: 'ingested' },
    {
      label: 'Processed',
      value: (metrics.success + metrics.review + metrics.errors).toLocaleString(),
      note: `${metrics.errors.toLocaleString()} errors`,
    },
    {
      label: 'Success rate',
      value: `${metrics.success_rate.toFixed(1)}%`,
      note: `${metrics.success.toLocaleString()} clean rows`,
      accent: true,
    },
    {
      label: 'Needs review',
      value: metrics.review.toLocaleString(),
      note: `${((metrics.review / Math.max(1, metrics.total)) * 100).toFixed(1)}% of batch`,
    },
    {
      label: 'Avg confidence',
      value: metrics.avg_confidence.toFixed(1),
      note: `${metrics.avg_attributes.toFixed(1)} attrs/row`,
      accent: true,
    },
  ];

  return (
    <div className="grid grid-cols-2 lg:grid-cols-5 gap-gutter">
      {kpis.map((kpi, index) => (
        <Plate key={kpi.label} idx={index + 1} bodyClassName="p-5">
          <div className="font-label-caps text-label-caps text-secondary uppercase mb-3 pr-14">
            {kpi.label}
          </div>
          <div
            className={[
              'font-data-mono text-headline-md leading-none mb-2',
              kpi.accent ? 'text-primary' : 'text-ink-graphite',
            ].join(' ')}
          >
            {kpi.value}
          </div>
          <div className="font-annotation text-annotation text-secondary uppercase">{kpi.note}</div>
        </Plate>
      ))}
    </div>
  );
}
