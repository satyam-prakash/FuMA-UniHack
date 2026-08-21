/**
 * Technical plate: the card replacement from DESIGN.md. 1px outline, no radius,
 * and a mono `IDX-nn` serial in the top-right corner to read as a machined part.
 */

import type { ReactNode } from 'react';

interface PlateProps {
  /** Serial number; rendered as `IDX-07`. */
  idx?: number;
  label?: string;
  title?: ReactNode;
  /** Charcoal outline + hard stamp shadow for the emphasised plate on a screen. */
  emphasis?: boolean;
  className?: string;
  bodyClassName?: string;
  children?: ReactNode;
}

export default function Plate({
  idx,
  label,
  title,
  emphasis = false,
  className = '',
  bodyClassName = 'p-6',
  children,
}: PlateProps) {
  return (
    <div
      className={[
        'relative flex flex-col bg-surface-bright border',
        emphasis
          ? 'border-ink-graphite shadow-[2px_2px_0px_0px_#171715]'
          : 'border-border-subtle',
        className,
      ].join(' ')}
    >
      {idx !== undefined && (
        <div
          className={[
            'absolute top-3 right-4 font-annotation text-annotation',
            emphasis ? 'text-ink-graphite font-bold' : 'text-secondary',
          ].join(' ')}
        >
          IDX-{String(idx).padStart(2, '0')}
        </div>
      )}
      {(label || title) && (
        <div
          className={[
            'px-6 pt-5 pb-4 border-b',
            emphasis ? 'border-ink-graphite bg-background' : 'border-border-subtle bg-surface-container-low',
          ].join(' ')}
        >
          {label && (
            <h2 className="font-label-caps text-label-caps text-secondary uppercase tracking-widest pr-16">
              {label}
            </h2>
          )}
          {title && (
            <div className="font-headline-md text-headline-md text-ink-graphite mt-1 leading-none">
              {title}
            </div>
          )}
        </div>
      )}
      <div className={['flex-grow', bodyClassName].join(' ')}>{children}</div>
    </div>
  );
}
