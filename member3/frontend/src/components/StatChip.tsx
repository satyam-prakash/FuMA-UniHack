/**
 * Rectangular status chip. 1px border, mono text, no radius.
 * `tone` maps to the palette: terracotta is reserved for genuine signal,
 * so a neutral pass renders in charcoal/olive rather than accent.
 */

import type { ReactNode } from 'react';

export type ChipTone = 'neutral' | 'pass' | 'warn' | 'fail' | 'accent';

const TONES: Record<ChipTone, string> = {
  neutral: 'border-border-subtle bg-surface-variant text-secondary',
  pass: 'border-tertiary bg-tertiary-fixed text-on-tertiary-fixed',
  warn: 'border-ink-graphite bg-surface-variant text-ink-graphite',
  fail: 'border-error bg-error-container text-on-error-container',
  accent: 'border-primary bg-primary text-on-primary',
};

interface StatChipProps {
  tone?: ChipTone;
  children: ReactNode;
  className?: string;
}

export default function StatChip({ tone = 'neutral', children, className = '' }: StatChipProps) {
  return (
    <span
      className={[
        'inline-flex items-center gap-1 border px-2 py-[2px]',
        'font-label-caps text-annotation uppercase whitespace-nowrap',
        TONES[tone],
        className,
      ].join(' ')}
    >
      {children}
    </span>
  );
}

/** PASS/FAIL chip used across quality plates and the detail screen. */
export function PassChip({ pass, label }: { pass: boolean; label?: string }) {
  return <StatChip tone={pass ? 'pass' : 'fail'}>{label ?? (pass ? 'PASS' : 'FAIL')}</StatChip>;
}

/** Row status chip. Only `error` earns a loud colour; review stays charcoal. */
export function StatusChip({ status }: { status: string }) {
  const tone: ChipTone = status === 'error' ? 'fail' : status === 'review' ? 'warn' : 'pass';
  return <StatChip tone={tone}>{status}</StatChip>;
}
