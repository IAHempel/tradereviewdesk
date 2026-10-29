"use client";

import { useState, type PointerEvent } from "react";

const VIEW_WIDTH = 1000;
const VIEW_HEIGHT = 200;

export interface LineSeries {
  key: string;
  label: string;
  color: string;
  values: (number | null)[];
  step?: boolean;
}

export interface ChartMarker {
  x: number;
  y: number;
  color: string;
  label: string;
  hollow?: boolean;
}

function pathFor(values: (number | null)[], x: (index: number) => number, y: (value: number) => number, step: boolean): string {
  let path = "";
  let previous: number | null = null;
  values.forEach((value, index) => {
    if (value === null || Number.isNaN(value)) {
      previous = null;
      return;
    }
    const px = x(index).toFixed(2);
    const py = y(value).toFixed(2);
    if (previous === null) {
      path += `M${px},${py}`;
    } else if (step) {
      path += ` L${px},${y(previous).toFixed(2)} L${px},${py}`;
    } else {
      path += ` L${px},${py}`;
    }
    previous = value;
  });
  return path;
}

/** Thin lines on a recessive grid, one legend, and a crosshair tooltip listing every series at that minute. */
export function LineChart({
  series,
  length,
  yDomain,
  height = 160,
  xLabel,
  format,
  markers = [],
  refLines = [],
  ariaLabel,
  showLegend = true,
}: {
  series: LineSeries[];
  length: number;
  yDomain?: [number, number];
  height?: number;
  xLabel: (index: number) => string;
  format: (value: number) => string;
  markers?: ChartMarker[];
  refLines?: Array<{ y: number; label: string }>;
  ariaLabel: string;
  showLegend?: boolean;
}) {
  const [hover, setHover] = useState<number | null>(null);
  const values = series.flatMap((item) => item.values.filter((value): value is number => value !== null));
  const rawMin = yDomain ? yDomain[0] : Math.min(...values, ...refLines.map((line) => line.y));
  const rawMax = yDomain ? yDomain[1] : Math.max(...values, ...refLines.map((line) => line.y));
  const pad = yDomain ? 0 : (rawMax - rawMin) * 0.1 || Math.abs(rawMax) * 0.01 || 1;
  const yMin = rawMin - pad;
  const yMax = rawMax + pad;
  const last = Math.max(length - 1, 1);
  const x = (index: number) => (index / last) * VIEW_WIDTH;
  const y = (value: number) => VIEW_HEIGHT - ((value - yMin) / (yMax - yMin || 1)) * VIEW_HEIGHT;
  const filled = Math.max(...series.map((item) => item.values.length), 0);

  function handlePointer(event: PointerEvent<HTMLDivElement>) {
    const bounds = event.currentTarget.getBoundingClientRect();
    const index = Math.round(((event.clientX - bounds.left) / bounds.width) * last);
    setHover(index >= 0 && index < filled ? index : null);
  }

  return (
    <div>
      {showLegend && series.length > 1 ? (
        <div className="mb-2 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-slate-400">
          {series.map((item) => (
            <span key={item.key} className="flex items-center gap-1.5">
              <span className="h-0.5 w-4 rounded" style={{ backgroundColor: item.color }} />
              {item.label}
            </span>
          ))}
        </div>
      ) : null}
      <div
        className="relative w-full touch-none select-none"
        style={{ height }}
        onPointerMove={handlePointer}
        onPointerLeave={() => setHover(null)}
        role="img"
        aria-label={ariaLabel}
      >
        <svg viewBox={`0 0 ${VIEW_WIDTH} ${VIEW_HEIGHT}`} preserveAspectRatio="none" className="absolute inset-0 h-full w-full" aria-hidden>
          {refLines.map((line) => (
            <line
              key={line.label}
              x1={0}
              x2={VIEW_WIDTH}
              y1={y(line.y)}
              y2={y(line.y)}
              stroke="rgba(148,163,184,0.28)"
              strokeWidth={1}
              vectorEffect="non-scaling-stroke"
            />
          ))}
          {series.map((item) => (
            <path
              key={item.key}
              d={pathFor(item.values, x, y, Boolean(item.step))}
              fill="none"
              stroke={item.color}
              strokeWidth={2}
              strokeLinejoin="round"
              strokeLinecap="round"
              vectorEffect="non-scaling-stroke"
            />
          ))}
          {hover !== null ? (
            <line x1={x(hover)} x2={x(hover)} y1={0} y2={VIEW_HEIGHT} stroke="rgba(226,232,240,0.45)" strokeWidth={1} vectorEffect="non-scaling-stroke" />
          ) : null}
        </svg>
        {refLines.map((line) => (
          <span
            key={line.label}
            className="pointer-events-none absolute right-1 rounded bg-slate-950/80 px-1 text-[10px] text-slate-400"
            style={{ top: `${(y(line.y) / VIEW_HEIGHT) * 100}%`, transform: "translateY(-50%)" }}
          >
            {line.label}
          </span>
        ))}
        {markers.map((marker, index) => (
          <span
            key={`${marker.x}-${index}`}
            title={marker.label}
            className="absolute h-2.5 w-2.5 -translate-x-1/2 -translate-y-1/2 rounded-full ring-2 ring-slate-950"
            style={{
              left: `${(x(marker.x) / VIEW_WIDTH) * 100}%`,
              top: `${(y(marker.y) / VIEW_HEIGHT) * 100}%`,
              backgroundColor: marker.hollow ? "transparent" : marker.color,
              boxShadow: marker.hollow ? `inset 0 0 0 2px ${marker.color}` : undefined,
            }}
          />
        ))}
        {hover !== null ? (
          <div
            className="pointer-events-none absolute top-1 z-10 min-w-[8rem] rounded-xl border border-white/10 bg-slate-950/95 px-3 py-2 text-xs shadow-lg"
            style={{ left: `${(x(hover) / VIEW_WIDTH) * 100}%`, transform: hover / last > 0.6 ? "translateX(calc(-100% - 8px))" : "translateX(8px)" }}
          >
            <p className="mb-1 text-slate-400">{xLabel(hover)}</p>
            {series.map((item) => {
              const value = item.values[hover];
              return (
                <p key={item.key} className="flex items-center gap-2">
                  <span className="h-0.5 w-3 rounded" style={{ backgroundColor: item.color }} />
                  <span className="font-semibold text-white">{value === null || value === undefined ? "—" : format(value)}</span>
                  <span className="text-slate-400">{item.label}</span>
                </p>
              );
            })}
          </div>
        ) : null}
      </div>
    </div>
  );
}

/** Columns from one baseline, labelled at the tip, for counts by minute of the window. */
export function ColumnChart({ values, labels, ariaLabel }: { values: number[]; labels: string[]; ariaLabel: string }) {
  const max = Math.max(...values, 1);
  return (
    <div className="flex h-32 items-end gap-1" role="img" aria-label={ariaLabel}>
      {values.map((value, index) => (
        <div key={labels[index]} className="flex flex-1 flex-col items-center justify-end gap-1" title={`${labels[index]}: ${value} fills`}>
          <span className="text-[9px] tabular-nums text-slate-400">{value || ""}</span>
          <span className="w-full max-w-[24px] rounded-t bg-[#3987e5]" style={{ height: `${(value / max) * 88}px`, minHeight: value ? 2 : 0 }} />
          <span className="text-[9px] text-slate-500">{labels[index]}</span>
        </div>
      ))}
    </div>
  );
}
