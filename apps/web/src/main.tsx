import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  BrowserRouter,
  Routes,
  Route,
  Link,
  useParams,
  useNavigate,
  useSearchParams,
  useLocation,
} from "react-router-dom";
import {
  QueryClient,
  QueryClientProvider,
  useQuery,
} from "@tanstack/react-query";
import {
  BatteryCharging,
  LayoutList,
  Car,
  FileText,
  Settings,
  ArrowUpRight,
  ArrowLeft,
  Plus,
  Search,
  ChevronRight,
  ShieldCheck,
  Clock,
  Check,
  Upload,
  Copy,
  Activity,
} from "lucide-react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
} from "recharts";
import "./style.css";
import { CorrectReading, SourcePanel } from "./EvidenceTools";
import {
  ValuationEditor,
  PolicyEditor,
  WarrantyPanel,
  ExcludeReading,
  type GovernanceVehicle,
} from "./Governance";
type Reading = {
  id: string;
  date: string;
  value: number;
  miles: number;
  source: string;
  pack: string;
  state: string;
  actor: string;
  provenance: string;
  attachment?: string;
  method?: string;
  reference_basis?: string;
  exclusion_reason?: string;
  amendment_reason?: string;
};
type Assessment = {
  as_of: string;
  input_ids: string[];
  exclusions?: { id: string; reason: string }[];
  method?: string;
  interval: number[] | null;
  quality: string;
  reason: string;
  warnings: string[];
  action: string;
  count: number;
  last: Reading | null;
  age_days?: number;
  slope: number | null;
  scenarios: { months: number; interval: number[] }[];
};
type Vehicle = GovernanceVehicle & {
  id: string;
  year: number;
  make: string;
  model: string;
  stock: string;
  vin: string;
  miles: number;
  pack: string;
  scenario: string;
  base: number;
  included: string;
  revision: number;
  assessment: Assessment;
  readings: Reading[];
  events: { id: string; date: string; type: string; notes: string }[];
  decisions: {
    id: string;
    accepted: number;
    at: string;
    newer_evidence: boolean;
    customer_note?: string;
  }[];
  activity: { id: string; action: string; actor: string; at: string }[];
  recommendation: {
    interval: number[] | null;
    reason: string;
    adjustment: number[] | null;
    reserve: number;
  };
};
type Report = {
  newer_evidence?: boolean;
  id: string;
  vehicle: string;
  token: string;
  status: string;
  payload: Payload;
};
type Payload = {
  vehicle: string;
  vin: string;
  version: number;
  interval: number[] | null;
  quality: string;
  reason: string;
  last: { date: string; value: number } | null;
  readings: Reading[];
  pack: string;
  warranty: string;
  dealer: string;
  as_of: string;
  generated_at: string;
  pack_context?: { start_date?: string; verification?: string };
  expires_on?: string;
  limitations: string;
};
const qc = new QueryClient();
async function api<T = any>(path: string, body?: unknown): Promise<T> {
  const r = await fetch("/api" + path, {
    method: body === undefined ? "GET" : "POST",
    headers:
      body instanceof FormData ? {} : { "Content-Type": "application/json" },
    body:
      body === undefined
        ? undefined
        : body instanceof FormData
          ? body
          : JSON.stringify(body),
  });
  if (!r.ok) {
    if (
      r.status === 401 &&
      path !== "/session" &&
      !path.startsWith("/public/")
    ) {
      window.dispatchEvent(new Event("battery-session-expired"));
    }
    const e = await r.json().catch(() => ({}));
    throw Error(
      e.detail?.message || "Please check the entered values and retry.",
    );
  }
  return r.json();
}
const money = (n: number) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(n);
const date = (d: string) =>
  new Date(d.length === 10 ? d + "T12:00:00Z" : d).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    timeZone: "America/Chicago",
  });
const interval = (n: number[] | null) =>
  n ? `${n[0]}–${n[1]}%` : "Not enough evidence";
