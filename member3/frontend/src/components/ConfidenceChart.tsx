/**
 * Confidence histogram (buckets of 10), hand-rolled SVG.
 * Terracotta is the single data colour: this histogram is the chart accent.
 */

import type { Metrics } from '../types';

const WIDTH = 620;
const HEIGHT = 240;
const PAD = { top: 16, right: 8, bottom: 44, left: 48 };

export default function ConfidenceChart({ metrics }: { metrics: Metrics }) {
  const data = metrics.confidence_histogram;
  const max = Math.max(1, ...data.map((entry) => entry.count));
  const plotWidth = WIDTH - PAD.left - PAD.right;
  const plotHeight = HEIGHT - PAD.top - PAD.bottom;
  const slot = plotWidth / Math.max(1, data.length);
  const barWidth = slot * 0.7;
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((fraction) => Math.round(max * fraction));

  return (
    <svg
      viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
      className="w-full h-auto"
      role="img"
      aria-label="Confidence score histogram"
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
          <g key={entry.bucket}>
            <rect
              x={x}
              y={PAD.top + plotHeight - height}
              width={barWidth}
              height={height}
              fill="#994422"
            />
            {entry.count > 0 && (
              <text
                x={x + barWidth / 2}
                y={PAD.top + plotHeight - height - 6}
                textAnchor="middle"
                fill="#34332F"
                fontFamily="IBM Plex Mono"
                fontSize={10}
                fontWeight={600}
              >
                {entry.count.toLocaleString()}
              </text>
            )}
            <text
              x={x + barWidth / 2}
              y={HEIGHT - 22}
              textAnchor="end"
              transform={`rotate(-35 ${x + barWidth / 2} ${HEIGHT - 22})`}
              fill="#5f5e5b"
              fontFamily="IBM Plex Mono"
              fontSize={10}
            >
              {entry.bucket}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
