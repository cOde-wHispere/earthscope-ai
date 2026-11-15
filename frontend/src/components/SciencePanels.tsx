import { ArrowUpRight, CircleCheck, Info, ShieldCheck } from "lucide-react";
import type { DashboardData, Resource } from "../api/client";
import type { Trend } from "../api/schemas";
import type { VariableDashboard } from "../api/variables";
import { displayUnits } from "../api/variableSchemas";
import { monthLabel, number, pValue, signed } from "../lib/format";
import { ErrorState } from "./States";

export function TrendPanel({ resource }: { resource: Resource<Trend> }) {
  if (resource.status === "error")
    return (
      <section className="panel" aria-labelledby="trend-title">
        <h2 id="trend-title">Full-record trend</h2>
        <ErrorState error={resource.error} title="Trend analysis unavailable" />
      </section>
    );
  const { observations: stats, interpretation } = resource.data;
  const ci = stats.confidence_interval_celsius_per_decade;
  return (
    <section className="trend-section" aria-labelledby="trend-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Scientific summary</p>
          <h2 id="trend-title">Full-record trend</h2>
        </div>
        <span className="subtle-tag">
          {monthLabel(stats.start)} – {monthLabel(stats.end)}
        </span>
      </div>
      <div className="stats-grid">
        <div className="stat-card">
          <span className="stat-label">Seasonality-adjusted trend</span>
          <strong>
            {signed(stats.slope_celsius_per_decade)} <small>°C / decade</small>
          </strong>
          <span className="stat-foot">
            {stats.n_observations} monthly observations
          </span>
        </div>
        <div className="stat-card">
          <span className="stat-label">
            {number(ci.level * 100, 0)}% confidence interval
          </span>
          <strong className="interval-value">
            {signed(ci.lower)} to {signed(ci.upper)}
          </strong>
          <span className="stat-foot">
            °C / decade · {stats.covariance} uncertainty
          </span>
        </div>
        <div className="stat-card">
          <span className="stat-label">Two-sided p-value</span>
          <strong>{pValue(stats.p_value)}</strong>
          <span className="stat-foot">
            Significance threshold α = {interpretation.significance_level}
          </span>
        </div>
      </div>
      <div className="interpretation">
        <Info size={21} aria-hidden="true" />
        <div>
          <p className="interpretation-label">Statistical interpretation</p>
          <p className="conclusion">{interpretation.conclusion}.</p>
          <p>
            {interpretation.causation} A p-value is not the probability that the
            trend is real. A nonsignificant result does not demonstrate a zero
            trend.
          </p>
        </div>
      </div>
    </section>
  );
}

