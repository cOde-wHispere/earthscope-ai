import { useId, useState } from "react";
import { number } from "../lib/format";
import { EmptyState } from "./States";

export interface ChartPoint {
  label: string;
  shortLabel: string;
  value: number;
  reference?: number;
}

// Only maps supplied values to display coordinates. No scientific statistics,
// aggregation, anomaly calculations, regression or fitted line is computed here.
export function Chart({
  points,
  title,
  description,
  referenceLabel,
  bars = false,
}: {
  points: ChartPoint[];
  title: string;
  description: string;
  referenceLabel?: string;
  bars?: boolean;
}) {
  const id = useId();
  const [selected, setSelected] = useState<number | null>(null);
  if (!points.length) return <EmptyState label={title.toLowerCase()} />;
  const index = Math.min(selected ?? points.length - 1, points.length - 1);
  const point = points[index];
  const values = points.flatMap((p) =>
    p.reference === undefined ? [p.value] : [p.value, p.reference],
  );
  const min = Math.min(...values, ...(bars ? [0] : []));
  const max = Math.max(...values, ...(bars ? [0] : []));
  const pad = (max - min || 1) * 0.15;
  const low = min - pad;
  const high = max + pad;
  const left = 58,
    right = 864,
    top = 18,
    bottom = 224;
  const x = (i: number) =>
    left + (i * (right - left)) / Math.max(points.length - 1, 1);
  const y = (value: number) =>
    bottom - ((value - low) / (high - low)) * (bottom - top);
  const path = (reference = false) =>
    points
      .map(
        (p, i) =>
          `${i ? "L" : "M"}${x(i)},${y(reference ? (p.reference ?? p.value) : p.value)}`,
      )
      .join(" ");
  const ticks = Array.from(
    { length: 5 },
    (_, i) => low + (i * (high - low)) / 4,
  );
  const tickIndices = [
    ...new Set([
      0,
      Math.floor((points.length - 1) / 3),
      Math.floor((2 * (points.length - 1)) / 3),
      points.length - 1,
    ]),
  ];
  return (
    <div className="chart">
      <div className="chart-readout" aria-live="polite">
        <span>{point.label}</span>
        <strong>
          {number(point.value)} <small>°C</small>
        </strong>
        {referenceLabel && point.reference !== undefined && (
          <span>
            {referenceLabel}: {number(point.reference)} °C
          </span>
        )}
      </div>
      <div
        className="chart-plot"
        role="region"
        aria-label={`${title} plot; scroll horizontally on small screens`}
        tabIndex={0}
      >
        <svg
          viewBox="0 0 900 262"
          role="img"
          aria-labelledby={`${id}-title ${id}-desc`}
          onPointerMove={(event) => {
            const rect = event.currentTarget.getBoundingClientRect();
            const position = ((event.clientX - rect.left) / rect.width) * 900;
            setSelected(
              Math.max(
                0,
                Math.min(
                  points.length - 1,
                  Math.round(
                    ((position - left) / (right - left)) * (points.length - 1),
                  ),
                ),
              ),
            );
          }}
        >
          <title id={`${id}-title`}>{title}</title>
          <desc id={`${id}-desc`}>
            {description} Use the observation slider or open the data table for
            values displayed to four decimal places.
          </desc>
          {ticks.map((tick) => (
            <g key={tick}>
              <line
                className="grid-line"
                x1={left}
                x2={right}
                y1={y(tick)}
                y2={y(tick)}
              />
              <text
                className="axis-label"
                x={left - 12}
                y={y(tick) + 4}
                textAnchor="end"
              >
                {number(tick, 1)}
              </text>
            </g>
          ))}
          <text className="axis-label" x="14" y="13">
            °C
          </text>
          {bars && (
            <line
              className="zero-line"
              x1={left}
              x2={right}
              y1={y(0)}
              y2={y(0)}
            />
          )}
          {referenceLabel && <path className="reference-line" d={path(true)} />}
          {bars ? (
            points.map((p, i) => (
              <line
                key={`${p.label}-${i}`}
                className={p.value >= 0 ? "positive-bar" : "negative-bar"}
                x1={x(i)}
                x2={x(i)}
                y1={y(0)}
                y2={y(p.value)}
                strokeWidth={Math.max(1, Math.min(20, 600 / points.length))}
              />
            ))
          ) : (
            <path className="data-line" d={path()} />
          )}
          <line
            className="cursor-line"
            x1={x(index)}
            x2={x(index)}
            y1={top}
            y2={bottom}
          />
          <circle
            className="data-dot"
            cx={x(index)}
            cy={y(point.value)}
            r="4.5"
          />
          {tickIndices.map((i) => (
            <text
              className="axis-label"
              key={i}
              x={x(i)}
              y="250"
              textAnchor={
                i === 0 ? "start" : i === points.length - 1 ? "end" : "middle"
              }
            >
              {points[i].shortLabel}
            </text>
          ))}
        </svg>
      </div>
      <label className="observation-control">
        <span>
          Explore observations{" "}
          <span className="muted">· drag or use arrow keys</span>
        </span>
        <input
          aria-label={`${title}: observation`}
          type="range"
          min={0}
          max={points.length - 1}
          value={index}
          onChange={(event) => setSelected(Number(event.target.value))}
          aria-valuetext={`${point.label}, ${number(point.value)} degrees Celsius`}
        />
      </label>
      <details className="data-details">
        <summary>
          View data table <span>({points.length} observations)</span>
        </summary>
        <div
          className="table-scroll"
          role="region"
          aria-label={`${title} data table`}
          tabIndex={0}
        >
          <table>
            <caption>
              {title} — backend values displayed to four decimal places
            </caption>
            <thead>
              <tr>
                <th scope="col">Period</th>
                <th scope="col">
                  {bars ? "Anomaly (°C)" : "Temperature (°C)"}
                </th>
                {referenceLabel && <th scope="col">{referenceLabel} (°C)</th>}
              </tr>
            </thead>
            <tbody>
              {points.map((p, i) => (
                <tr key={`${p.label}-${i}`}>
                  <th scope="row">{p.label}</th>
                  <td>{number(p.value, 4)}</td>
                  {referenceLabel && (
                    <td>
                      {p.reference === undefined ? "—" : number(p.reference, 4)}
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </div>
  );
}
