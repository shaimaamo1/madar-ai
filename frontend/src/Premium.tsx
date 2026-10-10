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
import { workflowCatalog } from "./workflowCatalog";

export function OperatingStrip({
  operations,
  ar,
}: {
  operations: Row;
  ar: boolean;
}) {
  return (
    <div className="operating-strip">
      <span>
        <ShieldCheck size={14} />
        <strong>{ar ? "مساحة عمل آمنة" : "Private company workspace"}</strong>
      </span>
      <span>
        <span className="status-dot" />
        {ar ? "سجلات حية من CRM" : "Live CRM records"}
      </span>
      <span>
        <UsersRound size={14} />
        {operations.human_handoffs || 0}{" "}
        {ar ? "طلبات مستشار" : "adviser handoffs"}
      </span>
      <span>
        <MessageSquare size={14} />
        {operations.external_send_enabled
          ? ar
            ? "الإرسال مفعّل من المشغّل"
            : "Operator enabled delivery"
          : ar
            ? "الإرسال الخارجي معطّل"
            : "External delivery disabled"}
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
          <h3>
            {ar ? "إيقاع العملاء الجدد" : "The rhythm of new opportunities"}
          </h3>
          <p>
            {ar
              ? "استفسارات مسجلة خلال آخر ١٤ يومًا"
              : "Recorded inquiries over the last 14 days · UTC"}
          </p>
        </div>
        <span className="pill blue">
          {counts.reduce((a, b) => a + b, 0)} {ar ? "استفسار" : "inquiries"}
        </span>
      </div>
      <div className="trend-chart">
        <svg
          viewBox="0 0 628 172"
          role="img"
          aria-label={
            ar
              ? "العملاء الجدد خلال آخر ١٤ يومًا"
              : "New inquiries over the last fourteen days"
          }
        >
          {[38, 85, 132].map((y, i) => (
            <g key={y}>
              <line className="grid-line" x1="34" y1={y} x2="598" y2={y} />
              <text x="6" y={y + 4}>
                {Math.round(max * (1 - i / 2))}
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
                {days[i]}: {counts[i]} inquiries
              </title>
            </circle>
          ))}
          {[0, 4, 9, 13].map((i) => (
            <text key={i} x={points[i][0]} y="162" textAnchor="middle">
              {days[i].slice(5)}
            </text>
          ))}
        </svg>
        <div className="trend-caption">
          <span>
            {ar
              ? "من السجلات المعروضة في مساحة العمل"
              : "From the workspace records shown · up to 1,000 leads"}
          </span>
          <span>
            {ar ? "بلا توقعات مصطنعة" : "Observed activity, no forecast"}
          </span>
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
            {ar ? "هندسة رحلة العميل" : "The customer journey, orchestrated"}
          </h3>
          <p>
            {ar
              ? "مخططات مولّدة من ملفات n8n الفعلية. جميع الوحدات غير مفعّلة."
              : "Generated from actual n8n JSON. All ten modules are inactive; runtime requires local verification."}
          </p>
        </div>
        <span className="pill orange">
          {ar ? "تشغيل محلي مطلوب" : "Runtime not verified"}
        </span>
      </div>
      <div
        className="workflow-tabs"
        role="tablist"
        aria-label="Workflow modules"
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
                    : event.key === "ArrowRight"
                      ? (index + 1) % workflowCatalog.length
                      : event.key === "ArrowLeft"
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
            {w.name.replace("MADAR ", "")}
          </button>
        ))}
      </div>
      <div
        className="workflow-map"
        id="workflow-diagram"
        role="tabpanel"
        aria-labelledby={"tab-" + key}
      >
        <svg
          viewBox={`75 0 ${width} ${height}`}
          role="img"
          aria-label={flow.name + " actual workflow"}
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
                  x={n.position[0] + 16}
                  y={n.position[1] + 26}
                >
                  {n.note?.split("\n")[0].replace("## ", "")}
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
                    {e.branch === 0 ? "yes" : "no"}
                  </text>
                )}
              </g>
            );
          })}
          {executable.map((n) => (
            <g key={n.id} data-node-id={n.id}>
              <title>{n.name + " · " + n.type}</title>
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
                {n.type === "if"
                  ? "?"
                  : n.type === "code"
                    ? "{}"
                    : n.type === "httpRequest"
                      ? "↗"
                      : "◈"}
              </text>
              <text
                className="node-label"
                x={n.position[0] + 48}
                y={n.position[1] + 29}
              >
                {n.name.length > 24 ? n.name.slice(0, 24) + "…" : n.name}
              </text>
              <text
                className="node-type"
                x={n.position[0] + 14}
                y={n.position[1] + 62}
              >
                {n.type}
              </text>
            </g>
          ))}
        </svg>
      </div>
      <div className="workflow-footer">
        <span>
          <strong>{executable.length} executable nodes</strong> ·{" "}
          {flow.contracts.length} backend contracts · {flow.edges.length} real
          connections
          <br />
          {ar
            ? "موافقة المالك مطلوبة قبل الإرسال الحقيقي"
            : "Owner authorization required before real external delivery"}
        </span>
        <button
          className="text-button"
          onClick={() => download(flow.key + "-architecture.json", flow)}
        >
          {ar ? "تصدير المخطط" : "Export architecture"}
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
        name: ar ? "عميل تجربة واتساب" : "WhatsApp sandbox customer",
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
        <h3>
          {ar
            ? "تجربة آمنة في مساحة منفصلة"
            : "Rehearse in an isolated demo workspace"}
        </h3>
        <p>
          {ar
            ? "سجّل خروجك وافتح التجربة التفاعلية لاختبار واتساب دون التأثير على بيانات العملاء."
            : "Sign out and open the interactive demo to test WhatsApp without affecting customer data."}
        </p>
      </section>
    );
  return (
    <>
      <div className="connection-note">
        <ShieldCheck size={19} />
        <p>
          {ar
            ? "تجربة محلية آمنة. لا يتم الاتصال بـMeta أو إرسال رسائل أو استخدام نموذج مدفوع."
            : "Provider-free rehearsal. Messages update the fictional CRM; no Meta request, real delivery, or paid inference occurs."}
        </p>
      </div>
      {error && (
        <div className="alert" role="alert">
          {error}
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
              <h3>{ar ? "استوديو مبيعات واتساب" : "WhatsApp sales studio"}</h3>
              <p>
                {ar
                  ? "من أول استفسار إلى مستشار عقاري"
                  : "From first inquiry to a personal property adviser"}
              </p>
            </div>
            <span className="pill green">{ar ? "تجريبي" : "Sandbox"}</span>
          </div>
          <div className="sandbox-controls">
            <label className="field">
              {ar ? "العميل التجريبي" : "Sandbox conversation"}
              <select
                aria-label="Sandbox conversation"
                value={contact}
                onChange={(e) => setContact(e.target.value)}
              >
                {!lead && (
                  <option value={contact}>
                    {ar ? "محادثة جديدة" : "New conversation"}
                  </option>
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
              {ar ? "جديد" : "New conversation"}
            </button>
          </div>
          <div className="message-list" aria-live="polite">
            {!messages.length && (
              <div className="empty">
                <Sparkles size={29} />
                <h3>
                  {ar
                    ? "مستشارك العقاري جاهز"
                    : "A thoughtful adviser. A real inventory."}
                </h3>
                <p>
                  {ar
                    ? "جرّب: عايز شقة في التجمع، ميزانيتي ٥ مليون و٣ غرف"
                    : "Try: New Cairo apartment, budget 5 million, 3 bedrooms."}
                </p>
              </div>
            )}
            {messages.map((m: Row) => (
              <div key={m.id} className={"message " + m.direction}>
                <p dir="auto">{m.body}</p>
                <small>
                  {m.direction === "inbound" ? "Customer" : "MADAR"} ·{" "}
                  {date(m.created_at)}
                </small>
              </div>
            ))}
          </div>
          {human && (
            <div className="sandbox-tip" role="status">
              {ar
                ? "المستشار يدير المحادثة الآن. تم إيقاف الردود الآلية."
                : "An adviser owns this conversation. Automated replies are paused; incoming messages are still recorded."}
            </div>
          )}
          <label className="checkbox-field">
            <input
              type="checkbox"
              checked={lead ? !!lead.consent : consent}
              disabled={!!lead}
              onChange={(e) => setConsent(e.target.checked)}
            />
            {ar
              ? "موافقة العميل على المتابعة مسجلة"
              : "Customer follow-up opt-in recorded"}
          </label>
          <form className="composer" onSubmit={send}>
            <div>
              <input
                aria-label="WhatsApp sandbox message"
                required
                maxLength={4000}
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder={
                  ar
                    ? "اكتب رسالة بالعربي أو الإنجليزي…"
                    : "Write in Egyptian Arabic or English…"
                }
              />
              <button
                className="button primary"
                disabled={busy}
                aria-label="Send sandbox message"
              >
                <Send size={17} />
              </button>
            </div>
          </form>
        </section>
        <aside className="card sandbox-side">
          <span className="eyebrow">
            {ar ? "ذكاء المحادثة" : "CONVERSATION INTELLIGENCE"}
          </span>
          <h3 style={{ marginTop: 12 }}>
            {ar
              ? "السياق الصحيح. الخطوة الصحيحة."
              : "The right context. The right next step."}
          </h3>
          <dl className="intelligence-details">
            <div>
              <dt>Intent / النية</dt>
              <dd>{intelligence?.intent || "Awaiting inquiry"}</dd>
            </div>
            <div>
              <dt>Qualification / التأهيل</dt>
              <dd>{intelligence?.score ?? 0} / 100</dd>
            </div>
            <div>
              <dt>Adviser / المستشار</dt>
              <dd>
                {state.users.find((u: Row) => u.id === lead?.assigned_to)
                  ?.name || "Assigned on intake"}
              </dd>
            </div>
            <div>
              <dt>Next action / التالي</dt>
              <dd>
                {intelligence?.next_action?.replaceAll("_", " ") ||
                  "Start conversation"}
              </dd>
            </div>
          </dl>
          <div className="policy-row">
            <span>{ar ? "موافقة المتابعة" : "Follow-up consent"}</span>
            <span
              className={
                "pill " +
                (lead?.consent && !lead?.opted_out ? "green" : "orange")
              }
            >
              {lead?.opted_out
                ? "Opted out"
                : lead?.consent
                  ? "Recorded"
                  : "Not recorded"}
            </span>
          </div>
          <div className="policy-row">
            <span>{ar ? "نافذة ٢٤ ساعة" : "24-hour service window"}</span>
            <span className="pill blue">
              {intelligence?.service_window_open ? "Open" : "No recent inbound"}
            </span>
          </div>
          <div className="policy-row">
            <span>{ar ? "إرسال حقيقي" : "Real provider delivery"}</span>
            <span className="pill orange">Disabled</span>
          </div>
          <div className="sandbox-tip">
            {ar
              ? "اكتب «متبعتش» لإيقاف المتابعة، أو «عايز مستشار» للتحويل البشري."
              : "Send “stop” / “متبعتش” to opt out, or “human adviser” / “عايز مستشار” for a persistent handoff. Explicit re-opt-in: “I agree to follow-up” / “موافق على المتابعة”."}
          </div>
          {lead && (
            <button className="button" disabled={busy} onClick={handoff}>
              <UsersRound size={16} />
              {human
                ? ar
                  ? "إعادة المساعد"
                  : "Resume assistant"
                : ar
                  ? "تولي المستشار"
                  : "Take over conversation"}
            </button>
          )}
          <h3 style={{ marginTop: 27 }}>
            {ar ? "توصيات من المخزون" : "Matched to your actual inventory"}
          </h3>
          {intelligence?.recommendations?.map((p: Row) => (
            <div className="mini-property" key={p.id}>
              <strong>
                <Building2 size={12} /> {p.title}
              </strong>
              <small>{money(p.price, state.company.settings.currency)}</small>
              <span>{p.reasons.join(" · ")}</span>
              {lead && (
                <button
                  type="button"
                  className="text-button"
                  onClick={() => onBook(lead, p.id)}
                >
                  {ar ? "احجز معاينة" : "Book viewing"}
                  <ArrowUpRight size={14} />
                </button>
              )}
            </div>
          ))}
          {!intelligence?.recommendations?.length && (
            <p className="fine">
              {ar
                ? "يتم عرض العقارات المتاحة المطابقة فقط."
                : "Only available listings matching recorded preferences are shown."}
            </p>
          )}
          <p>
            {ar
              ? "التأهيل بقواعد واضحة. النموذج المدفوع اختياري."
              : "Explainable qualification. Paid language-model interpretation is optional and disabled in this rehearsal."}
          </p>
        </aside>
      </div>
    </>
  );
}
