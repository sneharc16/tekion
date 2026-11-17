import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
type Call = (path: string, body?: unknown) => Promise<any>;
export function CorrectReading({
  r,
  revision,
  api,
}: {
  r: any;
  revision: number;
  api: Call;
}) {
  const qc = useQueryClient();
  const [f, setF] = useState({
    value: String(r.raw_value ?? r.value),
    odometer: String(r.original_odometer ?? r.miles),
    unit: r.unit || "mi",
    date: r.date,
    reason: "",
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [op] = useState(() => crypto.randomUUID());
  return (
    <details>
      <summary>Correct this reading</summary>
      <p>
        The new reading supersedes this observation. The original remains
        available in the evidence history.
      </p>
      <form
        onSubmit={async (e) => {
          e.preventDefault();
          setBusy(true);
          setError("");
          try {
            await api("/readings/" + r.id + "/supersede", {
              revision,
              reason: f.reason,
              operation_id: op,
              reading: {
                value: Number(f.value),
                odometer: Number(f.odometer),
                unit: f.unit,
                date: f.date,
                pack: r.pack,
                source: r.source,
                measurement: "health",
                basis: r.basis,
                method: r.method || "BMS capacity estimate",
                reference_basis:
                  r.reference_basis || "Original usable capacity",
                notes: r.notes || "",
                attachment: r.attachment || null,
              },
            });
            await qc.invalidateQueries();
          } catch (e) {
            setError(String(e));
          } finally {
            setBusy(false);
          }
        }}
      >
        <div className="form-grid">
          <label>
            Corrected health (%)
            <input
              required
              type="number"
              min="0"
              max="100"
              step="0.01"
              value={f.value}
              onChange={(e) => setF({ ...f, value: e.target.value })}
            />
          </label>
          <label>
            Corrected reading date
            <input
              required
              type="date"
              value={f.date}
              onChange={(e) => setF({ ...f, date: e.target.value })}
            />
          </label>
          <label>
            Corrected odometer
            <input
              required
              type="number"
              min="0"
              step="0.01"
              value={f.odometer}
              onChange={(e) => setF({ ...f, odometer: e.target.value })}
            />
          </label>
          <label>
            Original distance unit
            <select
              value={f.unit}
              onChange={(e) => setF({ ...f, unit: e.target.value })}
            >
              <option value="mi">Miles</option>
              <option value="km">Kilometers</option>
            </select>
          </label>
        </div>
        <label>
          Correction reason
          <textarea
            required
            minLength={10}
            value={f.reason}
            onChange={(e) => setF({ ...f, reason: e.target.value })}
          />
        </label>
        <button disabled={busy}>Confirm correction</button>
        {error && (
          <p role="alert" className="error">
            {error}
          </p>
        )}
      </form>
    </details>
  );
}
export function SourcePanel({ v, api }: { v: any; api: Call }) {
  const qc = useQueryClient();
  const canEdit =
    (qc.getQueryData(["session"]) as { role: string })?.role === "manager";
  const [result, setResult] = useState<Record<string, any>>({});
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [selection, setSelection] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [f, setF] = useState({
    vin: v.vin,
    make: v.make,
    model: v.model,
    year: v.year,
    trim: v.trim || "",
    reason: "",
  });
  async function fetchSource(provider: string) {
    setBusy(provider);
    setError("");
    try {
      setResult({
        ...result,
        [provider]: await api("/vehicles/" + v.id + "/external/" + provider),
      });
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy("");
    }
  }
  return (
    <section className="card">
      <h2>Identity & public sources</h2>
      <p>
        Identity, recalls and original rated range provide context. They do not
        measure battery health.
      </p>
      <span className="badge">
        {v.identification_status ||
          v.provenance + " · Identity not externally verified"}
      </span>
      <div className="source-actions">
        {[
          ["vin", "Decode VIN"],
          ["recalls", "Check model recalls"],
          ["epa", "Find EPA variants"],
        ].map(([key, label]) => (
          <button key={key} disabled={!!busy} onClick={() => fetchSource(key)}>
            {busy === key ? "Checking…" : label}
          </button>
        ))}
      </div>
      {Object.entries(result).map(([key, r]) => (
        <div className="source-result" key={key}>
          <div className="section-title">
            <h3>
              {key === "vin"
                ? "Vehicle identity"
                : key === "recalls"
                  ? "Model-level recall information"
                  : "EPA vehicle options"}
            </h3>
            <span className="badge">{r.status}</span>
          </div>
          <p>{r.message || r.data?.message}</p>
          <a href={r.source} target="_blank" rel="noreferrer">
            View public source ↗
          </a>
          {r.sources && (
            <details>
              <summary>Variant source history</summary>
              {r.sources.map((s: any, index: number) => (
                <p key={s.source}>
                  <a href={s.source} target="_blank" rel="noreferrer">
                    {index === 0
                      ? "EPA model menu"
                      : `EPA variant menu ${index}`}
                  </a>
                  {" · "}
                  {s.status}
                  {" · "}
                  {s.retrieved_at
                    ? new Date(s.retrieved_at).toLocaleString("en-US", {
                        timeZone: "America/Chicago",
                      }) + " CT"
                    : "Unavailable"}
                </p>
              ))}
            </details>
          )}
          <small>
            {r.retrieved_at
              ? "Retrieved " +
                new Date(r.retrieved_at).toLocaleString("en-US", {
                  timeZone: "America/Chicago",
                }) +
                " CT"
              : "No external retrieval performed"}
          </small>
          {key === "vin" && r.data && (
            <p>
              {r.data.identification_status}
              <br />
              {r.data.ModelYear} {r.data.Make} {r.data.Model} {r.data.Trim}
              <br />
              Review any mismatch against this vehicle before resolving
              identity.
              {r.data.review_required && (
                <span className="warning">
                  Provider reported an incomplete or inconsistent decode. This
                  is not verified VIN identity.
                </span>
              )}
            </p>
          )}
          {key === "recalls" && r.data && (
            <>
              <div className="warning">
                Model-level information is not proof of this VIN’s
                applicability, open status or completed repairs.
              </div>
              {r.data.items.length ? (
                r.data.items.map((x: any) => (
                  <details key={x.NHTSACampaignNumber}>
                    <summary>
                      {x.NHTSACampaignNumber} · {x.Component}
                    </summary>
                    <p>{x.Summary}</p>
                    <small>Reported {x.ReportReceivedDate}</small>
                  </details>
                ))
              ) : (
                <p>No model-level records returned.</p>
              )}
            </>
          )}
          {key === "epa" && r.data && (
            <>
              <label>
                Exact EPA variant
                <select
                  value={selection}
                  onChange={(e) => {
                    setSelection(e.target.value);
                    setConfirmed(false);
                  }}
                >
                  <option value="">
                    Select after checking trim, drive and battery
                  </option>
                  {r.data.options.map((x: any) => (
                    <option key={x.value} value={x.value}>
                      {x.text}
                    </option>
                  ))}
                </select>
              </label>
              {r.data.options.length > 1 && (
                <p className="warning">
                  Multiple variants: no option has been automatically selected.
                </p>
              )}
              {canEdit && (
                <>
                  <label className="check-label">
                    <input
                      type="checkbox"
                      checked={confirmed}
                      onChange={(e) => setConfirmed(e.target.checked)}
                    />
                    I checked this variant against the vehicle’s trim, drive and
                    battery.
                  </label>
                  <button
                    disabled={!selection || !confirmed || !!busy}
                    onClick={async () => {
                      setBusy("match");
                      setError("");
                      try {
                        await api("/vehicles/" + v.id + "/epa-match", {
                          revision: v.revision,
                          record_id: selection,
                          confirmation: confirmed,
                        });
                        await qc.invalidateQueries();
                        setNotice(
                          "EPA variant saved. It does not change battery health.",
                        );
                      } catch (e) {
                        setError(String(e));
                      } finally {
                        setBusy("");
                      }
                    }}
                  >
                    Save selected variant
                  </button>
                </>
              )}
            </>
          )}
        </div>
      ))}
      {v.epa_match && (
        <div className="info">
          <strong>Saved EPA variant: {v.epa_match.id}</strong>
          <p>
            {v.epa_match.description.drive} · {v.epa_match.description.fuelType}
          </p>
          <p>
            Original EPA-rated range:{" "}
            {v.epa_match.description.range ?? "Unknown"} miles. This is not
            driving range today.
          </p>
        </div>
      )}
      {canEdit && (
        <details>
          <summary>Resolve identity manually</summary>
          <p>
            Manual resolution is labeled as dealer-entered. Warranty and EPA
            matching must be reviewed again.
          </p>
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              setBusy("identity");
              setError("");
              try {
                await api("/vehicles/" + v.id + "/identity", {
                  ...f,
                  revision: v.revision,
                });
                await qc.invalidateQueries();
                setNotice(
                  "Identity saved as dealer-entered. Review warranty and EPA match.",
                );
                setResult({});
              } catch (e) {
                setError(String(e));
              } finally {
                setBusy("");
              }
            }}
          >
            <label>
              VIN
              <input
                required
                minLength={17}
                maxLength={17}
                pattern="[A-HJ-NPR-Z0-9]{17}"
                value={f.vin}
                onChange={(e) =>
                  setF({ ...f, vin: e.target.value.toUpperCase() })
                }
              />
            </label>
            <div className="form-grid">
              <label>
                Make
                <input
                  required
                  value={f.make}
                  onChange={(e) => setF({ ...f, make: e.target.value })}
                />
              </label>
              <label>
                Model
                <input
                  required
                  value={f.model}
                  onChange={(e) => setF({ ...f, model: e.target.value })}
                />
              </label>
              <label>
                Model year
                <input
                  required
                  type="number"
                  min="1996"
                  max="2030"
                  value={f.year}
                  onChange={(e) => setF({ ...f, year: Number(e.target.value) })}
                />
              </label>
              <label>
                Trim / variant
                <input
                  value={f.trim}
                  onChange={(e) => setF({ ...f, trim: e.target.value })}
                />
              </label>
            </div>
            <label>
              Identity evidence and reason
              <textarea
                required
                minLength={10}
                value={f.reason}
                onChange={(e) => setF({ ...f, reason: e.target.value })}
              />
            </label>
            <button disabled={!!busy}>Save manual identity</button>
          </form>
        </details>
      )}
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {notice && (
        <p className="success" role="status">
          {notice}
        </p>
      )}
    </section>
  );
}
