import { useState } from "react";
import { ChartNoAxesCombined, SlidersHorizontal } from "lucide-react";
import type { Annual, Climatology, Monthly } from "../api/schemas";
import type { Resource } from "../api/client";
import { monthLabel, monthName } from "../lib/format";
import { Chart } from "./Chart";
import { ErrorState } from "./States";

function Segmented<T extends string>({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: { value: T; label: string }[];
  value: T;
  onChange: (value: T) => void;
}) {
  return (
    <div className="segmented" role="group" aria-label={label}>
      {options.map((option) => (
        <button
          key={option.value}
          type="button"
          aria-pressed={option.value === value}
          onClick={() => onChange(option.value)}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}

export function RecordExplorer({
  monthly,
  annual,
}: {
  monthly: Resource<Monthly>;
  annual: Resource<Annual>;
}) {
  const [frequency, setFrequency] = useState<"monthly" | "annual">("monthly");
  const [start, setStart] = useState("all");
  const [end, setEnd] = useState("all");
  const years = [
    ...new Set([
      ...(monthly.status === "ready"
        ? monthly.data.observations.map((p) => p.time.slice(0, 4))
        : []),
      ...(annual.status === "ready"
        ? annual.data.observations.map((p) => String(p.year))
        : []),
    ]),
  ].sort();
  const inPeriod = (year: string) =>
    (start === "all" || year >= start) && (end === "all" || year <= end);
  const resource = frequency === "monthly" ? monthly : annual;
  const points =
    frequency === "monthly"
      ? monthly.status === "ready"
        ? monthly.data.observations
            .filter((p) => inPeriod(p.time.slice(0, 4)))
            .map((p) => ({
              label: monthLabel(p.time),
              shortLabel: p.time.slice(0, 4),
              value: p.temperature_celsius,
              reference: p.climatology_celsius,
            }))
        : []
      : annual.status === "ready"
        ? annual.data.observations
            .filter((p) => inPeriod(String(p.year)))
            .map((p) => ({
              label: String(p.year),
              shortLabel: String(p.year),
              value: p.mean_celsius,
            }))
        : [];
  return (
    <section
      className="panel record-panel"
      id="record"
      aria-labelledby="record-title"
    >
      <div className="panel-heading">
        <div>
          <p className="eyebrow">
            <ChartNoAxesCombined size={15} /> Temperature record
          </p>
          <h2 id="record-title">The long view</h2>
          <p className="muted">
            Explore the historical 2-meter air temperature record.
          </p>
        </div>
        <Segmented
          label="Temperature frequency"
          value={frequency}
          onChange={setFrequency}
          options={[
            { value: "monthly", label: "Monthly" },
            { value: "annual", label: "Annual" },
          ]}
        />
      </div>
      <div className="chart-toolbar">
        <div className="legend">
          <span>
            <i className="swatch temperature" />
            {frequency === "monthly" ? "Monthly temperature" : "Annual mean"}
          </span>
          {frequency === "monthly" && (
            <span>
              <i className="swatch baseline" />
              Full-record climatology
            </span>
          )}
        </div>
        <div className="period-filter">
          <SlidersHorizontal size={14} aria-hidden="true" />
          <label>
            From{" "}
            <select
              aria-label="Chart start year"
              value={start}
              onChange={(event) => {
                setStart(event.target.value);
                if (
                  end !== "all" &&
                  event.target.value !== "all" &&
                  event.target.value > end
                )
                  setEnd(event.target.value);
              }}
            >
              <option value="all">First year</option>
              {years.map((year) => (
                <option key={year}>{year}</option>
              ))}
            </select>
          </label>
          <label>
            To{" "}
            <select
              aria-label="Chart end year"
              value={end}
              onChange={(event) => {
                setEnd(event.target.value);
                if (
                  start !== "all" &&
                  event.target.value !== "all" &&
                  event.target.value < start
                )
                  setStart(event.target.value);
              }}
            >
              <option value="all">Last year</option>
              {years.map((year) => (
                <option key={year}>{year}</option>
              ))}
            </select>
          </label>
        </div>
      </div>
      {resource.status === "error" ? (
        <ErrorState
          error={resource.error}
          title={`${frequency === "monthly" ? "Monthly" : "Annual"} record unavailable`}
        />
      ) : (
        <Chart
          key={`${frequency}-${start}-${end}`}
          title={
            frequency === "monthly"
              ? "Monthly air temperature"
              : "Annual air temperature"
          }
          description={
            frequency === "monthly"
              ? "Monthly air temperature and the backend full-record month-of-year climatology."
              : "Annual air temperature means returned by the backend."
          }
          points={points}
          referenceLabel={frequency === "monthly" ? "Climatology" : undefined}
        />
      )}
      <p className="panel-note">
        {frequency === "annual" && annual.status === "ready"
          ? `${annual.data.method}. `
          : ""}
        Chart filters change this view only. The trend and climatology baseline
        use the full validated record.
      </p>
    </section>
  );
}

export function SeasonalContext({
  monthly,
  climatology,
}: {
  monthly: Resource<Monthly>;
  climatology: Resource<Climatology>;
}) {
  const [view, setView] = useState<"anomalies" | "climatology">("anomalies");
  const resource = view === "anomalies" ? monthly : climatology;
  const points =
    view === "anomalies"
      ? monthly.status === "ready"
        ? monthly.data.observations.map((p) => ({
            label: monthLabel(p.time),
            shortLabel: p.time.slice(0, 4),
            value: p.anomaly_celsius,
          }))
        : []
      : climatology.status === "ready"
        ? climatology.data.observations.map((p) => ({
            label: `${monthName(p.month)} · ${p.observations} observations`,
            shortLabel: monthName(p.month),
            value: p.mean_celsius,
          }))
        : [];
  const baseline =
    resource.status === "ready"
      ? `${monthLabel(resource.data.baseline_start)} – ${monthLabel(resource.data.baseline_end)}`
      : "full validated record";
  return (
    <section className="panel" aria-labelledby="seasonal-title">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Seasonal context</p>
          <h2 id="seasonal-title">
            {view === "anomalies"
              ? "Beyond the seasonal cycle"
              : "A typical seasonal cycle"}
          </h2>
        </div>
        <Segmented
          label="Seasonal context view"
          value={view}
          onChange={setView}
          options={[
            { value: "anomalies", label: "Anomalies" },
            { value: "climatology", label: "Climatology" },
          ]}
        />
      </div>
      <p className="context-description">
        {view === "anomalies"
          ? "Each month’s departure from its calendar-month climatology. Positive values are warmer than that baseline; negative values are cooler."
          : climatology.status === "ready"
            ? climatology.data.method
            : "Calendar-month means over the full record."}
      </p>
      <div className="legend seasonal-legend">
        {view === "anomalies" ? (
          <>
            <span>
              <i className="swatch temperature" />
              Above baseline (+)
            </span>
            <span>
              <i className="swatch cool" />
              Below baseline (−)
            </span>
          </>
        ) : (
          <span>
            <i className="swatch temperature" />
            Calendar-month mean
          </span>
        )}
        <span className="baseline-caption">Baseline: {baseline}</span>
      </div>
      {resource.status === "error" ? (
        <ErrorState error={resource.error} />
      ) : (
        <Chart
          key={view}
          title={
            view === "anomalies"
              ? "Monthly temperature anomalies"
              : "Monthly climatology"
          }
          description={
            view === "anomalies"
              ? "Monthly air temperature anomalies returned by the backend, relative to the full-record calendar-month climatology."
              : "Twelve calendar-month climatology means returned by the backend."
          }
          points={points}
          bars={view === "anomalies"}
        />
      )}
      <p className="panel-note">
        The full-record climatology is descriptive; it is not a standard 30-year
        climate normal. Values and anomalies are calculated by the scientific
        backend.
      </p>
    </section>
  );
}
