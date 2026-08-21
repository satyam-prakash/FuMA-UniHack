/**
 * Left rail from stitch_fuma_industrial_data_foundry/code.html:
 * 80px collapsed, expands to 256px on hover, `OP` identity block, mono labels.
 * Active item takes the terracotta right-edge marker (accent used sparingly).
 */

import {
  ClipboardCheck,
  Download,
  LayoutDashboard,
  ListChecks,
  Upload,
} from './icons';
import type { ComponentType, SVGProps } from 'react';
import type { Screen } from '../App';

type IconComponent = ComponentType<SVGProps<SVGSVGElement> & { size?: number; strokeWidth?: number }>;

interface NavItem {
  screen: Screen;
  label: string;
  Icon: IconComponent;
}

const ITEMS: NavItem[] = [
  { screen: 'upload', label: 'Ingest', Icon: Upload },
  { screen: 'processing', label: 'Pipeline', Icon: ListChecks },
  { screen: 'dashboard', label: 'Dashboard', Icon: LayoutDashboard },
  { screen: 'review', label: 'Review', Icon: ClipboardCheck },
  { screen: 'export', label: 'Export', Icon: Download },
];

interface SideNavProps {
  screen: Screen;
  onNavigate: (screen: Screen) => void;
  /** Screens that need a finished job stay disabled until one exists. */
  jobId: string | null;
}

export default function SideNav({ screen, onNavigate, jobId }: SideNavProps) {
  return (
    <nav className="group h-screen w-20 hover:w-64 transition-[width] duration-300 ease-out border-r border-border-subtle bg-surface-container-low flex flex-col py-unit overflow-hidden shrink-0 z-20">
      {/* Identity block */}
      <div className="px-6 py-4 border-b border-border-subtle flex items-center gap-4 mb-4">
        <div className="w-8 h-8 bg-ink-graphite text-surface-container-lowest flex items-center justify-center font-data-mono text-data-mono shrink-0">
          OP
        </div>
        <div className="opacity-0 group-hover:opacity-100 transition-opacity duration-300 whitespace-nowrap">
          <div className="font-data-mono text-data-mono text-ink-graphite uppercase">OPERATOR_01</div>
          <div className="font-label-caps text-label-caps text-secondary uppercase">Technical Lead</div>
        </div>
      </div>

      <div className="flex-grow flex flex-col gap-1 w-full">
        {ITEMS.map(({ screen: target, label, Icon }) => {
          const active = screen === target;
          const locked = jobId === null && target !== 'upload';
          return (
            <button
              key={target}
              type="button"
              disabled={locked}
              onClick={() => onNavigate(target)}
              title={label}
              className={[
                'flex items-center px-6 py-3 w-full text-left transition-colors',
                active
                  ? 'bg-primary-container text-on-primary-container border-r-4 border-primary'
                  : 'text-secondary hover:bg-surface-variant hover:text-ink-graphite',
                locked ? 'opacity-35 cursor-not-allowed hover:bg-transparent' : '',
              ].join(' ')}
            >
              <Icon size={20} strokeWidth={1.75} className="shrink-0" />
              <span className="ml-4 font-label-caps text-label-caps uppercase whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                {label}
              </span>
            </button>
          );
        })}
      </div>

      <div className="px-4 py-4 mt-auto border-t border-border-subtle">
        <div className="font-annotation text-annotation text-secondary uppercase whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity duration-300">
          Delivery schema
          <div className="font-data-mono text-data-mono text-ink-graphite">252 COLUMNS</div>
        </div>
      </div>
    </nav>
  );
}
