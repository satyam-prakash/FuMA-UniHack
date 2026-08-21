/**
 * Quality compliance plates.
 *
 * The two mobile KPIs are deliberately separate cards:
 *   "Mobile (schema <= 85)"  is what ProductRecord actually enforces.
 *   "Mobile (target 60-80)"  is the stricter client target.
 * Merging them would let the dashboard claim compliance it has not earned, so
 * they never share a card, a number, or a label.
 */

import Plate from './Plate';
import { PassChip } from './StatChip';
import type { Metrics } from '../types';

interface Gauge {
  label: string;
  rate: number;
  target: number;
  note: string;
}

export default function QualityGrid({ metrics }: { metrics: Metrics }) {
  const gauges: Gauge[] = [
    {
      label: 'Invoice ≤ 40 chars',
      rate: metrics.invoice_char_pass,
      target: 100,
      note: 'INVOICE_DESC length',
    },
    {
      label: 'Invoice ALL CAPS',
      rate: metrics.invoice_caps_pass,
      target: 100,
      note: 'INVOICE_DESC casing',
    },
    {
      label: 'Mobile (schema ≤ 85)',
      rate: metrics.schema_mobile_pass,
      target: 100,
      note: 'Limit ProductRecord enforces',
    },
    {
      label: 'Mobile (target 60–80)',
      rate: metrics.mobile_target_60_80_pass,
      target: 90,
      note: 'Stricter client window',
    },
    {
      label: 'Schema pass',
      rate: metrics.schema_pass_rate,
      target: 100,
      note: 'ProductRecord revalidation',
    },
    {
      label: 'Classpath specific',
      rate: metrics.classpath_specific_rate,
      target: 95,
      note: 'Non-generic taxonomy',
    },
    {
      label: 'Attribute coverage',
      rate: metrics.attribute_coverage,
      target: 90,
      note: 'Rows with ≥ 1 attribute',
    },
  ];

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-gutter">
      {gauges.map((gauge, index) => {
        const pass = gauge.rate >= gauge.target;
        return (
          <Plate key={gauge.label} idx={index + 6} bodyClassName="p-5">
            <div className="font-label-caps text-label-caps text-secondary uppercase mb-3 pr-14 min-h-[32px]">
              {gauge.label}
            </div>
            <div className="flex items-end justify-between mb-3">
              <span className="font-data-mono text-headline-md leading-none text-ink-graphite">
                {gauge.rate.toFixed(1)}%
              </span>
              <PassChip pass={pass} />
            </div>
            {/* Hairline meter: charcoal track, terracotta fill, square ends. */}
            <div className="h-2 border border-border-subtle bg-surface-container-low mb-2">
              <div
                className={pass ? 'h-full bg-primary' : 'h-full bg-ink-graphite'}
                style={{ width: `${Math.min(100, gauge.rate)}%` }}
              />
            </div>
            <div className="font-annotation text-annotation text-secondary uppercase">
              {gauge.note} · target {gauge.target}%
            </div>
          </Plate>
        );
      })}
    </div>
  );
}