function Badge({
  children,
  tone = "neutral",
}: {
  children: React.ReactNode;
  tone?: string;
}) {
  return <span className={"badge " + tone}>{children}</span>;
}
function ErrorBox({ error }: { error: string }) {
  return error ? (
    <div role="alert" className="error">
      {error}
    </div>
  ) : null;
}
function Loading() {
  return (
    <div className="card loading" role="status" aria-label="Loading records">
      {[1, 2, 3, 4].map((i) => (
        <div key={i} />
      ))}
    </div>
  );
}
function readLocalDraft(key: string) {
  try {
    const value = JSON.parse(localStorage.getItem(key) || "null");
    return value && typeof value === "object" && !Array.isArray(value)
      ? value
      : null;
  } catch {
    return null;
  }
}
function App() {
  const loc = useLocation();
  const session = useQuery({
    queryKey: ["session"],
    queryFn: () => api("/session"),
    retry: false,
  });
  const [error, setError] = useState("");
  const [sessionExpired, setSessionExpired] = useState(false);
  const [loginBusy, setLoginBusy] = useState(false);
  useEffect(() => {
    const expire = () => setSessionExpired(true);
    window.addEventListener("battery-session-expired", expire);
    return () => window.removeEventListener("battery-session-expired", expire);
  }, []);
  if (loc.pathname.startsWith("/r/"))
    return (
      <Routes>
        <Route path="/r/:token" element={<PublicReport />} />
      </Routes>
    );
  if (session.isPending) return <Loading />;
  if (!session.data || sessionExpired)
    return (
      <div className="login">
        <BatteryCharging size={44} />
        <h1>Battery Timeline</h1>
        <p>Service evidence. Confident handoffs.</p>
        <Badge>Tek-Qubit concept · Demo access</Badge>
        <div className="card">
          <h2>Open Northline Motors</h2>
          <p>Choose a seeded role. Access is checked by the server.</p>
          {sessionExpired && (
            <p role="status">
              Your session expired. Sign in to continue. Your unfinished capture
              is saved on this browser.
            </p>
          )}
          {["manager", "technician", "sales"].map((role) => (
            <button
              className="primary wide"
              key={role}
              disabled={loginBusy}
              onClick={async () => {
                setLoginBusy(true);
                setError("");
                try {
                  await api("/session", { role });
                  await qc.cancelQueries();
                  qc.clear();
                  await qc.fetchQuery({
                    queryKey: ["session"],
                    queryFn: () => api("/session"),
                  });
                  setSessionExpired(false);
                } catch (e) {
                  setError(String(e));
                } finally {
                  setLoginBusy(false);
                }
              }}
            >
              Continue as {role}
              <ChevronRight size={17} />
            </button>
          ))}
          <ErrorBox error={error} />
        </div>
        <small>
          Independent hackathon concept. No Tekion integration or endorsement.
        </small>
      </div>
    );
  return (
    <div className="shell">
      <aside>
        <Link className="brand" to="/work-queue">
          <span className="logo">
            <BatteryCharging />
          </span>
          <span>
            Battery
            <br />
            Timeline
          </span>
        </Link>
        <small className="concept">TEK-QUBIT CONCEPT</small>
        <div className="navlabel">WORKSPACE</div>
        <nav aria-label="Main navigation">
          {[
            ["/work-queue", "Work queue", LayoutList],
            ["/vehicles", "Vehicles", Car],
            ["/reports", "Reports", FileText],
            ["/settings/sources", "Sources & settings", Settings],
          ].map(([p, t, Icon]) => {
            const active =
              loc.pathname === p ||
              (p === "/work-queue" &&
                (loc.pathname === "/" ||
                  loc.pathname.startsWith("/service/"))) ||
              (p !== "/work-queue" && loc.pathname.startsWith(String(p) + "/"));
            return (
              <Link
                key={String(p)}
                aria-label={String(t)}
                aria-current={active ? "page" : undefined}
                title={String(t)}
                className={active ? "active" : ""}
                to={String(p)}
              >
                {React.createElement(Icon as typeof Car, { size: 19 })}
                <span className="nav-text">{String(t)}</span>
                {p === "/settings/sources" && (
                  <span className="nav-short">Sources</span>
                )}
              </Link>
            );
          })}
        </nav>
        <div className="sidebar-note">
          <ShieldCheck size={20} />
          <strong>Evidence before decisions</strong>
          <p>
            Every reading has a source.
            <br />
            Every decision has a record.
          </p>
        </div>
        <div className="profile">
          <span className="avatar">NL</span>
          <div>
            Northline Motors<small>Chicago, Illinois</small>
          </div>
        </div>
      </aside>
      <div className="workspace">
        <header>
          <div>
            <span className="dealer">Northline Motors</span>
            <span className="divider">/</span>
            <span>Used vehicle operations</span>
          </div>
          <div className="header-right">
            <Badge tone="amber">Demo · {date(session.data.as_of)}</Badge>
            <span className="role">{session.data.role}</span>
            <button
              className="signout"
              onClick={async () => {
                await api("/session/logout", {});
                qc.clear();
                location.assign("/");
              }}
            >
              Sign out
            </button>
          </div>
        </header>
        <main>
          <Routes>
            <Route path="/" element={<Queue />} />
            <Route path="/work-queue" element={<Queue />} />
            <Route path="/vehicles" element={<Queue all />} />
            <Route path="/vehicles/:id" element={<Detail />} />
            <Route path="/service/:id/capture" element={<Capture />} />
            <Route path="/reports" element={<Reports />} />
            <Route path="/reports/:id/preview" element={<Preview />} />
            <Route path="/settings/sources" element={<Sources />} />
          </Routes>
        </main>
        <footer>
          Battery Timeline · Tek-Qubit concept{" "}
          <span>Independent demo · Synthetic inventory</span>
        </footer>
      </div>
    </div>
  );
}
function Queue({ all = false }: { all?: boolean }) {
  const q = useQuery({
    queryKey: ["vehicles"],
    queryFn: () => api<{ items: Vehicle[]; total: number }>("/vehicles"),
  });
  const [sp, setSp] = useSearchParams();
  const filter = sp.get("view") || (all ? "all" : "needs");
  const search = sp.get("q") || "";
  const make = sp.get("make") || "";
  const scenario = sp.get("scenario") || "";
  function set(k: string, v: string) {
    const n = new URLSearchParams(sp);
    n.set(k, v);
    setSp(n);
  }
  const vs = q.data?.items || [];
  const needs = (v: Vehicle) => v.assessment.quality === "limited";
  const shown = vs.filter(
    (v) =>
      (filter === "all" || (filter === "needs" ? needs(v) : !needs(v))) &&
      `${v.stock} ${v.vin} ${v.make} ${v.model}`
        .toLowerCase()
        .includes(search.toLowerCase()) &&
      (!make || v.make === make) &&
      (!scenario || v.scenario === scenario),
  );
  return (
    <>
      <div className="eyebrow">WORK QUEUE</div>
      <div className="page-title">
        <div>
          <h1>{all ? "Vehicle inventory" : "EV battery appraisals"}</h1>
          <p>Turn service-lane evidence into your next informed decision.</p>
        </div>
        <Badge>
          <span className="dot" />{" "}
          {q.data
            ? `${q.data.total} vehicles in inventory`
            : "Loading inventory…"}
        </Badge>
      </div>
      <div className="workflow-banner">
        <div className="banner-icon">
          <Activity />
        </div>
        <div>
          <strong>From service visit to buyer report</strong>
          <p>One vehicle record. Evidence at every step.</p>
        </div>
        <span className="flow">
          Capture <ChevronRight size={14} /> Timeline <ChevronRight size={14} />{" "}
          Appraisal <ChevronRight size={14} /> Report
        </span>
      </div>
      <section className="card queue-card">
        <div className="toolbar">
          <div className="segments">
            {[
              ["needs", "Needs action", vs.filter(needs).length],
              [
                "ready",
                "Ready for appraisal",
                vs.filter((v) => !needs(v)).length,
              ],
              ["all", "All vehicles", vs.length],
            ].map(([key, label, count]) => (
              <button
                key={key}
                aria-pressed={filter === key}
                onClick={() => set("view", String(key))}
                className={filter === key ? "selected" : ""}
              >
                {label}
                <span>{q.data ? count : "—"}</span>
              </button>
            ))}
          </div>
          <div className="search-row">
            <label className="search">
              <Search size={18} />
              <input
                aria-label="Search vehicles"
                placeholder="Search stock, VIN, make or model"
                value={search}
                onChange={(e) => set("q", e.target.value)}
              />
            </label>
            <select
              aria-label="Filter by make"
              value={make}
              onChange={(e) => set("make", e.target.value)}
            >
              <option value="">All makes</option>
              {[...new Set(vs.map((v) => v.make))].map((m) => (
                <option key={m}>{m}</option>
              ))}
            </select>
            <select
              aria-label="Demo scenario"
              value={scenario}
              onChange={(e) => set("scenario", e.target.value)}
            >
              <option value="">All demo scenarios</option>
              {[...new Set(vs.map((v) => v.scenario))].map((x) => (
                <option key={x}>{x}</option>
              ))}
            </select>
          </div>
        </div>
        {q.isLoading ? (
          <Loading />
        ) : q.error ? (
          <>
            <ErrorBox error={String(q.error)} />
            <button onClick={() => q.refetch()}>Retry</button>
          </>
        ) : (
          <>
            <div className="queue-head">
              <span>VEHICLE</span>
              <span>BATTERY HEALTH</span>
              <span>EVIDENCE QUALITY</span>
              <span>LAST READING</span>
              <span>NEXT ACTION</span>
            </div>
            {shown.map((v) => (
              <div className="vehicle-row" key={v.id}>
                <Link className="vehicle-name" to={"/vehicles/" + v.id}>
                  <span className="car-icon">
                    <Car size={25} />
                  </span>
                  <span>
                    <strong>
                      {v.year} {v.make} {v.model}
                    </strong>
                    <small>
                      {v.stock} <span>·</span> {v.miles.toLocaleString()} mi
                    </small>
                  </span>
                </Link>
                <div className="health-cell">
                  <span className="cell-label">Estimated battery health</span>
                  <strong className={v.assessment.interval ? "" : "no-health"}>
                    {interval(v.assessment.interval)}
                  </strong>
                  <small>
                    {v.warranty.time_remaining !== null
                      ? `${v.warranty.miles_remaining?.toLocaleString()} mi warranty headroom`
                      : v.warranty.status}
                  </small>
                </div>
                <div>
                  <span className="cell-label">Evidence quality</span>
                  <Badge tone={needs(v) ? "amber" : "teal"}>
                    {v.assessment.warnings.length
                      ? "Needs review"
                      : v.assessment.quality}
                  </Badge>
                  <small>{v.scenario}</small>
                </div>
                <div>
                  <span>
                    {v.assessment.last
                      ? date(v.assessment.last.date)
                      : "No reading yet"}
                  </span>
                  <small>
                    {v.assessment.age_days !== undefined
                      ? `${v.assessment.age_days} days ago`
                      : "Start the Timeline"}
                  </small>
                </div>
                <Link
                  className="row-action"
                  to={
                    v.assessment.count
                      ? "/vehicles/" + v.id
                      : "/service/" + v.id + "/capture"
                  }
                >
                  {v.assessment.count
                    ? needs(v)
                      ? "Review evidence"
                      : "Open appraisal"
                    : "Capture reading"}
                  <ArrowUpRight size={16} />
                </Link>
              </div>
            ))}
            {!shown.length && (
              <div className="empty">
                <Search />
                <h2>No matching vehicles</h2>
                <p>Try another search or clear your filters.</p>
                <button onClick={() => setSp({ view: "all" })}>
                  Clear filters
                </button>
              </div>
            )}
            <div className="table-footer">
              Showing {shown.length} of {vs.length} vehicles{" "}
              <span>All distances in miles · USD</span>
            </div>
          </>
        )}
      </section>
      <div className="footnote">
        <ShieldCheck size={16} /> Battery health describes remaining usable
        capacity relative to its reference capacity. It is different from charge
        level.
      </div>
    </>
  );
}
function Chart({
  readings,
  events = [],
}: {
  readings: Reading[];
  events?: { date: string; type: string }[];
}) {
  const points = [...readings]
    .sort((a, b) => a.date.localeCompare(b.date))
    .map((r) => ({ ...r, time: new Date(r.date + "T12:00:00Z").getTime() }));
  const packs = [...new Set(points.map((r) => r.pack || "current"))];
  return (
    <>
      <div
        className="chart"
        role="img"
        aria-label="Confirmed battery health readings by elapsed date, on a zero to one hundred percent scale"
      >
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={points}
            margin={{ top: 16, right: 16, bottom: 8, left: -16 }}
          >
            <CartesianGrid
              strokeDasharray="3 4"
              vertical={false}
              stroke="#e5e9eb"
            />
            <XAxis
              type="number"
              dataKey="time"
              domain={["dataMin", "dataMax"]}
              tickFormatter={(v) =>
                new Date(v).toLocaleDateString("en-US", {
                  timeZone: "America/Chicago",
                  month: "short",
                  year: "2-digit",
                })
              }
              tick={{ fontSize: 11 }}
            />
            <YAxis domain={[0, 100]} unit="%" tick={{ fontSize: 11 }} />
            {events.map((e, i) => (
              <ReferenceLine
                key={i}
                x={new Date(e.date + "T12:00:00Z").getTime()}
                stroke="#8a9099"
                strokeDasharray="4 4"
                label={{
                  value: e.type,
                  position: "insideBottomRight",
                  fontSize: 10,
                }}
              />
            ))}
            <Tooltip
              labelFormatter={(v) => date(new Date(Number(v)).toISOString())}
            />
            {packs.map((pack, i) => (
              <Line
                key={pack}
                dataKey={(r) =>
                  (r.pack || "current") === pack ? r.value : null
                }
                name={pack + " pack · health %"}
                connectNulls={false}
                stroke={i ? "#8791a0" : "#008578"}
                strokeWidth={2}
                dot={(p: any) => {
                  if (p.value === null || p.value === undefined)
                    return <g key={p.key} />;
                  const independent = p.payload.source === "Independent test";
                  return independent ? (
                    <rect
                      key={p.key}
                      x={p.cx - 4}
                      y={p.cy - 4}
                      width={8}
                      height={8}
                      fill="white"
                      stroke="#008578"
                      strokeWidth={2}
                    />
                  ) : (
                    <circle
                      key={p.key}
                      cx={p.cx}
                      cy={p.cy}
                      r={4}
                      fill="white"
                      stroke="#008578"
                      strokeWidth={2}
                    />
                  );
                }}
                isAnimationActive={false}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div className="legend">
        <span className="dot" /> ○ Diagnostic / transcription · □ Independent
        test <span>0–100% scale · Pack segments are separate</span>
      </div>
    </>
  );
}
function Detail() {
  const role = (qc.getQueryData(["session"]) as { role: string })?.role;
  const { id } = useParams();
  const q = useQuery({
    queryKey: ["vehicle", id],
    queryFn: () => api<Vehicle>("/vehicles/" + id),
  });
  const nav = useNavigate();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [reason, setReason] = useState("");
  const [amount, setAmount] = useState("");
  const [tab, setTab] = useState("Timeline");
  const [notice, setNotice] = useState("");
  const [reportOperation] = useState(() => crypto.randomUUID());
  if (!q.data)
    return q.error ? <ErrorBox error={String(q.error)} /> : <Loading />;
  const v = q.data;
  const h = v.assessment;
  async function decide() {
    setBusy(true);
    try {
      await api("/vehicles/" + id + "/appraisals", {
        revision: v.revision,
        base: v.base,
        included: v.included,
        amount: amount ? Number(amount) : null,
        reason,
        operation_id: crypto.randomUUID(),
        decision_revision: v.decision_revision || 0,
        policy_version: v.policy.version,
      });
      setNotice("Appraisal saved with an immutable evidence snapshot.");
      await q.refetch();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }
  async function preview() {
    setBusy(true);
    try {
      const r = await api("/vehicles/" + id + "/reports", {
        operation_id: reportOperation,
        valid_days: 90,
      });
      nav("/reports/" + r.id + "/preview");
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <Link className="back" to="/work-queue">
        <ArrowLeft size={15} /> Work queue
      </Link>
      <div className="page-title">
        <div>
          <div className="eyebrow">
            {v.stock} · {v.scenario}
          </div>
          <h1>
            {v.year} {v.make} {v.model}
          </h1>
          <p>
            {v.miles.toLocaleString()} mi <span className="divider">·</span> VIN
            •••••••••••{v.vin.slice(-6)}{" "}
            <button
              className="icon-button"
              aria-label="Copy VIN"
              onClick={() => {
                navigator.clipboard.writeText(v.vin);
                setNotice("VIN copied");
              }}
            >
              <Copy size={14} />
            </button>
          </p>
        </div>
        {role !== "sales" && (
          <Link className="button primary" to={"/service/" + id + "/capture"}>
            <Plus size={17} /> Add reading
          </Link>
        )}
      </div>
      <div className="detail-grid">
        <div>
          <section className="card summary">
            <div className="health-overview">
              <div className="section-title">
                <span>Estimated battery health</span>
                <Badge tone={h.quality === "limited" ? "amber" : "teal"}>
                  {h.quality} evidence
                </Badge>
              </div>
              <div className={"big-health " + (!h.interval ? "no-health" : "")}>
                {interval(h.interval)}
              </div>
              <p>{h.reason}</p>
              <div className="summary-bottom">
                <div>
                  <small>LAST RECORDED READING</small>
                  <strong>
                    {h.last
                      ? `${h.last.value}% · ${date(h.last.date)}`
                      : "No confirmed reading"}
                  </strong>
                </div>
                <div>
                  <small>NEXT STEP</small>
                  <strong>{h.action}</strong>
                </div>
              </div>
            </div>
            <div className="summary-context">
              <details>
                <summary>Why this estimate?</summary>
                <p>
                  Current pack, confirmed usable-capacity readings only. Source
                  allowances and age widen the interval. These are product
                  assumptions, not calibrated confidence bounds. Same-day tests
                  count as one independent date.
                </p>
                <p>
                  Selected measurement method:{" "}
                  {h.method || "Not enough evidence"}.{" "}
                  {h.exclusions?.length || 0} readings excluded for incompatible
                  methods or invalid source values.
                </p>
                <p>
                  Trend requires at least 3 comparable dates over 183 days.{" "}
                  {h.slope !== null
                    ? `Observed slope: ${h.slope} percentage points/year.`
                    : "There is not enough consistent evidence for a trend."}
                </p>
                {h.scenarios.map((x) => (
                  <p key={x.months}>
                    {x.months}-month conditional scenario:{" "}
                    {interval(x.interval)}. Assumes continuation of the observed
                    trend.
                  </p>
                ))}
              </details>
              {h.warnings.map((w) => (
                <div className="warning" key={w}>
                  {w}
                </div>
              ))}
              {role === "manager" && (
                <a
                  className="button primary mobile-decision-link"
                  href="#appraisal-decision"
                >
                  Review appraisal <ArrowUpRight size={17} />
                </a>
              )}
            </div>
          </section>
          <div className="tabs">
            {(role === "sales"
              ? ["Timeline", "Warranty"]
              : ["Timeline", "Warranty", "Sources", "Activity"]
            ).map((t) => (
              <button
                className={tab === t ? "selected" : ""}
                onClick={() => setTab(t)}
                key={t}
              >
                {t}
              </button>
            ))}
          </div>
          {tab === "Timeline" ? (
            <section className="card">
              <div className="section-title">
                <h2>Battery Timeline</h2>
                <Badge>{v.readings.length} recorded readings</Badge>
              </div>
              <p className="muted">
                A sourced history, from service visit to appraisal.
              </p>
              {v.readings.length ? (
                <Chart
                  events={v.events}
                  readings={v.readings.filter(
                    (r) =>
                      r.state === "confirmed" &&
                      (r.pack !== v.pack || h.input_ids.includes(r.id)),
                  )}
                />
              ) : (
                <div className="empty">
                  <BatteryCharging />
                  <h2>Start this vehicle’s history</h2>
                  <p>A confirmed capacity reading is the first step.</p>
                </div>
              )}
              {v.events.map((e) => (
                <div className="warning" key={e.id}>
                  <strong>
                    {date(e.date)} · {e.type}
                  </strong>
                  <p>{e.notes}</p>
                </div>
              ))}
              <h3>Evidence records</h3>
              <div className="evidence-list">
                {[...v.readings].reverse().map((r) => (
                  <div className="evidence" key={r.id}>
                    <span className="evidence-dot">
                      <Check size={14} />
                    </span>
                    <div>
                      <strong>
                        {r.value}% battery health <Badge>{r.pack} pack</Badge>
                      </strong>
                      <p>
                        {r.source} · {date(r.date)} ·{" "}
                        {r.miles.toLocaleString(undefined, {
                          maximumFractionDigits: 0,
                        })}{" "}
                        mi
                      </p>
                      <small>
                        {r.provenance} · {r.state} ·{" "}
                        {r.actor || "Source confirmed"}
                      </small>
                      {r.state === "confirmed" && role === "manager" ? (
                        <ExcludeReading
                          id={r.id}
                          revision={v.revision}
                          api={api}
                        />
                      ) : r.state !== "confirmed" ? (
                        <Badge tone="amber">
                          {r.state} · excluded from assessment
                        </Badge>
                      ) : null}
                      {role === "manager" &&
                        r.state !== "superseded" &&
                        r.pack === v.pack && (
                          <CorrectReading
                            r={r}
                            revision={v.revision}
                            api={api}
                          />
                        )}
                      <small>
                        {r.method ||
                          "BMS capacity estimate · legacy assumption"}{" "}
                        ·{" "}
                        {r.reference_basis ||
                          "Original usable capacity · legacy assumption"}
                      </small>
                      {r.exclusion_reason && (
                        <p>Exclusion: {r.exclusion_reason}</p>
                      )}
                      {r.amendment_reason && (
                        <p>Correction: {r.amendment_reason}</p>
                      )}
                      {r.attachment && (
                        <a
                          href={"/api/attachments/" + r.attachment}
                          target="_blank"
                        >
                          View original image
                        </a>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </section>
          ) : tab === "Warranty" ? (
            <WarrantyPanel key={v.id + v.revision} v={v} api={api} />
          ) : tab === "Sources" ? (
            <SourcePanel key={v.id + v.revision} v={v} api={api} />
          ) : (
            <section className="card">
              <h2>Activity</h2>
              {v.activity.length ? (
                v.activity.map((e) => (
                  <p key={e.id}>
                    {e.action}
                    <small>
                      {e.actor} · {date(e.at)}
                    </small>
                  </p>
                ))
              ) : (
                <p>No dealer actions recorded yet.</p>
              )}
            </section>
          )}
        </div>
        {role === "manager" ? (
          <div className="appraisal-column">
            <section
              className="card appraisal"
              id="appraisal-decision"
              tabIndex={-1}
            >
              <div className="eyebrow">APPRAISAL DESK</div>
              <h2>Evidence into an offer</h2>
              <p>Illustrative dealer policy · {v.policy.version}</p>
              <div className="price-row">
                <span>Starting dealer appraisal</span>
                <strong>{money(v.base)}</strong>
              </div>
              <small>
                {v.base_source || "Synthetic dealer value"} · as of{" "}
                {date(v.base_effective_date || h.as_of)}
              </small>
              <div className="price-row">
                <span>Battery adjustment</span>
                <strong>
                  {v.recommendation.adjustment
                    ? v.recommendation.adjustment.map(money).join(" to ")
                    : "Pending"}
                </strong>
              </div>
              <div className="price-row">
                <span>Uncertainty reserve</span>
                <strong>{money(v.recommendation.reserve)}</strong>
              </div>
              <div className="offer">
                <small>SUGGESTED APPRAISAL</small>
                <strong>
                  {v.recommendation.interval
                    ? v.recommendation.interval.map(money).join(" – ")
                    : "Obtain more evidence"}
                </strong>
              </div>
              <details>
                <summary>Why this recommendation?</summary>
                <p>{v.recommendation.reason}</p>
                <p>
                  Reference health {v.policy.reference_health}%;{" "}
                  {money(v.policy.dollars_per_point)} per percentage point,
                  capped at ±{money(v.policy.cap)}. Unvalidated dealer demo
                  assumptions. Warranty does not add a premium.
                </p>
                <p>Base already includes battery: {v.included}.</p>
              </details>
              <ValuationEditor key={v.id + v.revision} v={v} api={api} />
              {h.quality === "limited" && (
                <div className="warning">
                  Obtain more evidence. Proceeding requires a review reason.
                </div>
              )}
              <label>
                Override amount (optional)
                <input
                  type="number"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  placeholder="USD"
                />
              </label>
              <label>
                Review / override reason
                <textarea
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  placeholder="Explain your decision when review is needed"
                />
              </label>
              <button
                className="primary wide"
                disabled={busy || !v.recommendation.interval}
                onClick={decide}
              >
                {amount ? "Save override" : "Accept appraisal"}
                <Check size={16} />
              </button>
              <ErrorBox error={error} />
              <div role="status" className="success">
                {notice}
              </div>
            </section>
            {v.decisions.map((d) => (
              <section className="card" key={d.id}>
                <Badge tone="teal">Accepted · {money(d.accepted)}</Badge>
                <p>{date(d.at)}</p>
                {d.customer_note && <p className="muted">{d.customer_note}</p>}
                {d.newer_evidence && (
                  <div className="warning">
                    Newer evidence or appraisal inputs are available. This
                    accepted offer is unchanged.
                  </div>
                )}
              </section>
            ))}
            <section className="card report-callout">
              <FileText />
              <h3>Carry the evidence forward</h3>
              <p>Create a privacy-safe buyer report from this assessment.</p>
              <button className="wide" disabled={busy} onClick={preview}>
                Preview battery report <ArrowUpRight size={16} />
              </button>
            </section>
          </div>
        ) : (
          <section className="card">
            <h2>Evidence workspace</h2>
            <p>
              {role === "technician"
                ? "Capture and review service evidence here. Managers handle appraisal decisions and report publication."
                : "Read-only vehicle summary. Open Reports to view published buyer reports."}
            </p>
            <Link className="button" to="/reports">
              View reports
            </Link>
          </section>
        )}
      </div>
    </>
  );
}
function Capture() {
  const asOf =
    (qc.getQueryData(["session"]) as { as_of: string })?.as_of ||
    new Date().toISOString().slice(0, 10);
  const role = (qc.getQueryData(["session"]) as { role: string })?.role;
  const { id } = useParams();
  const nav = useNavigate();
  const visit = useQuery({
    queryKey: ["visit", id],
    queryFn: () =>
      api<{ id: string; vehicle: string; ro: string; state: string }>(
        "/service-visits/" + id,
      ),
    enabled: role !== "sales",
  });
  const vehicleId = visit.data?.vehicle || id;
  const q = useQuery({
    queryKey: ["vehicle", vehicleId],
    queryFn: () => api<Vehicle>("/vehicles/" + vehicleId),
    enabled: !!visit.data,
  });
  const key = "capture-" + id;
  const [f, setF] = useState(
    () =>
      readLocalDraft(key) || {
        value: "",
        measurement: "ambiguous",
        date: asOf,
        odometer: "",
        unit: "mi",
        source: "OEM diagnostic tool",
        basis: "usable capacity",
        notes: "",
        method: "BMS capacity estimate",
        reference_basis: "Original usable capacity",
        temperature_c: "",
        soc_at_measurement: "",
      },
  );
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [extracting, setExtracting] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [upload, setUpload] = useState<{
    id: string;
    url: string;
    message: string;
    transcript?: string;
  } | null>(() => readLocalDraft(key + "-attachment"));
  const [captureMethod, setCaptureMethod] = useState<"manual" | "photo">(() =>
    readLocalDraft(key + "-attachment") ? "photo" : "manual",
  );
  const [success, setSuccess] = useState(false);
  function change(k: string, value: string) {
    const n = { ...f, [k]: value };
    setF(n);
    localStorage.setItem(key, JSON.stringify(n));
  }
  async function save(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const body = {
        ...f,
        value: Number(f.value),
        odometer: Number(f.odometer),
        temperature_c:
          f.temperature_c === "" || f.temperature_c === undefined
            ? null
            : Number(f.temperature_c),
        soc_at_measurement:
          f.soc_at_measurement === "" || f.soc_at_measurement === undefined
            ? null
            : Number(f.soc_at_measurement),
        pack: q.data?.pack,
        attachment: upload?.id || null,
      };
      const fingerprint = JSON.stringify(body);
      const pending = readLocalDraft(key + "-confirmation");
      const d =
        pending?.fingerprint === fingerprint
          ? pending
          : await api("/service-visits/" + id + "/capture-drafts", body);
      localStorage.setItem(
        key + "-confirmation",
        JSON.stringify({ id: d.id, fingerprint }),
      );
      await api("/capture-drafts/" + d.id + "/confirm", {});
      localStorage.removeItem(key);
      localStorage.removeItem(key + "-attachment");
      localStorage.removeItem(key + "-confirmation");
      await qc.invalidateQueries();
      setSuccess(true);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }
  if (role === "sales")
    return (
      <div className="card">
        <h1>Read-only access</h1>
        <p>A technician or manager can capture this reading.</p>
        <Link to={"/vehicles/" + vehicleId}>Back to vehicle</Link>
      </div>
    );
  if (visit.error)
    return (
      <div className="card">
        <ErrorBox error={String(visit.error)} />
        <button onClick={() => visit.refetch()}>Retry service visit</button>
      </div>
    );
  if (q.error)
    return (
      <div className="card">
        <ErrorBox error={String(q.error)} />
        <button onClick={() => q.refetch()}>Retry vehicle</button>
      </div>
    );
  if (!q.data) return <Loading />;
  return (
    <div className="capture-page">
      <Link className="back" to={"/vehicles/" + vehicleId}>
        <ArrowLeft size={15} /> Vehicle workspace
      </Link>
      <div className="eyebrow">
        SERVICE VISIT · {visit.data?.ro || "Loading visit…"}
      </div>
      <h1>Capture a battery reading</h1>
      <p>Review the source. Confirm the reading. Build the history.</p>
      {q.data && (
        <div className="capture-context">
          <Car />
          <div>
            <strong>
              {q.data.year} {q.data.make} {q.data.model}
            </strong>
            <small>
              {q.data.stock} · {q.data.miles.toLocaleString()} mi ·{" "}
              {q.data.pack} pack
            </small>
          </div>
          <Badge>{visit.data?.state}</Badge>
        </div>
      )}
      {success ? (
        <div className="card empty" role="status">
          <Check size={36} />
          <h2>Reading added to the Timeline</h2>
          <p>The assessment has been recalculated and saved.</p>
          <button
            className="primary"
            onClick={() => nav("/vehicles/" + vehicleId)}
          >
            Open updated appraisal <ArrowUpRight size={17} />
          </button>
        </div>
      ) : (
        <form onSubmit={save}>
          <div
            className="capture-methods"
            role="group"
            aria-label="Input method"
          >
            <button
              type="button"
              aria-pressed={captureMethod === "manual"}
              className={captureMethod === "manual" ? "selected" : ""}
              onClick={() => setCaptureMethod("manual")}
            >
              <FileText size={19} /> Enter reading
            </button>
            <button
              type="button"
              aria-pressed={captureMethod === "photo"}
              className={captureMethod === "photo" ? "selected" : ""}
              onClick={() => setCaptureMethod("photo")}
            >
              <Upload size={19} /> Upload photo
            </button>
          </div>
          <section
            className="card"
            hidden={captureMethod !== "photo" && !upload}
          >
            <div className="step-title">
              <span>1</span>
              <h2>Capture the evidence</h2>
              <Badge>Manual review</Badge>
            </div>
            <label className="upload">
              <Upload size={25} />
              <strong>Photograph or upload a diagnostic screen</strong>
              <span>JPEG, PNG or WebP · up to 8 MB</span>
              <input
                aria-label="Upload diagnostic image"
                type="file"
                disabled={busy || extracting || uploading}
                accept="image/png,image/jpeg,image/webp"
                capture="environment"
                onChange={async (e) => {
                  if (!e.target.files?.[0]) return;
                  setUploading(true);
                  const form = new FormData();
                  form.append("file", e.target.files[0]);
                  try {
                    const uploaded = await api("/uploads", form);
                    setUpload(uploaded);
                    localStorage.setItem(
                      key + "-attachment",
                      JSON.stringify(uploaded),
                    );
                    const next = { ...f, measurement: "ambiguous", value: "" };
                    setF(next);
                    localStorage.setItem(key, JSON.stringify(next));
                  } catch (err) {
                    setError(String(err));
                  } finally {
                    setUploading(false);
                  }
                }}
              />
            </label>
            {(uploading || extracting) && (
              <p role="status">
                {uploading
                  ? "Storing the image…"
                  : "Reading the image. Review is required before confirmation."}
              </p>
            )}
            {upload && (
              <>
                <img
                  className="uploaded"
                  src={upload.url}
                  alt="Original uploaded diagnostic evidence"
                />
                <p className="warning">{upload.message}</p>
                {upload.transcript && (
                  <details>
                    <summary>Review extracted text</summary>
                    <pre className="ocr-transcript">{upload.transcript}</pre>
                  </details>
                )}
                <button
                  type="button"
                  disabled={busy || extracting || uploading}
                  onClick={async () => {
                    setExtracting(true);
                    try {
                      const x = await api(
                        "/attachments/" + upload.id + "/extract",
                        {},
                      );
                      const reviewed = {
                        ...upload,
                        message: x.message,
                        transcript: x.transcript,
                      };
                      setUpload(reviewed);
                      localStorage.setItem(
                        key + "-attachment",
                        JSON.stringify(reviewed),
                      );
                      if (x.status === "review") {
                        const n = {
                          ...f,
                          value: x.value === null ? "" : String(x.value),
                          measurement: x.measurement,
                          date: x.date || f.date,
                          odometer:
                            x.odometer !== null
                              ? String(x.odometer)
                              : f.odometer,
                          unit: x.unit || f.unit,
                        };
                        setF(n);
                        localStorage.setItem(key, JSON.stringify(n));
                      }
                    } catch (e) {
                      setError(String(e));
                    } finally {
                      setExtracting(false);
                    }
                  }}
                >
                  Extract with configured OCR
                </button>
              </>
            )}
            <p className="muted">
              Review the original image against the fields below before
              confirming.
            </p>
          </section>
          <section className="card">
            <div className="step-title">
              <span>{captureMethod === "photo" || upload ? "2" : "1"}</span>
              <h2>Review the reading</h2>
            </div>
            <div className="info">
              Battery health is remaining usable capacity. Charge level is how
              full the battery is right now.
            </div>
            <div className="form-grid">
              <label>
                Measurement type
                <select
                  value={f.measurement}
                  onChange={(e) => change("measurement", e.target.value)}
                >
                  <option value="ambiguous">Select measurement type</option>
                  <option value="health">
                    Battery health / usable capacity
                  </option>
                  <option value="charge">State of charge</option>
                </select>
              </label>
              <label>
                Reading (%)
                <input
                  required
                  type="number"
                  min="0"
                  max="100"
                  step="0.01"
                  inputMode="decimal"
                  value={f.value}
                  onChange={(e) => change("value", e.target.value)}
                />
              </label>
              <label>
                Reading date
                <input
                  required
                  type="date"
                  value={f.date}
                  onChange={(e) => change("date", e.target.value)}
                />
              </label>
              <label>
                Odometer
                <input
                  required
                  type="number"
                  min="0"
                  step="0.01"
                  inputMode="decimal"
                  placeholder={String(q.data?.miles || "")}
                  value={f.odometer}
                  onChange={(e) => change("odometer", e.target.value)}
                />
              </label>
              <label>
                Distance unit
                <select
                  value={f.unit}
                  onChange={(e) => change("unit", e.target.value)}
                >
                  <option value="mi">Miles (mi)</option>
                  <option value="km">Kilometers (km)</option>
                </select>
              </label>
              <label>
                Source
                <select
                  value={f.source}
                  onChange={(e) => change("source", e.target.value)}
                >
                  {[
                    "OEM diagnostic tool",
                    "OEM dashboard",
                    "Independent test",
                    "Manual transcription",
                  ].map((x) => (
                    <option key={x}>{x}</option>
                  ))}
                </select>
              </label>
            </div>
            <label>
              Measurement method
              <select
                value={f.method || "BMS capacity estimate"}
                onChange={(e) => change("method", e.target.value)}
              >
                <option>BMS capacity estimate</option>
                <option>Measured usable energy</option>
                <option value="unknown">Unknown — needs review</option>
              </select>
            </label>
            <label>
              Reference capacity
              <select
                value={f.reference_basis || "Original usable capacity"}
                onChange={(e) => change("reference_basis", e.target.value)}
              >
                <option>Original usable capacity</option>
                <option>Documented replacement reference</option>
                <option value="unknown">Unknown — needs review</option>
              </select>
            </label>
            <label>
              Measurement basis
              <select
                value={f.basis}
                onChange={(e) => change("basis", e.target.value)}
              >
                <option value="usable capacity">
                  Usable capacity relative to reference
                </option>
                <option value="unknown">Unknown — needs review</option>
              </select>
            </label>
            <details>
              <summary>Optional measurement conditions</summary>
              <div className="form-grid">
                <label>
                  Battery temperature (°C)
                  <input
                    type="number"
                    min="-50"
                    max="100"
                    step="0.1"
                    value={f.temperature_c || ""}
                    onChange={(e) => change("temperature_c", e.target.value)}
                  />
                </label>
                <label>
                  State of charge at test (%)
                  <input
                    type="number"
                    min="0"
                    max="100"
                    value={f.soc_at_measurement || ""}
                    onChange={(e) =>
                      change("soc_at_measurement", e.target.value)
                    }
                  />
                </label>
              </div>
            </details>
            <label>
              Internal notes (optional)
              <textarea
                value={f.notes}
                onChange={(e) => change("notes", e.target.value)}
                placeholder="Measurement conditions, temperature, SOC, or source context if known"
              />
            </label>
            <ErrorBox error={error} />
          </section>
          <div className="confirm-bar">
            <span>Only confirmed health readings affect the assessment.</span>
            <button
              className="primary"
              disabled={busy || extracting || uploading}
            >
              {busy ? "Saving and assessing…" : "Confirm and add to Timeline"}
              <Check size={17} />
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
function Reports() {
  const q = useQuery({
    queryKey: ["reports"],
    queryFn: () => api<Report[]>("/reports"),
  });
  return (
    <>
      <div className="eyebrow">BUYER HANDOFF</div>
      <h1>Battery reports</h1>
      <p>
        Immutable evidence summaries. Each published version has its own link.
      </p>
      <div className="card">
        {q.data?.length ? (
          q.data.map((r) => (
            <Link
              className="report-row"
              key={r.id}
              to={"/reports/" + r.id + "/preview"}
            >
              <FileText />
              <div>
                <strong>{r.payload.vehicle}</strong>
                <small>
                  Version {r.payload.version} · {date(r.payload.as_of)}
                  {r.newer_evidence ? " · Newer evidence available" : ""}
                </small>
              </div>
              <Badge tone={r.status === "published" ? "teal" : "neutral"}>
                {r.status}
              </Badge>
              <ChevronRight />
            </Link>
          ))
        ) : (
          <div className="empty">
            <FileText />
            <h2>No reports yet</h2>
            <p>Open a vehicle to preview its battery report.</p>
            <Link className="button" to="/vehicles">
              Browse vehicles
            </Link>
          </div>
        )}
      </div>
    </>
  );
}
function ReportBody({ p, token }: { p: Payload; token?: string }) {
  return (
    <article className="report-paper">
      <div className="report-brand">
        <BatteryCharging />
        <strong>BATTERY TIMELINE</strong>
        <Badge>Dealer-issued evidence summary</Badge>
      </div>
      <h1>Battery Health Report</h1>
      <p>{p.vehicle}</p>
      <small>
        VIN {p.vin} · Version {p.version} · As of {date(p.as_of)}
      </small>
      {p.expires_on && (
        <small>
          Expires {date(p.expires_on)}. Scan the QR for current status.
        </small>
      )}
      <div className="report-health">
        <small>ESTIMATED BATTERY HEALTH</small>
        <div className="big-health">{interval(p.interval)}</div>
        <Badge tone="teal">{p.quality} evidence</Badge>
        <p>{p.reason}</p>
        <p>
          Last recorded:{" "}
          {p.last
            ? `${p.last.value}% on ${date(p.last.date)}`
            : "No confirmed readings"}
        </p>
      </div>
      <h2>Current-pack history</h2>
      <p>
        Pack: {p.pack}. Earlier pack readings are excluded from this estimate.
        {p.pack_context?.start_date && (
          <>
            {" "}
            Segment start: {date(p.pack_context.start_date)} (
            {p.pack_context.verification}). Replacement coverage is assessed
            separately.
          </>
        )}
      </p>
      {p.readings.length > 0 && <Chart readings={p.readings} />}
      <div className="report-data">
        {p.readings.map((r, i) => (
          <div key={i}>
            <span>{date(r.date)}</span>
            <strong>{r.value}%</strong>
            <span>{r.source}</span>
          </div>
        ))}
      </div>
      <h2>Warranty information</h2>
      <p>{p.warranty}</p>
      <h2>What this report tells you</h2>
      <p>{p.limitations}</p>
      <p>
        Battery health means usable capacity relative to the relevant reference
        capacity. It is different from charge level or driving range.
      </p>
      {token && (
        <div className="qr">
          <img
            src={"/api/public/reports/" + token + "/qr"}
            alt="QR code for this exact report version"
          />
          <div>
            <strong>Keep the evidence with the vehicle</strong>
            <p>
              <a href={"/r/" + token}>Open this published version</a>
            </p>
            <a
              className="button"
              href={"/api/public/reports/" + token + "/pdf"}
            >
              Download PDF <FileText size={16} />
            </a>
          </div>
        </div>
      )}
      <div className="report-footer">
        {p.dealer}
        <br />
        Generated {date(p.generated_at)} · Independent Tek-Qubit concept
      </div>
    </article>
  );
}
function Preview() {
  const canPublish =
    (qc.getQueryData(["session"]) as { role: string })?.role === "manager";
  const { id } = useParams();
  const q = useQuery({
    queryKey: ["reports"],
    queryFn: () => api<Report[]>("/reports"),
  });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const r = q.data?.find((r) => r.id === id);
  async function act(action: string) {
    setBusy(true);
    try {
      await api("/reports/" + id + "/" + action, {});
      await q.refetch();
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }
  if (!r)
    return q.isLoading ? (
      <Loading />
    ) : (
      <div className="card">
        <h2>Report unavailable</h2>
        <p>
          {q.error
            ? String(q.error)
            : "This report does not exist or is not available to your role."}
        </p>
        <Link to="/reports">Back to reports</Link>
      </div>
    );
  return (
    <>
      <Link to="/reports" className="back">
        <ArrowLeft size={15} /> Reports
      </Link>
      <div className="page-title">
        <div>
          <h1>Report preview</h1>
          <p>Review the buyer-visible snapshot before publication.</p>
        </div>
        <div className="actions">
          <Badge>{r.status}</Badge>
          {r.newer_evidence && (
            <Badge tone="amber">Newer evidence available</Badge>
          )}
          {r.status === "draft" && canPublish ? (
            <button
              className="primary"
              disabled={busy}
              onClick={() => act("publish")}
            >
              Publish report
            </button>
          ) : r.status === "published" ? (
            <>
              <Link className="button" to={"/r/" + r.token}>
                Open public report
              </Link>
              {canPublish && (
                <button disabled={busy} onClick={() => act("revoke")}>
                  Revoke
                </button>
              )}
            </>
          ) : null}
        </div>
      </div>
      <ErrorBox error={error} />
      <ReportBody
        p={r.payload}
        token={r.status === "published" ? r.token : undefined}
      />
    </>
  );
}
function PublicReport() {
  const { token } = useParams();
  const q = useQuery({
    queryKey: ["public", token],
    queryFn: () => api<Payload>("/public/reports/" + token),
    retry: false,
  });
  return (
    <div className="public">
      {q.error ? (
        <div className="card">
          <h1>Report unavailable</h1>
          <ErrorBox error={String(q.error)} />
        </div>
      ) : q.data ? (
        <ReportBody p={q.data} token={token} />
      ) : (
        <Loading />
      )}
    </div>
  );
}
function Sources() {
  const q = useQuery({ queryKey: ["sources"], queryFn: () => api("/sources") });
  return (
    <>
      <div className="eyebrow">GOVERNANCE</div>
      <h1>Sources & settings</h1>
      <p>Know where the evidence comes from, and where its limits are.</p>
      <div className="settings-grid">
        <section className="card">
          <h2>Demo environment</h2>
          <Badge tone="amber">{q.data?.mode || "Loading"} data mode</Badge>
          <p>
            {q.data?.vehicle_count ?? "…"} synthetic vehicles. Assessment clock:{" "}
            {q.data?.as_of ? date(q.data.as_of) : "…"}. Dealer timezone:
            America/Chicago. Currency: USD.
          </p>
          <p>
            Public-data adapters use explicit fixture/live configuration.
            Optional local Tesseract OCR proposes fields for review; manual
            capture always works.
          </p>
          <h3>Source registry</h3>
          {q.data?.sources.map((s: any) => (
            <p key={s.title}>
              <a href={s.url}>{s.title} ↗</a>
              <small>{s.status}</small>
            </p>
          ))}
        </section>
        {q.data?.policy && (
          <PolicyEditor
            key={q.data.policy.version}
            policy={q.data.policy}
            api={api}
          />
        )}
      </div>
    </>
  );
}
createRoot(document.getElementById("root")!).render(
  <QueryClientProvider client={qc}>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </QueryClientProvider>,
);
