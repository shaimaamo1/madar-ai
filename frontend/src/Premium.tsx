import { useEffect, useState, FormEvent } from "react";
import {
  ArrowUpRight,
  Building2,
  MessageSquare,
  Plus,
  Send,
  ShieldCheck,
  Sparkles,
  UsersRound,
  Workflow,
} from "lucide-react";
import { api, Row, money, date, download } from "./api";
import { tr, localize, number, percent, errorText } from "./i18n";
import { workflowCatalog } from "./workflowCatalog";

export function OperatingStrip({
  operations,
  ar,
  demo = false,
}: {
  operations: Row;
  ar: boolean;
  demo?: boolean;
}) {
  return (
    <div className="operating-strip">
      <span>
        <ShieldCheck size={14} />
        <strong>
          {demo
            ? tr("Isolated demo workspace")
            : tr("Private company workspace")}
        </strong>
      </span>
      <span>
        <span className="status-dot" />
        {demo ? tr("Fictional CRM records") : tr("Live CRM records")}
      </span>
      <span>
        <UsersRound size={14} />
        {number(operations.human_handoffs || 0)} {tr("adviser handoffs")}
      </span>
      <span>
        <MessageSquare size={14} />
        {localize(
          operations.external_send_enabled
            ? tr("Operator enabled delivery")
            : tr("External delivery disabled"),
        )}
      </span>
    </div>
  );
}

export function ActivityTrend({ leads, ar }: { leads: Row[]; ar: boolean }) {
  const days = Array.from({ length: 14 }, (_, i) => {
    const d = new Date();
    d.setUTCDate(d.getUTCDate() - 13 + i);
    return d.toISOString().slice(0, 10);
  });
  const counts = days.map(
    (d) => leads.filter((l) => l.created_at.startsWith(d)).length,
  );
  const max = Math.max(...counts, 2),
    points = counts.map((count, i) => [34 + i * 43, 132 - (count / max) * 94]);
  const path = points.map(([x, y], i) => `${i ? "L" : "M"}${x},${y}`).join(" ");
  return (
    <section className="card">
      <div className="card-head">
        <div>
          <h3>{tr("The rhythm of new opportunities")}</h3>
          <p>{tr("Recorded inquiries over the last 14 days · UTC")}</p>
        </div>
        <span className="pill blue">
          {number(counts.reduce((a, b) => a + b, 0))} {tr("inquiries")}
        </span>
      </div>
      <div className="trend-chart">
        <svg
          viewBox="0 0 628 172"
          role="img"
          aria-label={tr("New inquiries over the last fourteen days")}
        >
          {[38, 85, 132].map((y, i) => (
            <g key={y}>
              <line className="grid-line" x1="34" y1={y} x2="598" y2={y} />
              <text x="6" y={y + 4}>
                {number(Math.round(max * (1 - i / 2)))}
              </text>
            </g>
          ))}
          <path
            d={`${path} L593,132 L34,132Z`}
            fill="var(--teal)"
            opacity=".07"
          />
          <path className="trend-line" d={path} />
          {points.map(([x, y], i) => (
            <circle
              key={i}
              cx={x}
              cy={y}
              r="4"
              fill="var(--card)"
              stroke="var(--teal)"
              strokeWidth="2"
            >
              <title>
                {date(days[i], {
                  timeZone: "UTC",
                  year: "numeric",
                  hour: undefined,
                  minute: undefined,
                })}
                : {localize(counts[i])} {tr("inquiries")}
              </title>
            </circle>
          ))}
          {[0, 4, 9, 13].map((i) => (
            <text key={i} x={points[i][0]} y="162" textAnchor="middle">
              {date(days[i], {
                timeZone: "UTC",
                month: "short",
                day: "numeric",
                hour: undefined,
                minute: undefined,
              })}
            </text>
          ))}
        </svg>
        <div className="trend-caption">
          <span>
            {tr("From the workspace records shown · up to 1,000 leads")}
          </span>
          <span>{tr("Observed activity, no forecast")}</span>
        </div>
      </div>
    </section>
  );
}

