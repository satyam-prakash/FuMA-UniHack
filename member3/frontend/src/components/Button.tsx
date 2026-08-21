/**
 * Perfectly rectangular button, per DESIGN.md.
 *  primary   -> solid terracotta + cream text + hard stamp shadow
 *  secondary -> 1px charcoal border, transparent fill
 *  ghost     -> hairline border, for low-emphasis table actions
 */

import type { ButtonHTMLAttributes, ReactNode } from 'react';

type Variant = 'primary' | 'secondary' | 'ghost';
type Size = 'sm' | 'md';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  children: ReactNode;
}

const VARIANTS: Record<Variant, string> = {
  primary:
    'bg-primary text-on-primary border border-primary hover:bg-primary-container shadow-[2px_2px_0px_0px_#171715]',
  secondary: 'bg-transparent text-ink-graphite border border-ink-graphite hover:bg-surface-variant',
  ghost: 'bg-transparent text-secondary border border-border-subtle hover:border-ink-graphite hover:text-ink-graphite',
};

const SIZES: Record<Size, string> = {
  sm: 'h-8 px-3',
  md: 'h-10 px-6',
};

export default function Button({
  variant = 'secondary',
  size = 'md',
  className = '',
  children,
  ...rest
}: ButtonProps) {
  return (
    <button
      {...rest}
      className={[
        'inline-flex items-center justify-center gap-2 font-label-caps text-label-caps uppercase',
        // 120ms press feedback: fast enough to read as "the UI heard me".
        'transition-transform duration-150 ease-out active:scale-[0.97]',
        'disabled:opacity-40 disabled:cursor-not-allowed disabled:active:scale-100 disabled:shadow-none',
        SIZES[size],
        VARIANTS[variant],
        className,
      ].join(' ')}
    >
      {children}
    </button>
  );
}
