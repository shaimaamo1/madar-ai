import { useEffect, useState } from "react";
import { Activity, Play, RefreshCw, ShieldCheck, Sparkles } from "lucide-react";
import { api, Row, date } from "./api";
import { tr, localize, number, errorText, useLanguage } from "./i18n";

export function EnterpriseConsole({
  leads,
  demo,
  refresh,
}: {
  leads: Row[];
  demo: boolean;
  refresh: () => Promise<void>;
}) {
  const { lang: language } = useLanguage();
  const [health, setHealth] = useState<Row | null>(null);
  const [runs, setRuns] = useState<Row[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState(leads[0]?.id || "");
  const [agents, setAgents] = useState<Row | null>(null);
  async function load() {
    const [h, r] = await Promise.all([
      api("/system-health"),
      api("/demo/runs"),
    ]);
    setHealth(h);
    setRuns(r);
  }
  useEffect(() => {
    let active = true;
    const update = () => {
      if (active)
        load().catch((e) => {
          if (active) setError(e.message);
        });
    };
    update();
    const timer = setInterval(update, 15000);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, []);
  async function act(fn: () => Promise<unknown>) {
    setBusy(true);
    setError("");
    try {
      await fn();
      await load();
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  const current = runs[0];
  const labels: Row = {
    qualification: "Qualification agent",
    intent_detection: "Intent detection agent",
    property_explanation: "Property explanation agent",
    reply_drafting: "Reply drafting agent",
    sales_assistance: "Sales assistance agent",
  };
  return (
    <div className="enterprise-console">
      {error && (
        <div role="alert" className="alert error">
          {errorText(error)}
        </div>
      )}
      <section className="card">
        <div className="card-head">
          <div>
            <h3>
              <Activity size={18} />
              {tr("Component checks")}
            </h3>
            <p>{tr("Measured checks with explicit verification boundaries")}</p>
          </div>
          <button className="button" disabled={busy} onClick={() => act(load)}>
            <RefreshCw size={15} />
            {tr("Refresh checks")}
          </button>
        </div>
        <div className="health-grid">
          {health?.checks.map((check: Row) => (
            <article key={check.component} className="health-check">
              <div className="card-head">
                <strong>{tr(check.component)}</strong>
                <span
                  className={
                    "pill " +
                    (check.status === "PASS"
                      ? "green"
                      : check.status === "FAIL"
                        ? "red"
                        : "orange")
                  }
                >
                  {tr(check.status)}
                </span>
              </div>
              <p>{tr(check.detail, { count: number(check.count || 0) })}</p>
            </article>
          ))}
        </div>
        <p className="small muted">
          {tr("Last checked")}:{" "}
          {health ? date(health.checked_at) : tr("Loading…")}
        </p>
      </section>
      <section className="card">
        <div className="card-head">
          <div>
            <h3>
              <Play size={18} />
              {tr("Run Full Demo")}
            </h3>
            <p>
              {tr("Real n8n execution with isolated fictional CRM records")}
            </p>
          </div>
          <button
            className="button primary"
            disabled={
              busy ||
              !demo ||
              ["Queued", "Running", "Awaiting verification"].includes(
                current?.status,
              )
            }
            onClick={() => act(() => api("/demo/runs", "POST"))}
          >
            <Play size={15} />
            {tr("Queue full demo")}
          </button>
        </div>
        <p>
          {tr(
            "The imported inactive MADAR Full Demo workflow claims the queued run when executed in n8n. No customer messaging or paid models are used.",
          )}
        </p>
        {!demo && (
          <p className="small muted">
            {tr("Use a fictional demo workspace to run this scenario.")}
          </p>
        )}
        {current && (
          <>
            <div className="card-head">
              <span className="pill orange">{tr(current.status)}</span>
              <strong>
                {number(current.steps.length)}{" "}
                {tr("of eight business steps recorded")}
              </strong>
            </div>
            <div className="demo-steps">
              {[
                "intake",
                "qualification",
                "matching",
                "appointment",
                "followup",
                "conversation",
                "handoff",
                "reporting",
              ].map((kind) => (
                <div
                  key={kind}
                  className={
                    current.steps.some((s: Row) => s.kind === kind)
                      ? "step complete"
                      : "step"
                  }
                >
                  <ShieldCheck size={16} />
                  <span>{tr("demo_step_" + kind)}</span>
                </div>
              ))}
            </div>
            <p className="small muted">
              {tr("Execution reference")}:{" "}
              <span>{current.execution_id || tr("Not yet reported")}</span>
            </p>
            <button
              className="button"
              disabled={busy || current.status !== "Awaiting verification"}
              onClick={() =>
                act(() => api("/demo/runs/" + current.id + "/verify", "POST"))
              }
            >
              {tr("Verify n8n execution")}
            </button>
          </>
        )}
        <p className="small muted">
          {tr(
            "Records alone do not prove n8n success. Verification reads the actual execution status through the local n8n API.",
          )}
        </p>
      </section>
      <section className="card">
        <div className="card-head">
          <div>
            <h3>
              <Sparkles size={18} />
              {tr("Grounded AI agents")}
            </h3>
            <p>
              {tr(
                "Five evidence-based capabilities with explicit provider modes and human review",
              )}
            </p>
          </div>
        </div>
        <div className="filter-row">
          <div className="field">
            <label htmlFor="enterprise-customer">{tr("Customer")}</label>
            <select
              id="enterprise-customer"
              value={selected}
              onChange={(e) => {
                setSelected(e.target.value);
                setAgents(null);
              }}
            >
              {leads.map((l) => (
                <option key={l.id} value={l.id}>
                  {l.name}
                </option>
              ))}
            </select>
          </div>
          <button
            className="button primary"
            disabled={busy || !selected}
            onClick={() =>
              act(async () =>
                setAgents(
                  await api("/leads/" + selected + "/agents", "POST", {
                    language: language === "ar" ? "ar" : "en",
                  }),
                ),
              )
            }
          >
            {tr("Evaluate agents")}
          </button>
        </div>
        {agents && (
          <div className="health-grid">
            {Object.entries(agents).map(([key, value]) => (
              <article className="health-check" key={key}>
                <strong>{tr(labels[key])}</strong>
                <p className="small muted">
                  {tr(value.mode)} · {tr("Human approval required")}
                </p>
                {value.draft && (
                  <p dir="auto">{value.drafts?.[language] || value.draft}</p>
                )}
                {value.score !== undefined && (
                  <p>
                    {tr("Qualification score")}: {number(value.score)}
                  </p>
                )}
                {value.next_action && <p>{localize(value.next_action)}</p>}
                {value.readiness && <p>{tr(value.readiness)}</p>}
                {value.recommendations && (
                  <p>
                    {number(value.recommendations.length)}{" "}
                    {tr("verified inventory recommendations")}
                  </p>
                )}
              </article>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