type DiagramNode = {
  id: string;
  name: string;
  type: string;
  position: number[];
  note?: string;
  width?: number;
  height?: number;
};
export function WorkflowStudio({ ar }: { ar: boolean }) {
  const [key, setKey] = useState("madar-omnichannel-intake");
  const [zoom, setZoom] = useState(1);
  const flow = workflowCatalog.find((w) => w.key === key)!;
  const nodes: DiagramNode[] = flow.nodes;
  const width =
    Math.max(...nodes.map((n) => n.position[0] + (n.width || 225))) + 60;
  const height =
    Math.max(...nodes.map((n) => n.position[1] + (n.height || 90))) + 35;
  const executable = nodes.filter((n) => n.type !== "stickyNote");
  return (
    <section className="card workflow-studio">
      <div className="card-head">
        <div>
          <h3>
            <Workflow size={18} />
            {tr("The customer journey, orchestrated")}
          </h3>
          <p>
            {tr(
              "Generated from actual n8n JSON. All modules are inactive; runtime requires local verification.",
            )}
          </p>
        </div>
        <span className="pill orange">{tr("Runtime not verified")}</span>
      </div>
      <div
        className="workflow-tabs"
        role="tablist"
        aria-label={tr("Workflow modules")}
      >
        {workflowCatalog.map((w) => (
          <button
            type="button"
            role="tab"
            id={"tab-" + w.key}
            aria-controls="workflow-diagram"
            aria-selected={key === w.key}
            tabIndex={key === w.key ? 0 : -1}
            onKeyDown={(event) => {
              const index = workflowCatalog.findIndex(
                (item) => item.key === key,
              );
              const next =
                event.key === "Home"
                  ? 0
                  : event.key === "End"
                    ? workflowCatalog.length - 1
                    : event.key === (ar ? "ArrowLeft" : "ArrowRight")
                      ? (index + 1) % workflowCatalog.length
                      : event.key === (ar ? "ArrowRight" : "ArrowLeft")
                        ? (index - 1 + workflowCatalog.length) %
                          workflowCatalog.length
                        : -1;
              if (next >= 0) {
                event.preventDefault();
                const id = workflowCatalog[next].key;
                setKey(id);
                document.getElementById("tab-" + id)?.focus();
              }
            }}
            className={key === w.key ? "selected" : ""}
            key={w.key}
            onClick={() => setKey(w.key)}
          >
            {tr(w.name.replace("MADAR ", ""))}
          </button>
        ))}
      </div>
      <div
        className="workflow-zoom"
        role="group"
        aria-label={tr("Diagram zoom")}
      >
        <button
          type="button"
          className="button"
          onClick={() => setZoom(Math.max(0.15, zoom - 0.15))}
        >
          {tr("Zoom out")}
        </button>
        <span>{percent(zoom * 100)}</span>
        <button
          type="button"
          className="button"
          onClick={() => setZoom(Math.min(1.5, zoom + 0.15))}
        >
          {tr("Zoom in")}
        </button>
        <button
          type="button"
          className="button"
          onClick={() =>
            setZoom(
              Math.max(
                0.15,
                Math.min(
                  1,
                  (document.getElementById("workflow-diagram")?.clientWidth ||
                    900) / width,
                ),
              ),
            )
          }
        >
          {tr("Fit diagram")}
        </button>
      </div>
      <div
        className="workflow-map"
        id="workflow-diagram"
        role="tabpanel"
        tabIndex={0}
        aria-labelledby={"tab-" + key}
      >
        <svg
          viewBox={`75 0 ${width} ${height}`}
          style={{ width: width * zoom, minWidth: 0 }}
          role="img"
          aria-label={tr("{name} actual workflow", {
            name: "MADAR " + tr(flow.name.replace("MADAR ", "")),
          })}
        >
          <defs>
            <marker
              id="flow-arrow"
              viewBox="0 0 10 10"
              refX="9"
              refY="5"
              markerWidth="5"
              markerHeight="5"
              orient="auto"
            >
              <path d="M0 0L10 5L0 10" fill="#6c8e9b" />
            </marker>
          </defs>
          {nodes
            .filter((n) => n.type === "stickyNote")
            .map((n) => (
              <g key={n.id}>
                <rect
                  className="group"
                  x={n.position[0]}
                  y={n.position[1]}
                  width={n.width}
                  height={n.height}
                  rx="12"
                />
                <text
                  className="group-label"
                  x={n.position[0] + (ar ? (n.width || 225) - 16 : 16)}
                  textAnchor={ar ? "end" : "start"}
                  direction={ar ? "rtl" : "ltr"}
                  y={n.position[1] + 26}
                >
                  {localize(n.note?.split("\n")[0].replace("## ", ""))}
                </text>
              </g>
            ))}
          {flow.edges.map((e, i) => {
            const a = nodes.find((n) => n.name === e.source)!,
              b = nodes.find((n) => n.name === e.target)!;
            const x1 = a.position[0] + 215,
              y1 = a.position[1] + 40,
              x2 = b.position[0],
              y2 = b.position[1] + 40;
            return (
              <g key={i}>
                <path
                  className="edge"
                  d={`M${x1},${y1} C${x1 + 45},${y1} ${x2 - 50},${y2} ${x2},${y2}`}
                  markerEnd="url(#flow-arrow)"
                />
                {a.type === "if" && (
                  <text
                    x={x1 + 9}
                    y={y1 + (e.branch === 0 ? -9 : 19)}
                    className="node-type"
                  >
                    {tr(e.branch === 0 ? "yes" : "no")}
                  </text>
                )}
              </g>
            );
          })}
          {executable.map((n) => (
            <g key={n.id} data-node-id={n.id}>
              <title>{localize(tr(n.name) + " · " + tr(n.type))}</title>
              <rect
                className="node-box"
                x={n.position[0]}
                y={n.position[1]}
                width="215"
                height="80"
                rx="10"
              />
              <rect
                className="node-icon"
                x={n.position[0] + 12}
                y={n.position[1] + 15}
                width="25"
                height="25"
                rx="6"
              />
              <text
                x={n.position[0] + 24}
                y={n.position[1] + 32}
                textAnchor="middle"
                style={{ fill: "#D8BE83" }}
              >
                {localize(
                  n.type === "if"
                    ? "?"
                    : n.type === "code"
                      ? "{}"
                      : n.type === "httpRequest"
                        ? "↗"
                        : "◈",
                )}
              </text>
              <text
                className="node-label"
                x={n.position[0] + (ar ? 203 : 48)}
                textAnchor={ar ? "end" : "start"}
                direction={ar ? "rtl" : "ltr"}
                y={n.position[1] + 29}
              >
                {localize(
                  tr(n.name).length > 27
                    ? tr(n.name).slice(0, 27) + "…"
                    : tr(n.name),
                )}
              </text>
              <text
                className="node-type"
                x={n.position[0] + (ar ? 203 : 14)}
                textAnchor={ar ? "end" : "start"}
                direction={ar ? "rtl" : "ltr"}
                y={n.position[1] + 62}
              >
                {tr(n.type)}
              </text>
            </g>
          ))}
        </svg>
      </div>
      <div className="workflow-footer">
        <span>
          <strong>
            {number(executable.length)} {tr("executable nodes")}
          </strong>{" "}
          · {number(flow.contracts.length)} {tr("backend contracts ·")}{" "}
          {number(flow.edges.length)} {tr("real connections")}
          <br />
          {tr("Owner authorization required before real external delivery")}
        </span>
        <button
          className="text-button"
          onClick={() => download(flow.key + "-architecture.json", flow)}
        >
          {tr("Export architecture")}
          <ArrowUpRight size={15} />
        </button>
      </div>
    </section>
  );
}