export function ProvenancePanel({ data }: { data: VariableDashboard }) {
  const resource = data.metadata;
  return (
    <section
      className="panel provenance-panel"
      id="provenance"
      aria-labelledby="provenance-title"
    >
      <div className="panel-heading">
        <div>
          <p className="eyebrow">
            <ShieldCheck size={15} /> Source & provenance
          </p>
          <h2 id="provenance-title">Trace every observation</h2>
        </div>
        {resource.status === "ready" && (
          <a
            className="text-link"
            href={`https://disc.gsfc.nasa.gov/datasets/${resource.data.identity.collection}_5.12.4/summary`}
            target="_blank"
            rel="noreferrer"
          >
            NASA product <ArrowUpRight size={15} />
            <span className="sr-only"> (opens in a new tab)</span>
          </a>
        )}
      </div>
      {resource.status === "error" ? (
        <ErrorState
          error={resource.error}
          title="Source metadata unavailable"
        />
      ) : (
        <>
          <div className="source-banner">
            <div className="source-monogram">NASA</div>
            <div>
              <strong>NASA GES DISC / Giovanni</strong>
              <p>
                {resource.data.identity.collection} v
                {resource.data.identity.version} · Historical local export
              </p>
            </div>
            <span className="badge">
              <CircleCheck size={13} /> Source validated
            </span>
          </div>
          <dl className="metadata-grid">
            <div>
              <dt>Variable</dt>
              <dd>
                {resource.data.variable} ({resource.data.label})
              </dd>
            </div>
            <div>
              <dt>Geographic support</dt>
              <dd>{resource.data.identity.region}</dd>
            </div>
            <div>
              <dt>Validated coverage</dt>
              <dd>
                {monthLabel(resource.data.validation.expected_start)} –{" "}
                {monthLabel(resource.data.validation.expected_end)}
              </dd>
            </div>
            <div>
              <dt>Completeness</dt>
              <dd>
                {resource.data.validation.valid_observations} /{" "}
                {resource.data.validation.expected_observations} valid months ·{" "}
                {resource.data.validation.interpolated_observations}{" "}
                interpolated
              </dd>
            </div>
            <div>
              <dt>Units & conversion</dt>
              <dd>
                Exported {resource.data.exported_units} →{" "}
                {displayUnits(resource.data.monthly_units)} ·{" "}
                {resource.data.conversion}
              </dd>
            </div>
            <div>
              <dt>Retrieval date</dt>
              <dd>Unknown in this export</dd>
            </div>
          </dl>
          <p className="panel-note">
            Annual aggregation: {resource.data.annual_method} (
            {displayUnits(resource.data.annual_units)}).
          </p>
          <div className="hash-block">
            <span>Dataset ID</span>
            <code>{resource.data.dataset_id}</code>
            <span>Source SHA-256</span>
            <code>{resource.data.source_sha256}</code>
            <p>
              A checksum identifies the file bytes; it does not independently
              establish scientific authenticity.
            </p>
          </div>
          {resource.data.validation.warnings.length > 0 && (
            <div className="validation-warnings">
              <h3>Validation warnings</h3>
              <ul>
                {resource.data.validation.warnings.map((warning) => (
                  <li key={warning}>{warning}</li>
                ))}
              </ul>
            </div>
          )}
          <details className="source-details">
            <summary>Inspect source metadata & validation</summary>
            <dl className="raw-metadata">
              <dt>Source file</dt>
              <dd>{resource.data.source_name}</dd>
              <dt>Units basis</dt>
              <dd>{resource.data.units_basis}</dd>
              <dt>NASA product native units</dt>
              <dd>{resource.data.product_native_units}</dd>
              <dt>Validation screen</dt>
              <dd>{resource.data.validation_screen}</dd>
              <dt>Value column</dt>
              <dd>{resource.data.value_column}</dd>
              <dt>Fill value (rejected)</dt>
              <dd>{resource.data.fill_value}</dd>
              <dt>Input ordering</dt>
              <dd>
                {resource.data.validation.input_was_sorted
                  ? "Already sorted"
                  : "Sorted by the backend"}
              </dd>
              {resource.data.source_metadata.map((entry, index) => (
                <div key={`${entry.key}-${index}`}>
                  <dt>{entry.key}</dt>
                  <dd>{entry.value}</dd>
                </div>
              ))}
            </dl>
            <pre>{resource.data.raw_preamble}</pre>
            <pre>{JSON.stringify(resource.data.identity, null, 2)}</pre>
            <pre>{JSON.stringify(resource.data.validation, null, 2)}</pre>
          </details>
          <details className="source-details">
            <summary>Source limitations</summary>
            <ul>
              {resource.data.limitations.map((text) => (
                <li key={text}>{text}</li>
              ))}
            </ul>
          </details>
        </>
      )}
    </section>
  );
}

export function DescriptiveMethodology({ data }: { data: VariableDashboard }) {
  return (
    <section
      className="panel methodology-panel"
      id="methodology"
      aria-labelledby="methods-title"
    >
      <p className="eyebrow">Read the evidence responsibly</p>
      <h2 id="methods-title">Methodology & limitations</h2>
      <div className="method-grid">
        <div>
          <h3>From export to evidence</h3>
          <p>
            The backend verifies the approved file identity, SHA-256, country
            shape, coverage, duplicates, gaps, fill values and finite values.
            Invalid records block output; no interpolation is used.
          </p>
          {data.metadata.status === "ready" && (
            <>
              <h3>Units & annual aggregation</h3>
              <p>{data.metadata.data.units_basis}</p>
              <p>{data.metadata.data.conversion}</p>
              <p>
                {data.metadata.data.annual_method} (
                {displayUnits(data.metadata.data.annual_units)}). Every annual
                value requires 12 complete months.
              </p>
            </>
          )}
          <p>
            This view provides descriptive monthly values and annual aggregates.
            Additional statistical analysis requires separate scientific
            approval.
          </p>
        </div>
        <div className="limits-column">
          <h3>What this record can tell us</h3>
          <p>
            MERRA-2 combines a physical model and assimilated observations.
            Monthly country averages can obscure local conditions, particularly
            for a country narrow relative to the native grid.
          </p>
          {data.metadata.status === "ready" && (
            <ul>
              {data.metadata.data.limitations.map((text) => (
                <li key={text}>{text}</li>
              ))}
            </ul>
          )}
          <p>
            Historical context does not establish causation or forecast future
            conditions. Operational aviation, marine and safety decisions
            require certified services.
          </p>
        </div>
      </div>
    </section>
  );
}

