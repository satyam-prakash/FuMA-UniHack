/**
 * Row status distribution, hand-rolled SVG.
 *
 * Not a chart library: recharts' bundle hangs the Vite transform on this
 * machine, and its defaults (rounded bars, soft tooltips) would each need
 * overriding to satisfy the 0px-radius rule. A bar chart is ~40 lines of SVG.
 */

import type { Metrics } from '../types';

/** success -> olive, review -> terracotta (needs a human), error -> charcoal. */
const FILLS: Record<string, string> = {
  success: '#5b5f4d',
  review: '#994422',
  error: '#34332F',
};

const WIDTH = 420;
const HEIGHT = 240;
const PAD = { top: 16, right: 8, bottom: 40, left: 48 };

export default function StatusChart({ metrics }: { metrics: Metrics }) {
  const data = metrics.status_distribution;
  const max = Math.max(1, ...data.map((entry) => entry.count));
  const plotWidth = WIDTH - PAD.left - PAD.right;
  const plotHeight = HEIGHT - PAD.top - PAD.bottom;
  const slot = plotWidth / Math.max(1, data.length);
  const barWidth = Math.min(72, slot * 0.55);

  // Four gridlines is enough to read a value without turning into graph paper.
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((fraction) => Math.round(max * fraction));

  return (
    <svg
      viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
      className="w-full h-auto"
      role="img"
      aria-label="Row status distribution"
    >
      {ticks.map((tick) => {
        const y = PAD.top + plotHeight - (tick / max) * plotHeight;
        return (
          <g key={tick}>
            <line x1={PAD.left} y1={y} x2={WIDTH - PAD.right} y2={y} stroke="#D8D2C8" strokeWidth={1} />
            <text
              x={PAD.left - 8}
              y={y + 4}
              textAnchor="end"
              fill="#5f5e5b"
              fontFamily="IBM Plex Mono"
              fontSize={11}
            >
              {tick}
            </text>
          </g>
        );
      })}

      {/* Charcoal baseline, square ends. */}
      <line
        x1={PAD.left}
        y1={PAD.top + plotHeight}
        x2={WIDTH - PAD.right}
        y2={PAD.top + plotHeight}
        stroke="#34332F"
        strokeWidth={1}
      />

      {data.map((entry, index) => {
        const height = (entry.count / max) * plotHeight;
        const x = PAD.left + slot * index + (slot - barWidth) / 2;
        return (
          <g key={entry.status}>
            <rect
              x={x}
              y={PAD.top + plotHeight - height}
              width={barWidth}
              height={height}
              fill={FILLS[entry.status] ?? '#5f5e5b'}
            />
            <text
              x={x + barWidth / 2}
              y={PAD.top + plotHeight - height - 6}
              textAnchor="middle"
              fill="#34332F"
              fontFamily="IBM Plex Mono"
              fontSize={11}
              fontWeight={600}
            >
              {entry.count.toLocaleString()}
            </text>
            <text
              x={x + barWidth / 2}
              y={HEIGHT - 14}
              textAnchor="middle"
              fill="#5f5e5b"
              fontFamily="IBM Plex Mono"
              fontSize={11}
              letterSpacing="0.08em"
            >
              {entry.status.toUpperCase()}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