export function WhatsAppStudio({
  state,
  onUpdated,
  onBook,
  ar,
}: {
  state: Row;
  onUpdated: () => Promise<unknown>;
  onBook: (lead: Row, propertyId: string) => void;
  ar: boolean;
}) {
  const contacts = state.leads.filter((l: Row) =>
    l.external_id.startsWith("sandbox:"),
  );
  const [contact, setContact] = useState(
      contacts[0]?.external_id.slice(8) || crypto.randomUUID(),
    ),
    [text, setText] = useState(""),
    [consent, setConsent] = useState(false),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [intelligence, setIntelligence] = useState<Row | null>(null);
  const lead = contacts.find(
    (l: Row) => l.external_id === "sandbox:" + contact,
  );
  const messages = state.messages
    .filter((m: Row) => m.lead_id === lead?.id)
    .slice()
    .reverse();
  const human = state.conversation_controls?.some(
    (c: Row) => c.lead_id === lead?.id && c.human_active,
  );
  useEffect(() => {
    let current = true;
    if (!lead) {
      setIntelligence(null);
      return;
    }
    api("/leads/" + lead.id + "/intelligence")
      .then((value) => {
        if (current) setIntelligence(value);
      })
      .catch(() => {
        if (current) setIntelligence(null);
      });
    return () => {
      current = false;
    };
  }, [state, contact]);
  async function send(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api("/sandbox/whatsapp", "POST", {
        contact_id: contact,
        event_id: crypto.randomUUID(),
        name: "WhatsApp sandbox customer",
        text,
        consent,
      });
      setText("");
      await onUpdated();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function handoff() {
    if (!lead) return;
    setBusy(true);
    setError("");
    try {
      await api("/leads/" + lead.id + "/handoff", "POST", {
        active: !human,
        reason: "Operator takeover",
      });
      await onUpdated();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  if (!state.company.demo)
    return (
      <section className="card empty">
        <ShieldCheck size={35} />
        <h3>{tr("Rehearse in an isolated demo workspace")}</h3>
        <p>
          {tr(
            "Sign out and open the interactive demo to test WhatsApp without affecting customer data.",
          )}
        </p>
      </section>
    );
  return (
    <>
      <div className="connection-note">
        <ShieldCheck size={19} />
        <p>
          {tr(
            "Provider-free rehearsal. Messages update the fictional CRM; no Meta request, real delivery, or paid inference occurs.",
          )}
        </p>
      </div>
      {error && (
        <div className="alert" role="alert">
          {errorText(error)}
        </div>
      )}
      <div className="sandbox-grid">
        <section className="card">
          <div className="studio-heading">
            <span
              className="integration-icon whatsapp"
              style={{ marginBottom: 0 }}
            >
              <MessageSquare size={23} />
            </span>
            <div>
              <h3>{tr("WhatsApp sales studio")}</h3>
              <p>{tr("From first inquiry to a personal property adviser")}</p>
            </div>
            <span className="pill green">{tr("Sandbox")}</span>
          </div>
          <div className="sandbox-controls">
            <label className="field">
              {tr("Sandbox conversation")}
              <select
                aria-label={tr("Sandbox conversation")}
                value={contact}
                onChange={(e) => setContact(e.target.value)}
              >
                {!lead && (
                  <option value={contact}>{tr("New conversation")}</option>
                )}
                {contacts.map((c: Row) => (
                  <option value={c.external_id.slice(8)} key={c.id}>
                    {c.name} · {c.external_id.slice(8, 14)}
                  </option>
                ))}
              </select>
            </label>
            <button
              className="button"
              onClick={() => {
                setContact(crypto.randomUUID());
                setIntelligence(null);
                setConsent(false);
              }}
            >
              <Plus size={15} />
              {tr("New conversation")}
            </button>
          </div>
          <div className="message-list" aria-live="polite">
            {!messages.length && (
              <div className="empty">
                <Sparkles size={29} />
                <h3>{tr("A thoughtful adviser. A real inventory.")}</h3>
                <p>
                  {tr(
                    "Try: New Cairo apartment, budget 5 million, 3 bedrooms.",
                  )}
                </p>
              </div>
            )}
            {messages.map((m: Row) => (
              <div key={m.id} className={"message " + m.direction}>
                <p dir="auto">{m.body}</p>
                <small>
                  {localize(m.direction === "inbound" ? "Customer" : "MADAR")} ·{" "}
                  {date(m.created_at)}
                </small>
              </div>
            ))}
          </div>
          {human && (
            <div className="sandbox-tip" role="status">
              {tr(
                "An adviser owns this conversation. Automated replies are paused; incoming messages are still recorded.",
              )}
            </div>
          )}
          <label className="checkbox-field">
            <input
              type="checkbox"
              checked={lead ? !!lead.consent : consent}
              disabled={!!lead}
              onChange={(e) => setConsent(e.target.checked)}
            />
            {tr("Customer follow-up opt-in recorded")}
          </label>
          <form className="composer" onSubmit={send}>
            <div>
              <input
                aria-label={tr("WhatsApp sandbox message")}
                required
                maxLength={4000}
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder={tr("Write in Egyptian Arabic or English…")}
              />
              <button
                className="button primary"
                disabled={busy}
                aria-label={tr("Send sandbox message")}
              >
                <Send size={17} />
              </button>
            </div>
          </form>
        </section>
        <aside className="card sandbox-side">
          <span className="eyebrow">{tr("CONVERSATION INTELLIGENCE")}</span>
          <h3 style={{ marginTop: 12 }}>
            {tr("The right context. The right next step.")}
          </h3>
          <dl className="intelligence-details">
            <div>
              <dt>{tr("Intent / النية")}</dt>
              <dd>{localize(intelligence?.intent || "Awaiting inquiry")}</dd>
            </div>
            <div>
              <dt>{tr("Qualification / التأهيل")}</dt>
              <dd>
                {number(intelligence?.score ?? 0)} / {number(100)}
              </dd>
            </div>
            <div>
              <dt>{tr("Adviser / المستشار")}</dt>
              <dd>
                {state.users.find((u: Row) => u.id === lead?.assigned_to)
                  ?.name || tr("Assigned on intake")}
              </dd>
            </div>
            <div>
              <dt>{tr("Next action / التالي")}</dt>
              <dd>
                {localize(intelligence?.next_action || "Start conversation")}
              </dd>
            </div>
          </dl>
          <div className="policy-row">
            <span>{tr("Follow-up consent")}</span>
            <span
              className={
                "pill " +
                (lead?.consent && !lead?.opted_out ? "green" : "orange")
              }
            >
              {localize(
                lead?.opted_out
                  ? "Opted out"
                  : lead?.consent
                    ? "Recorded"
                    : "Not recorded",
              )}
            </span>
          </div>
          <div className="policy-row">
            <span>{tr("24-hour service window")}</span>
            <span className="pill blue">
              {localize(
                intelligence?.service_window_open
                  ? "Open"
                  : "No recent inbound",
              )}
            </span>
          </div>
          <div className="policy-row">
            <span>{tr("Real provider delivery")}</span>
            <span className="pill orange">{tr("Disabled")}</span>
          </div>
          <div className="sandbox-tip">
            {tr(
              "Send “stop” / “متبعتش” to opt out, or “human adviser” / “عايز مستشار” for a persistent handoff. Explicit re-opt-in: “I agree to follow-up” / “موافق على المتابعة”.",
            )}
          </div>
          {lead && (
            <button className="button" disabled={busy} onClick={handoff}>
              <UsersRound size={16} />
              {localize(
                human ? tr("Resume assistant") : tr("Take over conversation"),
              )}
            </button>
          )}
          <h3 style={{ marginTop: 27 }}>
            {tr("Matched to your actual inventory")}
          </h3>
          {intelligence?.recommendations?.map((p: Row) => (
            <div className="mini-property" key={p.id}>
              <strong>
                <Building2 size={12} /> {p.title}
              </strong>
              <small>{money(p.price, state.company.settings.currency)}</small>
              <span>{p.reasons.map(localize).join(" · ")}</span>
              {lead && (
                <button
                  type="button"
                  className="text-button"
                  onClick={() => onBook(lead, p.id)}
                >
                  {tr("Book viewing")}
                  <ArrowUpRight size={14} />
                </button>
              )}
            </div>
          ))}
          {!intelligence?.recommendations?.length && (
            <p className="fine">
              {tr(
                "Only available listings matching recorded preferences are shown.",
              )}
            </p>
          )}
          <p>
            {tr(
              "Explainable qualification. Paid language-model interpretation is optional and disabled in this rehearsal.",
            )}
          </p>
        </aside>
      </div>
    </>
  );
}
