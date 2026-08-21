/** Shell: fixed left rail + 64px top bar + scrolling canvas at 64px margins. */

import type { ReactNode } from 'react';
import type { Screen } from '../App';
import SideNav from './SideNav';
import TopBar from './TopBar';

interface AppShellProps {
  screen: Screen;
  onNavigate: (screen: Screen) => void;
  jobId: string | null;
  jobLabel?: string;
  children: ReactNode;
}

export default function AppShell({
  screen,
  onNavigate,
  jobId,
  jobLabel,
  children,
}: AppShellProps) {
  return (
    <div className="h-screen flex overflow-hidden bg-background text-on-background">
      <SideNav screen={screen} onNavigate={onNavigate} jobId={jobId} />
      <div className="flex-grow flex flex-col h-full overflow-hidden">
        <TopBar screen={screen} onNavigate={onNavigate} jobId={jobId} jobLabel={jobLabel} />
        <main className="flex-grow overflow-auto p-margin-desktop">{children}</main>
      </div>
    </div>
  );
}

/**
 * Screen header: Instrument Serif title, mono meta chips, right-aligned actions.
 * Closed with a charcoal rule, matching the reference context header.
 */
export function PageHeader({
  title,
  meta = [],
  actions,
}: {
  title: string;
  meta?: { label: string; value?: string }[];
  actions?: ReactNode;
}) {
  return (
    <div className="flex flex-wrap gap-6 justify-between items-end mb-10 border-b border-ink-graphite pb-4">
      <div>
        <h1 className="font-headline-lg text-headline-lg text-ink-graphite tracking-tight mb-2 leading-none">
          {title}
        </h1>
        {meta.length > 0 && (
          <div className="flex flex-wrap items-center gap-3 font-data-mono text-data-mono text-secondary">
            {meta.map((item) => (
              <span
                key={item.label}
                className="bg-surface-variant px-2 py-1 border border-border-subtle uppercase"
              >
                {item.label}
                {item.value !== undefined && <span className="text-ink-graphite">: {item.value}</span>}
              </span>
            ))}
          </div>
        )}
      </div>
      {actions && <div className="flex items-center gap-4">{actions}</div>}
    </div>
  );
}
