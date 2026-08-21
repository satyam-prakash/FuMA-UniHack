/**
 * 64px top bar from the stitch reference: Instrument Serif `FuMA` wordmark,
 * mono search affordance, nav links where the active one takes a 2px
 * terracotta underline.
 */

import { Search } from './icons';
import type { Screen } from '../App';

const LINKS: { screen: Screen; label: string }[] = [
  { screen: 'upload', label: 'Ingest' },
  { screen: 'dashboard', label: 'Enrichment' },
  { screen: 'review', label: 'Quality Control' },
  { screen: 'export', label: 'Delivery' },
];

interface TopBarProps {
  screen: Screen;
  onNavigate: (screen: Screen) => void;
  jobId: string | null;
  jobLabel?: string;
}

export default function TopBar({ screen, onNavigate, jobId, jobLabel }: TopBarProps) {
  return (
    <header className="w-full h-16 shrink-0 border-b border-border-subtle bg-background flex justify-between items-center px-margin-desktop">
      <div className="flex items-center gap-8">
        <div className="font-headline-md text-headline-md text-ink-graphite uppercase tracking-tighter leading-none">
          FuMA
        </div>
        <div className="hidden md:flex items-center border border-border-subtle bg-surface-bright h-8 px-3 w-64 text-secondary">
          <Search size={14} strokeWidth={1.75} className="mr-2 shrink-0" />
          <span className="font-data-mono text-annotation uppercase truncate">
            {jobLabel ?? 'No job loaded'}
          </span>
        </div>
      </div>

      <nav className="hidden md:flex items-center gap-8 font-body-md text-body-md font-medium">
        {LINKS.map(({ screen: target, label }) => {
          const active = screen === target || (target === 'dashboard' && screen === 'detail');
          const locked = jobId === null && target !== 'upload';
          return (
            <button
              key={target}
              type="button"
              disabled={locked}
              onClick={() => onNavigate(target)}
              className={[
                'pb-1 transition-colors duration-200 active:scale-95',
                active
                  ? 'text-primary border-b-2 border-primary'
                  : 'text-secondary hover:text-primary border-b-2 border-transparent',
                locked ? 'opacity-35 cursor-not-allowed hover:text-secondary' : '',
              ].join(' ')}
            >
              {label}
            </button>
          );
        })}
      </nav>

      <div className="font-data-mono text-annotation text-secondary uppercase hidden lg:block">
        {jobId ? `JOB: ${jobId}` : 'JOB: —'}
      </div>
    </header>
  );
}
