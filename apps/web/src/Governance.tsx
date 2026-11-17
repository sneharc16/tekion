import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { ShieldCheck, Save } from "lucide-react";
type Call = (path: string, body?: unknown) => Promise<any>;
export type Policy = {
  version: string;
  reference_health: number;
  dollars_per_point: number;
  cap: number;
  reserve: number;
  label: string;
};
export type Coverage = {
  status: string;
  reason: string;
  time_remaining: number | null;
  miles_remaining: number | null;
  expiry?: string;
  rule: null | {
    capacity_threshold: number | null;
    status: string;
    source: string;
    locator: string;
    verified_date: string;
    version: string;
    notes: string;
  };
};
export type GovernanceVehicle = {
  id: string;
  revision: number;
  base: number;
  included: string;
  base_source?: string;
  base_effective_date?: string;
  in_service?: string;
  market?: string;
  sale_state?: string;
  transfer_verified?: boolean;
  warranty_start_verified?: boolean;
  warranty_evidence?: string;
  warranty: Coverage;
  policy: Policy;
  decision_revision?: number;
};
function Feedback({ error, notice }: { error: string; notice: string }) {
  return (
    <>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      {notice && (
        <p role="status" className="success">
          {notice}
        </p>
      )}
    </>
  );
}
function useSave(api: Call) {
  const qc = useQueryClient();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  return {
    busy,
    error,
    notice,
    save: async (path: string, body: unknown, success: string) => {
      setBusy(true);
      setError("");
      setNotice("");
      try {
        await api(path, body);
        await qc.invalidateQueries();
        setNotice(success);
      } catch (e) {
        setError(String(e));
      } finally {
        setBusy(false);
      }
    },
  };
}
export function ValuationEditor({
  v,
  api,
}: {
  v: GovernanceVehicle;
  api: Call;
}) {
  const asOf = (useQueryClient().getQueryData(["session"]) as { as_of: string })
    ?.as_of;
  const [base, setBase] = useState(String(v.base));
  const [included, setIncluded] = useState(v.included);
  const [source, setSource] = useState(
    v.base_source || "Synthetic dealer appraisal",
  );
  const [date, setDate] = useState(
    v.base_effective_date || asOf || new Date().toISOString().slice(0, 10),
  );
  const save = useSave(api);
  return (
    <details>
      <summary>Edit starting appraisal</summary>
      <p>
        Save the starting value and its battery treatment before accepting an
        offer. Saved decisions remain unchanged.
      </p>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          save.save(
            "/vehicles/" + v.id + "/valuation",
            {
              revision: v.revision,
              base: Number(base),
              included,
              source,
              effective_date: date,
            },
            "Starting appraisal saved; recommendation recalculated.",
          );
        }}
      >
        <label>
          Starting value (USD)
          <input
            required
            type="number"
            min="0"
            max="1000000"
            step="0.01"
            value={base}
            onChange={(e) => setBase(e.target.value)}
          />
        </label>
        <label>
          Battery health already included?
          <select
            value={included}
            onChange={(e) => setIncluded(e.target.value)}
          >
            <option value="unknown">Unknown — resolve before applying</option>
            <option value="no">No — apply battery policy</option>
            <option value="yes">Yes — no additional battery adjustment</option>
          </select>
        </label>
        <label>
          Valuation source
          <input
            required
            minLength={3}
            maxLength={200}
            value={source}
            onChange={(e) => setSource(e.target.value)}
          />
        </label>
        <label>
          Effective date
          <input
            required
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
          />
        </label>
        <button className="wide" disabled={save.busy}>
          Save appraisal inputs <Save size={16} />
        </button>
      </form>
      <Feedback {...save} />
    </details>
  );
}
export function PolicyEditor({ policy, api }: { policy: Policy; api: Call }) {
  const [f, setF] = useState(policy);
  const save = useSave(api);
  return (
    <section className="card">
      <div className="eyebrow">DEALER ASSUMPTIONS</div>
      <h2>Appraisal policy</h2>
      <p className="policy-version">Active version: {policy.version}</p>
      <div className="warning">
        Illustrative pricing assumptions. These coefficients are not
        market-calibrated values.
      </div>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          save.save(
            "/settings/appraisal-policy",
            {
              previous_version: policy.version,
              reference_health: f.reference_health,
              dollars_per_point: f.dollars_per_point,
              cap: f.cap,
              reserve: f.reserve,
            },
            "New policy version saved. Existing decisions retain their original policy.",
          );
        }}
      >
        {(
          [
            ["reference_health", "Reference health (%)", 100],
            ["dollars_per_point", "USD per percentage point", 10000],
            ["cap", "Maximum adjustment (USD)", 50000],
            ["reserve", "Limited-evidence reserve (USD)", 50000],
          ] as const
        ).map(([key, label, max]) => (
          <label key={key}>
            {label}
            <input
              required
              type="number"
              min="0"
              max={max}
              step="0.01"
              value={f[key]}
              onChange={(e) => setF({ ...f, [key]: Number(e.target.value) })}
            />
          </label>
        ))}
        <p className="muted">
          Reserve applies only to limited evidence. No adjustment or reserve is
          added when the starting value already includes battery health.
        </p>
        <button disabled={save.busy} className="primary wide">
          Save new policy version <Save size={16} />
        </button>
      </form>
      <Feedback {...save} />
    </section>
  );
}
export function WarrantyPanel({ v, api }: { v: GovernanceVehicle; api: Call }) {
  const canEdit =
    (useQueryClient().getQueryData(["session"]) as { role: string })?.role ===
    "manager";
  const [f, setF] = useState({
    in_service: v.in_service || "",
    market: v.market || "unknown",
    sale_state: v.sale_state || "",
    transfer_verified: v.transfer_verified || false,
    warranty_start_verified: v.warranty_start_verified || false,
    warranty_evidence: v.warranty_evidence || "",
  });
  const save = useSave(api);
  const c = v.warranty;
  return (
    <section className="card">
      <ShieldCheck />
      <h2>{c.status}</h2>
      <p>{c.reason}</p>
      {(c.time_remaining !== null || c.miles_remaining !== null) && (
        <div className="warranty-metrics">
          <div>
            <strong>
              {c.time_remaining === null
                ? "Unknown"
                : c.time_remaining.toLocaleString()}
            </strong>
            <small>
              {c.expiry
                ? `days remaining · expires ${c.expiry}`
                : "time remaining · start date needs review"}
            </small>
          </div>
          <div>
            <strong>
              {c.miles_remaining === null
                ? "Unknown"
                : `${c.miles_remaining.toLocaleString()} mi`}
            </strong>
            <small>remaining · whichever comes first</small>
          </div>
        </div>
      )}
      {c.rule ? (
        <div className="info">
          <strong>
            {c.rule.capacity_threshold === null
              ? "Capacity provision: needs verification"
              : `Capacity provision: ${c.rule.capacity_threshold}%`}
          </strong>
          <p>
            {c.rule.status === "provisional"
              ? "Provisional source review · coverage not activated"
              : "Reviewed manufacturer rule · vehicle eligibility still applies"}
          </p>
          <p>{c.rule.notes}</p>
          <a href={c.rule.source} target="_blank" rel="noreferrer">
            View manufacturer source ↗
          </a>
          <small>
            {c.rule.locator} · Reviewed {c.rule.verified_date}
          </small>
        </div>
      ) : (
        <p>
          No exact model-year rule has been activated. Saving evidence does not
          create coverage terms.
        </p>
      )}
      {canEdit && (
        <details>
          <summary>Review warranty application evidence</summary>
          <p>
            Use documented first-service/delivery information, jurisdiction and
            eligibility. Demo records remain synthetic. A replacement pack does
            not reset these terms.
          </p>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              save.save(
                "/vehicles/" + v.id + "/warranty",
                {
                  ...f,
                  in_service: f.in_service || null,
                  revision: v.revision,
                },
                "Warranty evidence saved and coverage recalculated.",
              );
            }}
          >
            <div className="form-grid">
              <label>
                Actual in-service date
                <input
                  type="date"
                  value={f.in_service}
                  onChange={(e) => setF({ ...f, in_service: e.target.value })}
                />
              </label>
              <label>
                Warranty market
                <select
                  value={f.market}
                  onChange={(e) => setF({ ...f, market: e.target.value })}
                >
                  <option value="unknown">Unknown</option>
                  <option value="US">United States</option>
                </select>
              </label>
              <label>
                Sale state (two-letter code)
                <input
                  maxLength={2}
                  pattern="[A-Z]{2}"
                  value={f.sale_state}
                  onChange={(e) =>
                    setF({ ...f, sale_state: e.target.value.toUpperCase() })
                  }
                />
              </label>
            </div>
            <label className="check-label">
              <input
                type="checkbox"
                checked={f.warranty_start_verified}
                onChange={(e) =>
                  setF({ ...f, warranty_start_verified: e.target.checked })
                }
              />
              Start date verified against delivery / first-service evidence
            </label>
            <label className="check-label">
              <input
                type="checkbox"
                checked={f.transfer_verified}
                onChange={(e) =>
                  setF({ ...f, transfer_verified: e.target.checked })
                }
              />
              Transfer and ownership eligibility reviewed
            </label>
            <label>
              Evidence reference and verification notes
              <textarea
                required
                minLength={10}
                maxLength={1000}
                value={f.warranty_evidence}
                onChange={(e) =>
                  setF({ ...f, warranty_evidence: e.target.value })
                }
                placeholder="Document title, date and the eligibility basis reviewed"
              />
            </label>
            <button disabled={save.busy} className="primary">
              Save warranty evidence
            </button>
          </form>
          <Feedback {...save} />
        </details>
      )}
    </section>
  );
}
export function ExcludeReading({
  id,
  revision,
  api,
}: {
  id: string;
  revision: number;
  api: Call;
}) {
  const [reason, setReason] = useState("");
  const save = useSave(api);
  return (
    <details>
      <summary>Review / exclude this reading</summary>
      <p>
        Exclusion preserves the original observation and records your reason. It
        recalculates the current assessment; published reports remain fixed.
      </p>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          save.save(
            "/readings/" + id + "/exclude",
            { revision, reason },
            "Reading excluded; assessment updated.",
          );
        }}
      >
        <label>
          Reason for exclusion
          <textarea
            required
            minLength={10}
            maxLength={1000}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
          />
        </label>
        <button disabled={save.busy}>Exclude from assessment</button>
      </form>
      <Feedback {...save} />
    </details>
  );
}
