import { useState } from "react";
import { ChartNoAxesCombined, SlidersHorizontal } from "lucide-react";
import type { Climatology, Monthly } from "../api/schemas";
import type { Resource } from "../api/client";
import type { VariableDashboard } from "../api/variables";
import { displayUnits } from "../api/variableSchemas";
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

export function RecordExplorer({ data }: { data: VariableDashboard }) {
  const { monthly, annual, item, temperature } = data;
  const isTemperature = item.id === "T2M";
  const references = new Map(
    temperature?.monthly.status === "ready"
      ? temperature.monthly.data.observations.map((point) => [
          point.time,
          point.climatology_celsius,
        ])
      : [],
  );
  const hasReference =
    isTemperature &&
    monthly.status === "ready" &&
    monthly.data.observations.length > 0 &&
    monthly.data.observations.every((point) => references.has(point.time));
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
              value: p.value,
              reference: hasReference ? references.get(p.time) : undefined,
            }))
        : []
      : annual.status === "ready"
        ? annual.data.observations
            .filter((p) => inPeriod(String(p.year)))
            .map((p) => ({
              label: String(p.year),
              shortLabel: String(p.year),
              value: p.value,
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
            <ChartNoAxesCombined size={15} /> {item.id} record
          </p>
          <h2 id="record-title">The long view</h2>
          <p className="muted">
            Explore the historical {item.label.toLowerCase()} record.
          </p>
        </div>
        <Segmented
          label="Record frequency"
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
            {frequency === "monthly"
              ? item.label
              : item.id === "PRECTOTCORR"
                ? "Annual total"
                : "Annual mean"}
          </span>
          {frequency === "monthly" && hasReference && (
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
              ? isTemperature
                ? "Monthly air temperature"
                : `Monthly ${item.label.toLowerCase()}`
              : isTemperature
                ? "Annual air temperature"
                : `Annual ${item.label.toLowerCase()}`
          }
          description={
            frequency === "monthly"
              ? `Monthly ${item.label.toLowerCase()} returned by the backend.${hasReference ? " Includes the approved full-record month-of-year climatology." : ""}`
              : `Annual ${item.label.toLowerCase()} returned by the backend.`
          }
          points={points}
          referenceLabel={
            frequency === "monthly" && hasReference ? "Climatology" : undefined
          }
          unit={displayUnits(
            frequency === "monthly" ? item.monthly_units : item.annual_units,
          )}
          valueLabel={isTemperature ? "Temperature" : item.label}
          signedValues={item.id === "U10M" || item.id === "V10M"}
        />
      )}
      <p className="panel-note">
        {frequency === "annual" && annual.status === "ready"
          ? `${annual.data.method}. `
          : ""}
        Chart filters change this view only.{" "}
        {isTemperature
          ? "The trend and climatology baseline use the full validated record."
          : "Values and complete-year aggregates are supplied by the scientific backend."}
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