export function Methodology({ data }: { data: DashboardData }) {
  const trend = data.trend.status === "ready" ? data.trend.data : null;
  return (
    <section
      className="panel methodology-panel"
      id="methodology"
      aria-labelledby="methods-title"
    >
      <p className="eyebrow">Read the evidence responsibly</p>
      <h2 id="methods-title">Methodology & limitations</h2>
      <div className="method-grid">
        <div>
          <h3>From export to evidence</h3>
          <ol className="method-steps">
            <li>
              <strong>Validate the source</strong>
              <p>
                The backend checks the approved file identity, country shape,
                coverage, duplicates, gaps, fill values and finite values.
                Invalid records block output; no interpolation is used.
              </p>
            </li>
            <li>
              <strong>Describe the record</strong>
              <p>
                Kelvin is converted to Celsius. Annual means give equal weight
                to all 12 monthly means. Climatology uses calendar-month means
                across the full validated record.
              </p>
            </li>
            <li>
              <strong>Estimate association & uncertainty</strong>
              <p>
                OLS fits a time slope jointly with fixed month-of-year effects.
                The backend provides the slope, confidence interval, p-value and
                interpretation.
              </p>
            </li>
          </ol>
        </div>
        <div className="limits-column">
          <h3>What this record can tell us</h3>
          <p>
            MERRA-2 combines a physical model and assimilated observations.
            Country averages can obscure local conditions, particularly for a
            country narrow relative to the native grid.
          </p>
          <p>
            The record describes historical air temperature. It does not
            establish attribution, forecast future conditions, measure sea
            temperature or provide operational safety advice.
          </p>
          <p>
            Confidence intervals cover regression sampling uncertainty under
            model assumptions, excluding source, structural and spatial
            aggregation uncertainty.
          </p>
        </div>
      </div>
      {trend && (
        <>
          <details className="source-details">
            <summary>Inspect the backend statistical specification</summary>
            <dl className="raw-metadata">
              <dt>Model</dt>
              <dd>{trend.observations.method}</dd>
              <dt>Seasonality</dt>
              <dd>{trend.observations.seasonality}</dd>
              <dt>Covariance</dt>
              <dd>
                {trend.observations.covariance} · {trend.observations.kernel}{" "}
                kernel · {trend.observations.hac_maxlags_months} monthly lags
              </dd>
              <dt>Small-sample correction</dt>
              <dd>
                {trend.observations.small_sample_correction
                  ? "Applied"
                  : "Not applied"}
              </dd>
              <dt>Inference</dt>
              <dd>{trend.observations.inference}</dd>
              <dt>Residual degrees of freedom</dt>
              <dd>{trend.observations.residual_degrees_of_freedom}</dd>
              <dt>Standard error (°C / decade)</dt>
              <dd>
                {number(
                  trend.observations.standard_error_celsius_per_decade,
                  6,
                )}
              </dd>
            </dl>
          </details>
          <details className="source-details">
            <summary>Backend assumptions & limitations</summary>
            <h3>Assumptions</h3>
            <ul>
              {trend.assumptions.map((text) => (
                <li key={text}>{text}</li>
              ))}
            </ul>
            <h3>Limitations</h3>
            <ul>
              {trend.limitations.map((text) => (
                <li key={text}>{text}</li>
              ))}
            </ul>
          </details>
        </>
      )}
    </section>
  );
}
