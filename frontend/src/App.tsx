import { useEffect, useRef, useState } from "react";
import {
  ArrowDown,
  ArrowUpRight,
  ChartNoAxesCombined,
  ChevronRight,
  Compass,
  Database,
  FlaskConical,
  Globe2,
  Layers3,
  Leaf,
  MapPin,
  RefreshCw,
  ShieldCheck,
} from "lucide-react";
import { ApiError } from "./api/client";
import { loadCatalog, loadVariableDashboard } from "./api/variables";
import type { VariableDashboard } from "./api/variables";
import { variables } from "./api/variableSchemas";
import type { Catalog, Variable } from "./api/variableSchemas";
import { Applications } from "./components/Applications";
import { RecordExplorer, SeasonalContext } from "./components/RecordExplorer";
import {
  Methodology,
  DescriptiveMethodology,
  ProvenancePanel,
  TrendPanel,
} from "./components/SciencePanels";
import { ErrorState, LoadingState } from "./components/States";
import { monthLabel } from "./lib/format";

type State =
  | { status: "loading" }
  | { status: "ready"; data: VariableDashboard }
  | { status: "error"; error: ApiError };
const nav = [
  { href: "#overview", icon: Compass, label: "Overview" },
  { href: "#record", icon: ChartNoAxesCombined, label: "Environmental record" },
  { href: "#provenance", icon: Database, label: "Source & provenance" },
  { href: "#methodology", icon: FlaskConical, label: "Methodology" },
  { href: "#applications", icon: Layers3, label: "Applications" },
];

