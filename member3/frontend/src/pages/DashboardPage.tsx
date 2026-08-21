/**
 * Operational dashboard: KPI plates, quality plates, two charts, and the
 * searchable paginated results table.
 */

import { useEffect, useState } from 'react';
import { getMetrics } from '../api/client';
import { PageHeader } from '../components/AppShell';
import Button from '../components/Button';
import ConfidenceChart from '../components/ConfidenceChart';
import KpiGrid from '../components/KpiGrid';
import Plate from '../components/Plate';
import QualityGrid from '../components/QualityGrid';
import ResultsTable from '../components/ResultsTable';
import StatusChart from '../components/StatusChart';
import type { Screen } from '../App';
import type { Metrics } from '../types';

export default function DashboardPage({
  jobId,
  onOpenRow,
  onNavigate,
}: {
  jobId: string;
  onOpenRow: (rowId: number) => void;
  onNavigate: (screen: Screen) => void;
}) {
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let live = true;
    getMetrics(jobId)
      .then((data) => live && setMetrics(data))
      .catch((cause) => live && setError(String(cause)));
    return () => {
      live = false;
    };
  }, [jobId]);

  if (error) {
    return (
      <div className="border border-error bg-error-container px-4 py-3 font-data-mono text-data-mono text-on-error-container">
        {error}
      </div>
    );
  }

  if (!metrics) {
    // Skeleton plates, never a spinner: the layout lands before the data does.
    return (
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-gutter">
        {Array.from({ length: 5 }, (_, index) => (
          <div key={index} className="h-32 border border-border-subtle bg-surface-container-low" />
        ))}
      </div>
    );
  }

  const benchmark = metrics.benchmark;

  return (
    <>
      <PageHeader
        title="Operational Dashboard"
        meta={[
          { label: 'job', value: jobId },
          { label: 'rows', value: metrics.total.toLocaleString() },
          { label: 'runtime', value: `${metrics.elapsed_seconds.toFixed(2)}S` },
          { label: 'delivery', value: `${metrics.delivery_columns} COLUMNS` },
        ]}
        actions={
          <>
            <Button variant="secondary" onClick={() => onNavigate('review')}>
              Review queue ({metrics.review.toLocaleString()})
            </Button>
            <Button variant="primary" onClick={() => onNavigate('export')}>
              Export delivery
            </Button>
          </>
        }
      />

      <section className="mb-gutter">
        <KpiGrid metrics={metrics} />
      </section>

      <section className="mb-gutter">
        <h2 className="font-label-caps text-label-caps text-ink-graphite uppercase mb-4">
          Quality compliance
        </h2>
        <QualityGrid metrics={metrics} />
      </section>

      <section className="grid grid-cols-12 gap-gutter mb-gutter">
        <div className="col-span-12 lg:col-span-5">
          <Plate idx={13} label="Row status distribution">
            <StatusChart metrics={metrics} />
          </Plate>
        </div>
        <div className="col-span-12 lg:col-span-7">
          <Plate idx={14} label="Confidence histogram">
            <ConfidenceChart metrics={metrics} />
          </Plate>
        </div>
      </section>

      {metrics.review_reasons.length > 0 && (
        <section className="mb-gutter">
          <Plate idx={15} label="Top review reasons">
            <table className="w-full border-collapse">
              <thead>
                <tr className="border-b border-ink-graphite">
                  <th className="text-left font-label-caps text-label-caps text-secondary uppercase pb-2">
                    Reason
                  </th>
                  <th className="text-right font-label-caps text-label-caps text-secondary uppercase pb-2">
                    Rows
                  </th>
                </tr>
              </thead>
              <tbody>
                {metrics.review_reasons.slice(0, 8).map((reason) => (
                  <tr key={reason.reason} className="border-b border-border-subtle last:border-b-0">
                    <td className="py-2 font-body-md text-body-md text-ink-graphite">
                      {reason.reason}
                    </td>
                    <td className="py-2 text-right font-data-mono text-data-mono text-ink-graphite">
                      {reason.count.toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Plate>
        </section>
      )}

      {benchmark && benchmark.matched_rows > 0 && (
        <section className="mb-gutter">
          <Plate
            idx={16}
            label="Ground-truth benchmark"
            title={`${benchmark.overall_normalized_match_rate.toFixed(1)}% normalized match`}
            emphasis
          >
            <div className="font-annotation text-annotation text-secondary uppercase mb-4">
              {benchmark.matched_rows} of {benchmark.ground_truth_rows} labelled rows matched by MPN
            </div>
            <table className="w-full border-collapse">
              <thead>
                <tr className="border-b border-ink-graphite">
                  {['Field', 'Compared', 'Exact', 'Normalized'].map((heading, index) => (
                    <th
                      key={heading}
                      className={[
                        'font-label-caps text-label-caps text-secondary uppercase pb-2',
                        index === 0 ? 'text-left' : 'text-right',
                      ].join(' ')}
                    >
                      {heading}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {benchmark.fields
                  .filter((field) => field.compared > 0)
                  .map((field) => (
                    <tr key={field.field} className="border-b border-border-subtle last:border-b-0">
                      <td className="py-2 font-data-mono text-data-mono text-ink-graphite">
                        {field.field}
                      </td>
                      <td className="py-2 text-right font-data-mono text-data-mono text-secondary">
                        {field.compared}
                      </td>
                      <td className="py-2 text-right font-data-mono text-data-mono text-ink-graphite">
                        {field.exact_match_rate.toFixed(1)}%
                      </td>
                      <td className="py-2 text-right font-data-mono text-data-mono text-primary">
                        {field.normalized_match_rate.toFixed(1)}%
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </Plate>
        </section>
      )}

      <section>
        <h2 className="font-label-caps text-label-caps text-ink-graphite uppercase mb-4">
          Enriched records
        </h2>
        <ResultsTable jobId={jobId} onOpenRow={onOpenRow} />
      </section>
    </>
  );
}
