/**
 * Live pipeline screen. Polls GET /api/jobs/{id} every 400ms until the job
 * reaches a terminal status, then hands off to the dashboard.
 *
 * No spinner: the progress bar and the mono counters are the loading state, and
 * they carry real information instead of implying motion.
 */

import { useEffect, useRef, useState } from 'react';
import { getJob } from '../api/client';
import Plate from '../components/Plate';
import { PageHeader } from '../components/AppShell';
import { TERMINAL_STATUSES, type Job } from '../types';

const STAGES = [
  'Input validation',
  'Member 1 normalization',
  'Member 2 extraction',
  'Description generation',
  'Validation',
  'Delivery mapping',
] as const;

/** Progress is one linear counter, so stage completion is derived from it. */
function stagesDone(job: Job | null): number {
  if (!job) return 0;
  if (TERMINAL_STATUSES.includes(job.status)) return STAGES.length;
  if (job.status === 'uploaded' || job.status === 'queued') return 1;
  // Processing: input validation is done, the remaining five track progress.
  return 1 + Math.min(4, Math.floor((job.progress / 100) * 5));
}

export default function ProcessingPage({
  jobId,
  onComplete,
}: {
  jobId: string;
  onComplete: () => void;
}) {
  const [job, setJob] = useState<Job | null>(null);
  const [error, setError] = useState<string | null>(null);
  // Ref so the interval callback never fires the handoff twice.
  const handedOff = useRef(false);

  useEffect(() => {
    handedOff.current = false;
    let live = true;
    let timer = 0;

    async function tick() {
      try {
        const next = await getJob(jobId);
        if (!live) return;
        setJob(next);
        if (TERMINAL_STATUSES.includes(next.status) && !handedOff.current) {
          handedOff.current = true;
          window.clearInterval(timer);
          // Let the bar land on 100% before switching screens.
          window.setTimeout(() => {
            if (live) onComplete();
          }, 600);
        }
      } catch (cause) {
        if (live) setError(String(cause));
      }
    }

    void tick();
    timer = window.setInterval(() => void tick(), 400);
    return () => {
      live = false;
      window.clearInterval(timer);
    };
  }, [jobId, onComplete]);

  const done = stagesDone(job);
  const progress = job?.progress ?? 0;

  return (
    <>
      <PageHeader
        title="Pipeline Run"
        meta={[
          { label: 'job', value: jobId },
          { label: 'status', value: (job?.status ?? 'queued').toUpperCase() },
          { label: 'elapsed', value: `${(job?.elapsed_seconds ?? 0).toFixed(2)}S` },
        ]}
      />

      {error && (
        <div className="mb-8 border border-error bg-error-container px-4 py-3 font-data-mono text-data-mono text-on-error-container">
          {error}
        </div>
      )}

      <div className="grid grid-cols-12 gap-gutter">
        {/* Throughput */}
        <div className="col-span-12 lg:col-span-8">
          <Plate idx={1} label="Throughput" emphasis>
            <div className="flex items-end justify-between mb-6">
              <div className="font-data-mono text-[56px] leading-none text-ink-graphite">
                {(job?.processed ?? 0).toLocaleString()}
                <span className="text-secondary text-[28px]"> / {(job?.total ?? 0).toLocaleString()}</span>
              </div>
              <div className="font-data-mono text-headline-md text-primary leading-none">
                {progress}%
              </div>
            </div>

            {/* Square progress bar: 1px charcoal track, terracotta fill. */}
            <div className="h-6 border border-ink-graphite bg-surface-container-low">
              <div
                className="h-full bg-primary transition-[width] duration-300 ease-out"
                style={{ width: `${progress}%` }}
              />
            </div>

            <div className="grid grid-cols-3 gap-gutter mt-8">
              {[
                { label: 'Successful', value: job?.success ?? 0, accent: false },
                { label: 'Needs Review', value: job?.review ?? 0, accent: true },
                { label: 'Errors', value: job?.errors ?? 0, accent: false },
              ].map((counter) => (
                <div key={counter.label} className="border-t border-ink-graphite pt-3">
                  <div className="font-label-caps text-label-caps text-secondary uppercase mb-1">
                    {counter.label}
                  </div>
                  <div
                    className={[
                      'font-data-mono text-headline-md leading-none',
                      counter.accent ? 'text-primary' : 'text-ink-graphite',
                    ].join(' ')}
                  >
                    {counter.value.toLocaleString()}
                  </div>
                </div>
              ))}
            </div>
          </Plate>
        </div>

        {/* Stage stepper */}
        <div className="col-span-12 lg:col-span-4">
          <Plate idx={2} label="Stage sequence">
            <ol className="flex flex-col">
              {STAGES.map((stage, index) => {
                const complete = index < done;
                const active = index === done && !TERMINAL_STATUSES.includes(job?.status ?? 'queued');
                return (
                  <li
                    key={stage}
                    className="flex items-center gap-4 py-3 border-b border-border-subtle last:border-b-0"
                  >
                    {/* Filled terracotta square = done, hollow charcoal = pending. */}
                    <span
                      className={[
                        'w-4 h-4 shrink-0 border',
                        complete
                          ? 'bg-primary border-primary'
                          : active
                            ? 'border-ink-graphite border-2'
                            : 'border-ink-graphite',
                      ].join(' ')}
                    />
                    <span
                      className={[
                        'font-data-mono text-data-mono',
                        complete ? 'text-ink-graphite' : 'text-secondary',
                      ].join(' ')}
                    >
                      {stage}
                    </span>
                    <span className="ml-auto font-annotation text-annotation text-secondary uppercase">
                      {complete ? 'DONE' : active ? 'ACTIVE' : 'PENDING'}
                    </span>
                  </li>
                );
              })}
            </ol>
          </Plate>
        </div>
      </div>
    </>
  );
}