export default function App() {
  const [state, setState] = useState<State>({ status: "loading" });
  const [reload, setReload] = useState(0);
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [selected, setSelected] = useState<Variable>("T2M");
  const [active, setActive] = useState(window.location.hash || "#overview");
  const controllerRef = useRef<AbortController | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    loadCatalog(controller.signal)
      .then((value) => {
        if (!controller.signal.aborted) setCatalog(value);
      })
      .catch((error: unknown) => {
        if (!controller.signal.aborted)
          setState({
            status: "error",
            error:
              error instanceof ApiError
                ? error
                : new ApiError(
                    "load_failed",
                    "Dataset availability could not be loaded.",
                  ),
          });
      });
    return () => controller.abort();
  }, [reload]);
  useEffect(() => {
    if (!catalog) return;
    const controller = new AbortController();
    controllerRef.current = controller;
    const item = catalog.datasets.find((entry) => entry.id === selected)!;
    loadVariableDashboard(item, controller.signal)
      .then((data) => {
        if (!controller.signal.aborted) setState({ status: "ready", data });
      })
      .catch((error: unknown) => {
        if (!controller.signal.aborted)
          setState({
            status: "error",
            error:
              error instanceof ApiError
                ? error
                : new ApiError(
                    "load_failed",
                    "The scientific record could not be loaded.",
                  ),
          });
      });
    return () => controller.abort();
  }, [catalog, selected]);
  useEffect(() => {
    const sync = () => setActive(window.location.hash || "#overview");
    window.addEventListener("hashchange", sync);
    return () => window.removeEventListener("hashchange", sync);
  }, []);
  const retry = () => {
    controllerRef.current?.abort();
    setCatalog(null);
    setState({ status: "loading" });
    setReload((value) => value + 1);
  };
  const data =
    state.status === "ready" && state.data.item.id === selected
      ? state.data
      : null;
  const temperature = data?.temperature;
  const selectedItem = catalog?.datasets.find((item) => item.id === selected);
  const metadata =
    data?.metadata.status === "ready" ? data.metadata.data : null;
  const sourceHealthy = metadata !== null && selectedItem?.status === "ready";
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main">
        Skip to main content
      </a>
      <aside className="sidebar">
        <a className="brand" href="#overview">
          <span className="brand-icon">
            <Globe2 size={26} />
          </span>
          <span>
            EarthScope <b>AI</b>
            <small>EARTH INTELLIGENCE</small>
          </span>
        </a>
        <div className="workspace-label">
          WORKSPACE <span>MVP</span>
        </div>
        <nav aria-label="Main navigation">
          {nav.map(({ href, icon: Icon, label }) => (
            <a
              key={href}
              href={href}
              onClick={() => setActive(href)}
              aria-current={active === href ? "location" : undefined}
            >
              <Icon size={18} aria-hidden="true" />
              {label}
              {active === href && <span className="nav-dot" />}
            </a>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="scope-card">
            <Leaf size={20} />
            <strong>Built on evidence.</strong>
            <p>
              Transparent sources.
              <br />
              Shared understanding.
            </p>
            <a href="#methodology">
              Our scientific approach <ArrowUpRight size={14} />
            </a>
          </div>
          <div className="team-mark">
            <span>CO₂</span>
            <div>
              Team CO2<small>NASA Space Apps Challenge 2026</small>
            </div>
          </div>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <div className="breadcrumb">
            Workspace <ChevronRight size={14} />
            <strong>Environmental trends</strong>
          </div>
          <span className="snapshot-tag">
            <Database size={13} /> Historical snapshot
          </span>
        </header>
        <main id="main">
          <section id="overview" className="overview">
            <div className="page-heading">
              <div>
                <p className="eyebrow">
                  Observe. Understand. Put change in context.
                </p>
                <h1>Environmental intelligence</h1>
                <p className="page-intro">
                  A shared view of Earth’s changing environment, grounded in
                  transparent science.
                </p>
              </div>
              <button
                className="refresh-button"
                onClick={retry}
                disabled={state.status === "loading"}
              >
                <RefreshCw
                  size={16}
                  className={state.status === "loading" ? "spin" : undefined}
                />
                {state.status === "loading" ? "Loading" : "Reload data"}
              </button>
            </div>
            <div className="dataset-selector">
              <label htmlFor="dataset">NASA Giovanni dataset</label>
              <select
                id="dataset"
                value={selected}
                disabled={!catalog}
                aria-describedby="dataset-availability"
                onChange={(event) => {
                  const next = event.target.value as Variable;
                  if (next === selected) return;
                  controllerRef.current?.abort();
                  setState({ status: "loading" });
                  setSelected(next);
                }}
              >
                {variables.map((id) => {
                  const item = catalog?.datasets.find(
                    (entry) => entry.id === id,
                  );
                  return (
                    <option
                      key={id}
                      value={id}
                      disabled={!item || item.status !== "ready"}
                    >
                      {id}
                      {item
                        ? ` · ${item.label}${item.status === "ready" ? "" : ` (${item.status})`}`
                        : " · checking availability"}
                    </option>
                  );
                })}
              </select>
              <p id="dataset-availability" className="muted" role="status">
                {catalog
                  ? `${catalog.datasets.filter((item) => item.status === "ready").length} of 6 datasets available. Selected: ${selected}.`
                  : "Checking dataset availability with the scientific service."}
              </p>
              {catalog?.datasets.some((item) => item.status !== "ready") && (
                <ul className="availability-notes">
                  {catalog.datasets
                    .filter((item) => item.status !== "ready")
                    .map((item) => (
                      <li key={item.id}>
                        <strong>
                          {item.id}: {item.status}.
                        </strong>{" "}
                        {item.error?.message ||
                          "Approved source unavailable. Restore the backend source and reload."}
                      </li>
                    ))}
                </ul>
              )}
            </div>
            <div className="study-card">
              <div className="study-content">
                <span className="study-label">
                  <MapPin size={14} /> CURRENT STUDY AREA
                </span>
                <h2>
                  The Gambia<span>West Africa</span>
                </h2>
                <p>
                  Country-shape area average · {selectedItem?.label || selected}
                </p>
                <div className="study-tags">
                  <span>MERRA-2 reanalysis</span>
                  <span>
                    {metadata
                      ? `${monthLabel(metadata.validation.expected_start)} – ${monthLabel(metadata.validation.expected_end)}`
                      : "Historical baseline"}
                  </span>
                  <span>Monthly observations</span>
                </div>
                <a href="#record">
                  Explore the record <ArrowDown size={15} />
                </a>
              </div>
              <div className="study-art" aria-hidden="true">
                <svg viewBox="0 0 400 260">
                  <g fill="none" stroke="currentColor" strokeWidth="1">
                    <ellipse cx="240" cy="130" rx="136" ry="136" />
                    <ellipse cx="240" cy="130" rx="90" ry="136" />
                    <ellipse cx="240" cy="130" rx="35" ry="136" />
                    <ellipse cx="240" cy="130" rx="136" ry="90" />
                    <ellipse cx="240" cy="130" rx="136" ry="35" />
                    <path d="M104 130h272M240-6v272" />
                  </g>
                  <circle
                    cx="195"
                    cy="137"
                    r="30"
                    fill="#c7edb6"
                    fillOpacity=".08"
                  />
                  <circle cx="195" cy="137" r="6" fill="#c7edb6" />
                  <circle
                    cx="195"
                    cy="137"
                    r="13"
                    fill="none"
                    stroke="#c7edb6"
                  />
                  <path d="M209 137h65" stroke="#c7edb6" />
                  <text x="281" y="141" fill="#dff3d2" fontSize="12">
                    THE GAMBIA
                  </text>
                </svg>
                <span>EARTH SYSTEMS / {selected}</span>
              </div>
            </div>
            <div className="dataset-strip">
              <span>
                <i className={`status-dot ${sourceHealthy ? "ready" : ""}`} />
                <strong>
                  {state.status === "loading"
                    ? "Connecting to scientific service"
                    : sourceHealthy
                      ? "Validated source connected"
                      : metadata
                        ? "Source connected · check service status"
                        : "Source not verified"}
                </strong>
              </span>
              <span>
                <ShieldCheck size={14} /> Read-only scientific results
              </span>
              <span>Scope: The Gambia · {selected}</span>
            </div>
          </section>
          {state.status === "loading" && <LoadingState />}
          {state.status === "error" && (
            <ErrorState
              error={state.error}
              title={
                !catalog
                  ? "Dataset availability unavailable"
                  : "Dataset unavailable"
              }
            />
          )}
          {data && (
            <>
              {temperature &&
                (temperature.health.status === "error" ? (
                  <div className="service-warning">
                    <ErrorState
                      error={temperature.health.error}
                      title="Service health could not be checked"
                    />
                  </div>
                ) : (
                  temperature.health.data.status === "degraded" && (
                    <div className="service-warning" role="status">
                      <strong>
                        Scientific service:{" "}
                        {temperature.health.data.dataset_status.replaceAll(
                          "_",
                          " ",
                        )}
                      </strong>
                      <p>
                        {temperature.health.data.error?.message ||
                          "Some scientific outputs are unavailable."}{" "}
                        Available, source-matched results remain visible below.
                      </p>
                    </div>
                  )
                ))}
              {temperature && <TrendPanel resource={temperature.trend} />}
              <RecordExplorer key={selected} data={data} />
              {temperature && (
                <SeasonalContext
                  monthly={temperature.monthly}
                  climatology={temperature.climatology}
                />
              )}
              <ProvenancePanel data={data} />
              {temperature ? (
                <Methodology data={temperature} />
              ) : (
                <DescriptiveMethodology data={data} />
              )}
            </>
          )}
          {!data && (
            <section className="panel standalone-method" id="methodology">
              <p className="eyebrow">Scientific scope</p>
              <h2>Evidence before interpretation</h2>
              <p>
                This dashboard supports six verified NASA Giovanni MERRA-2
                exports for The Gambia. Scientific results require a running v2
                FastAPI backend and the selected approved local source file.
              </p>
            </section>
          )}
          <Applications />
          <footer>
            <a className="footer-brand" href="#overview">
              <Globe2 size={18} /> EarthScope AI
            </a>
            <p>Team CO2 · Earth observation for shared understanding.</p>
            <span>Six-variable research dashboard</span>
          </footer>
        </main>
      </div>
    </div>
  );
}
