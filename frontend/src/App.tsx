import { useEffect, useRef, useState, FormEvent } from "react";
import {
  Activity,
  ArrowDownToLine,
  ArrowRight,
  ArrowUpRight,
  Bell,
  Building2,
  CalendarDays,
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  CircleHelp,
  CircleUserRound,
  Clock3,
  Command,
  Globe2,
  LayoutDashboard,
  LogOut,
  Menu,
  MessageSquare,
  Moon,
  MoreHorizontal,
  Plus,
  Search,
  Settings2,
  ShieldCheck,
  Sparkles,
  Sun,
  Target,
  TrendingUp,
  UsersRound,
  Workflow,
  X,
  Zap,
  Plug,
  BarChart3,
  Send,
  RefreshCw,
} from "lucide-react";
import { api, Row, money, date, download } from "./api";
import {
  tr,
  localize,
  number,
  percent,
  errorText,
  auditDetail,
  useLanguage,
  setTimezone,
} from "./i18n";
import { LanguageSelector } from "./LanguageSelector";
import {
  ActivityTrend,
  OperatingStrip,
  WhatsAppStudio,
  WorkflowStudio,
} from "./Premium";

const pages = [
  ["overview", "Overview", LayoutDashboard, "نظرة عامة"],
  ["leads", "Leads & CRM", UsersRound, "العملاء وإدارة المبيعات"],
  ["whatsapp", "WhatsApp studio", MessageSquare, "استوديو واتساب"],
  ["properties", "Property inventory", Building2, "العقارات"],
  ["inbox", "Unified inbox", MessageSquare, "صندوق الرسائل"],
  ["appointments", "Appointments", CalendarDays, "المواعيد"],
  ["tasks", "Follow-up tasks", CheckCircle2, "مهام المتابعة"],
  ["analytics", "Analytics", BarChart3, "التحليلات"],
  ["agents", "Sales team", CircleUserRound, "فريق المبيعات"],
  ["assistant", "Sales intelligence", Sparkles, "ذكاء المبيعات"],
  ["automation", "Automations", Workflow, "الأتمتة"],
  ["integrations", "Integrations", Plug, "التكاملات"],
  ["settings", "Company settings", Settings2, "إعدادات الشركة"],
] as const;
const stageColors: Record<string, string> = {
  New: "blue",
  Qualified: "green",
  Viewing: "purple",
  Negotiation: "orange",
  Won: "green",
  Lost: "gray",
};
const emptyLead = {
  name: "",
  email: "",
  phone: "",
  source: "website",
  budget: 0,
  location: "",
  property_type: "Apartment",
  bedrooms: 0,
  intent: "buy",
  consent: false,
};
const emptyProperty = {
  title: "",
  location: "",
  price: 0,
  size: 0,
  bedrooms: 2,
  property_type: "Apartment",
  intent: "buy",
  status: "Available",
  amenities: [],
  description: "",
  image: "",
};

function Brand({ small = false }: { small?: boolean }) {
  return (
    <div className={"brand " + (small ? "small" : "")}>
      <span className="brand-mark">
        <Building2 size={23} />
      </span>
      <span>
        MADAR<span className="brand-ai">AI</span>
        <small>{tr("REAL ESTATE OPERATING SYSTEM")}</small>
      </span>
    </div>
  );
}
function Avatar({ name, index = 0 }: { name: string; index?: number }) {
  return (
    <span className={"avatar tone-" + (index % 4)}>
      {name
        .split(" ")
        .map((n) => n[0])
        .slice(0, 2)
        .join("")}
    </span>
  );
}
function Pill({ value }: { value: string }) {
  return (
    <span
      className={
        "pill " +
        (stageColors[value] ||
          (value === "Available" ||
          value === "Operational" ||
          value === "Completed"
            ? "green"
            : "gray"))
      }
    >
      {localize(value)}
    </span>
  );
}
function PropertyArt({ variant = 0 }: { variant?: number }) {
  const colors = [
    ["#e7dacc", "#a8937e", "#65584c"],
    ["#d7e3de", "#9fb6a7", "#5d7369"],
    ["#dddfe8", "#acaac0", "#656780"],
  ][variant % 3];
  return (
    <svg
      viewBox="0 0 500 240"
      className="property-art"
      aria-label={tr("Architectural illustration")}
    >
      <defs>
        <linearGradient id={"sky" + variant} x2="0" y2="1">
          <stop stopColor={colors[0]} />
          <stop offset="1" stopColor="#f4ede0" />
        </linearGradient>
      </defs>
      <rect width="500" height="240" fill={"url(#sky" + variant + ")"} />
      <circle cx="412" cy="58" r="29" fill="#fdf6d9" />
      <path d="M0 207L500 182V240H0Z" fill={colors[1]} />
      <path d="M74 87L251 48L416 77V220H74Z" fill={colors[0]} />
      <path d="M251 48L416 77V220L251 208Z" fill={colors[1]} />
      <path d="M60 90L249 46L431 76L416 88L251 61L75 102Z" fill={colors[2]} />
      {[0, 1, 2, 3].map((i) => (
        <g key={i}>
          <rect
            x={95 + i * 37}
            y="114"
            width="23"
            height="41"
            fill={colors[2]}
          />
          <rect
            x={95 + i * 37}
            y="171"
            width="23"
            height="38"
            fill={colors[2]}
          />
          <path d={`M${280 + i * 30} 110l20 4v42l-20-3Z`} fill={colors[2]} />
        </g>
      ))}
      <rect x="70" y="160" width="190" height="7" fill="#f5f1e8" />
      <path
        d="M26 232V144M14 164Q25 121 42 135M26 166Q60 132 66 151"
        stroke={colors[2]}
        strokeWidth="7"
        fill="none"
      />
      <path
        d="M451 220V119M435 140Q455 91 473 117M450 145Q487 115 491 133"
        stroke={colors[2]}
        strokeWidth="8"
        fill="none"
      />
    </svg>
  );
}

export default function App() {
  const [state, setState] = useState<Row | null>(null),
    [metrics, setMetrics] = useState<Row>({}),
    [operations, setOperations] = useState<Row>({}),
    [loading, setLoading] = useState(true),
    [demoEnabled, setDemoEnabled] = useState(false);
  const [page, setPage] = useState("overview"),
    [search, setSearch] = useState(""),
    [theme, setTheme] = useState(
      localStorage.getItem("madar-theme") || "light",
    );
  const { ar } = useLanguage();
  const [mobile, setMobile] = useState(false),
    [error, setError] = useState(""),
    [notice, setNotice] = useState("");
  const [modal, setModal] = useState(""),
    [form, setForm] = useState<Row>({}),
    [busy, setBusy] = useState(false),
    [selectedLead, setSelectedLead] = useState(""),
    [matches, setMatches] = useState<Row[]>([]);
  const [chatText, setChatText] = useState(""),
    [chatMode, setChatMode] = useState("assistant"),
    [stage, setStage] = useState("All"),
    [compare, setCompare] = useState<string[]>([]);
  const [roi, setRoi] = useState({
    leads: 100,
    uplift: 2,
    commission: 25000,
    monthly: 2500,
  });
  const chatBottom = useRef<HTMLDivElement>(null);
  const refresh = async () => {
    const [s, m, o] = await Promise.all([
      api("/state"),
      api("/analytics"),
      api("/operations"),
    ]);
    setState(s);
    setMetrics(m);
    setOperations(o);
    return s;
  };
  useEffect(() => {
    api("/public/runtime")
      .then((r) => setDemoEnabled(r.demo_enabled))
      .catch(() => {});
    refresh()
      .catch(() => setState(null))
      .finally(() => setLoading(false));
  }, []);
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("madar-theme", theme);
  }, [theme]);
  useEffect(() => {
    let current = true;
    if (selectedLead && state)
      api("/leads/" + selectedLead + "/matches")
        .then((value) => {
          if (current) setMatches(value);
        })
        .catch(() => {
          if (current) setMatches([]);
        });
    return () => {
      current = false;
    };
  }, [selectedLead, state]);
  useEffect(() => {
    chatBottom.current?.scrollIntoView({
      behavior: "smooth",
      block: "nearest",
    });
  }, [state, selectedLead]);
  useEffect(() => {
    if (notice) {
      const timeout = setTimeout(() => setNotice(""), 5000);
      return () => clearTimeout(timeout);
    }
  }, [notice]);
  useEffect(() => {
    if (!modal) return;
    const previous = document.activeElement as HTMLElement | null;
    const dialog = document.querySelector<HTMLElement>('[role="dialog"]');
    const focusable = () =>
      Array.from(
        dialog?.querySelectorAll<HTMLElement>(
          "button:not(:disabled),input:not(:disabled),select:not(:disabled),textarea:not(:disabled),a[href]",
        ) || [],
      );
    focusable()[0]?.focus();
    const trap = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setModal("");
        return;
      }
      if (event.key !== "Tab") return;
      const controls = focusable(),
        first = controls[0],
        last = controls[controls.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last?.focus();
      }
      if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first?.focus();
      }
    };
    document.addEventListener("keydown", trap);
    return () => {
      document.removeEventListener("keydown", trap);
      previous?.focus();
    };
  }, [modal]);
  const run = async (
    action: () => Promise<unknown>,
    message = "Saved successfully",
  ) => {
    setBusy(true);
    setError("");
    try {
      await action();
      await refresh();
      setNotice(message);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  const open = (kind: string, values: Row = {}) => {
    setModal(kind);
    setForm(values);
    setError("");
  };
  const navigate = (next: string) => {
    setPage(next);
    setSearch("");
    setMobile(false);
    setError("");
  };
  const update = (key: string, value: unknown) =>
    setForm((prev) => ({ ...prev, [key]: value }));
  const cfg = state?.company.settings || {},
    currency = cfg.currency || "EGP";
  setTimezone(cfg.timezone || "Africa/Cairo");
  const findLead = (id: string) => state?.leads.find((l: Row) => l.id === id);
  const findProp = (id: string) =>
    state?.properties.find((p: Row) => p.id === id);
  const leadName = (id: string) => findLead(id)?.name || tr("Unknown customer");
  const filtered = (rows: Row[], keys: string[]) =>
    rows.filter(
      (r) =>
        !search ||
        keys.some((k) =>
          String(r[k]).toLowerCase().includes(search.toLowerCase()),
        ),
    );
  const followups =
    state?.tasks.filter((r: Row) => r.status === "Pending") || [];
  const selected = state?.leads.find((l: Row) => l.id === selectedLead);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      if (modal === "lead") await api("/leads", "POST", form);
      if (modal === "property") {
        const { id, tenant_id, created_at, ...data } = form;
        data.amenities = data.amenities
          .map((a: string) => a.trim())
          .filter(Boolean);
        await api(
          "/properties" + (id ? "/" + id : ""),
          id ? "PATCH" : "POST",
          data,
        );
      }
      if (modal === "appointment") {
        const { id, ...data } = form;
        await api("/appointments" + (id ? "/" + id : ""), id ? "PUT" : "POST", {
          ...data,
          start_at: new Date(data.start_at).toISOString(),
        });
      }
      if (modal === "task")
        await api("/tasks", "POST", {
          ...form,
          due_at: new Date(form.due_at).toISOString(),
        });
      if (modal === "deal")
        await api("/deals", "POST", {
          ...form,
          property_id: form.property_id || null,
        });
      if (modal === "user") await api("/users", "POST", form);
      if (modal === "workspace") await api("/workspaces", "POST", form);
      if (modal === "password") await api("/auth/password", "POST", form);
      if (modal === "preferences")
        await api("/leads/" + selectedLead, "PATCH", form);
      if (modal === "template") {
        const { parameter_values, ...payload } = form;
        await api("/integrations/whatsapp/template", "POST", {
          ...payload,
          parameters: parameter_values
            ? parameter_values.split("|").map((s: string) => s.trim())
            : [],
        });
      }
      await refresh();
      setModal("");
      setNotice("Saved successfully");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function sendChat(e: FormEvent) {
    e.preventDefault();
    if (!selectedLead || !chatText.trim()) return;
    await run(
      async () => {
        await api(
          "/leads/" +
            selectedLead +
            (chatMode === "assistant" ? "/chat" : "/reply"),
          "POST",
          { text: chatText },
        );
        setChatText("");
      },
      chatMode === "assistant"
        ? "Qualification and recommendations updated"
        : "Reply saved; external delivery gate applies",
    );
  }

  const field = (
    label: string,
    key: string,
    type = "text",
    required = false,
  ) => (
    <label className="field" key={key}>
      {localize(label)}
      <input
        name={key}
        type={type}
        aria-label={localize(label)}
        required={required}
        min={type === "number" ? 0 : undefined}
        value={form[key] ?? ""}
        onChange={(e) =>
          update(
            key,
            type === "number" ? Number(e.target.value) : e.target.value,
          )
        }
      />
    </label>
  );
  const select = (
    label: string,
    key: string,
    options: Array<string | Row>,
    required = true,
  ) => (
    <label className="field" key={key}>
      {localize(label)}
      <select
        aria-label={localize(label)}
        name={key}
        value={form[key] ?? ""}
        required={required}
        onChange={(e) => update(key, e.target.value)}
      >
        <option value="">{tr("Choose…")}</option>
        {options.map((o) =>
          typeof o === "string" ? (
            <option key={o} value={o}>
              {localize(o)}
            </option>
          ) : (
            <option key={o.id} value={o.id}>
              {o.name || o.title}
            </option>
          ),
        )}
      </select>
    </label>
  );

  if (window.location.pathname === "/chat") return <PublicChatPage />;
  if (loading)
    return (
      <div className="loading">
        <Brand />
        <p>{tr("Opening your workspace…")}</p>
      </div>
    );
  if (!state)
    return (
      <div className="login-screen">
        <div className="login-story">
          <Brand />
          <div>
            <span className="eyebrow">
              {tr("THE NEXT CHAPTER OF REAL ESTATE")}
            </span>
            <h1>
              {tr("Every inquiry.")}
              <br />
              {tr("Every opportunity.")}
              <br />
              <em>{tr("One intelligent workspace.")}</em>
            </h1>
            <p>
              {tr("Your people, properties, and conversations — connected.")}
            </p>
          </div>
          <small>{tr("BUILT FOR AMBITION. DESIGNED FOR YOUR TEAM.")}</small>
        </div>
        <div className="login-panel">
          <LanguageSelector />
          <span className="eyebrow">{tr("WELCOME TO MADAR")}</span>
          <h2>{tr("Good business starts here.")}</h2>
          <p>{tr("Sign in to your company workspace.")}</p>
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              await run(() => api("/auth/login", "POST", form), "Welcome back");
            }}
          >
            {field("Workspace", "workspace", "text", true)}
            {field("Email", "email", "email", true)}
            {field("Password", "password", "password", true)}
            <button className="button primary" disabled={busy}>
              {tr("Sign in")} <ArrowRight size={17} />
            </button>
          </form>
          {demoEnabled && (
            <>
              <div className="divider">{tr("or explore the product")}</div>
              <button
                className="button demo-button"
                disabled={busy}
                onClick={() =>
                  run(
                    () => api("/auth/demo", "POST"),
                    "Your private demo workspace is ready",
                  )
                }
              >
                <Sparkles size={18} /> {tr("Open interactive demo")}{" "}
                <ArrowUpRight size={17} />
              </button>
              <p className="fine">
                {tr(
                  "Fictional data. Real workflows. Your demo workspace is isolated.",
                )}
              </p>
            </>
          )}
          {error && (
            <div className="alert" role="alert">
              {errorText(error)}
            </div>
          )}
        </div>
      </div>
    );

  const pageInfo = pages.find((p) => p[0] === page)!;
  const newBooking = (lead?: Row) =>
    open("appointment", {
      lead_id: lead?.id || "",
      property_id: "",
      agent_id: lead?.assigned_to || state.users[0]?.id || "",
      start_at: "",
      notes: "",
    });
  return (
    <div
      className="shell"
      style={
        {
          "--company-accent":
            cfg.brand_color?.toLowerCase() === "#b6ee6a"
              ? "#D8BE83"
              : cfg.brand_color,
        } as React.CSSProperties
      }
    >
      <a className="skip-link" href="#workspace-content">
        {tr("Skip to workspace")}
      </a>
      <aside
        id="workspace-navigation"
        aria-label={tr("Main navigation")}
        className={"sidebar " + (mobile ? "expanded" : "")}
      >
        {cfg.logo_url ? (
          <div className="custom-brand">
            <img src={cfg.logo_url} alt={cfg.company_name + " logo"} />
            <strong>{cfg.company_name}</strong>
          </div>
        ) : (
          <Brand />
        )}
        <button
          className="workspace-switch"
          onClick={() => navigate("settings")}
        >
          <span className="workspace-icon">
            {localize(state.company.name[0])}
          </span>
          <span>
            {state.company.name}
            <small>
              {localize(
                state.company.demo
                  ? "Demonstration workspace"
                  : "Company workspace",
              )}
            </small>
          </span>
          <ChevronDown size={14} />
        </button>
        <span className="nav-label">{tr("WORKSPACE")}</span>
        <nav aria-label={tr("Workspace pages")}>
          {pages.map(([key, label, Icon]) => (
            <button
              key={key}
              aria-label={tr(label)}
              aria-current={page === key ? "page" : undefined}
              className={page === key ? "active" : ""}
              onClick={() => navigate(key)}
            >
              <Icon size={19} />
              <span>{tr(label)}</span>
              {key === "inbox" && (
                <span className="nav-count">
                  {number(
                    state.leads.filter((l: Row) => l.stage === "New").length,
                  )}
                </span>
              )}
              {key === "assistant" && (
                <small className="new-tag">{tr("AI")}</small>
              )}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="system-health">
            <span className="status-dot" />
            <span>
              {tr("Core system operational")}
              <small>{tr("External channels need authorization")}</small>
            </span>
          </div>
          <button className="profile-button" onClick={() => navigate("agents")}>
            <Avatar name={state.user.name} />
            <span>
              {state.user.name}
              <small>
                {localize(
                  state.user.role === "admin"
                    ? "Workspace administrator"
                    : "Sales agent",
                )}
              </small>
            </span>
            <ChevronRight size={15} />
          </button>
          <button
            className="logout"
            onClick={async () => {
              await api("/auth/logout", "POST");
              setState(null);
              setForm({});
            }}
          >
            <LogOut size={15} />
            {tr("Sign out")}
          </button>
        </div>
      </aside>
      <main className="main">
        <header className="topbar">
          <div className="breadcrumb">
            <button
              className="icon-button mobile-menu"
              aria-label={tr("Open navigation")}
              aria-expanded={mobile}
              aria-controls="workspace-navigation"
              onClick={() => setMobile(!mobile)}
            >
              <Menu size={20} />
            </button>
            {tr("Workspace")}
            <ChevronRight size={14} />
            <strong>{tr(pageInfo[1])}</strong>
          </div>
          <div className="topbar-actions">
            <LanguageSelector />
            <button
              className="icon-button"
              aria-label={tr("Toggle theme")}
              onClick={() => setTheme(theme === "light" ? "dark" : "light")}
            >
              {theme === "light" ? <Moon size={18} /> : <Sun size={18} />}
            </button>
            <button
              className="icon-button notification"
              aria-label={tr("Open pending tasks")}
              onClick={() => navigate("tasks")}
            >
              <Bell size={19} />
              {followups.length > 0 && <span />}
            </button>
            <Avatar name={state.user.name} />
          </div>
        </header>
        <div className="content" id="workspace-content" tabIndex={-1}>
          {state.company.demo && (
            <div className="demo-banner">
              <span>
                <Sparkles size={14} />
                {tr("DEMO WORKSPACE")}
                <b>·</b>
                {tr(
                  "All properties, customers, and financial records are fictional.",
                )}
              </span>
              <button onClick={() => open("reset")}>
                {tr("Reset demo")}
                <RefreshCw size={12} />
              </button>
            </div>
          )}
          <div className="page-heading">
            <div>
              <div className="eyebrow">{tr("YOUR BUSINESS, CONNECTED")}</div>
              <h1>
                {localize(
                  page === "overview"
                    ? tr("A clearer view. A smarter business.")
                    : tr(pageInfo[1]),
                )}
              </h1>
              <p>
                {localize(
                  page === "overview"
                    ? tr(
                        "Turn conversations into relationships. Turn opportunities into growth.",
                      )
                    : tr(
                        "One connected workspace. Every action updates your business records.",
                      ),
                )}
              </p>
            </div>
            <div className="heading-actions">
              <button
                className="button"
                disabled={busy}
                onClick={() =>
                  run(
                    async () =>
                      download(
                        "madar-management-report.json",
                        await api("/report"),
                      ),
                    "Management report downloaded",
                  )
                }
              >
                <ArrowDownToLine size={16} />
                {tr("Export report")}
              </button>
              <button
                className="button primary"
                onClick={() => open("lead", emptyLead)}
              >
                <Plus size={17} />
                {tr("New lead")}
              </button>
            </div>
          </div>
          {error && (
            <div className="alert" role="alert">
              <span>{errorText(error)}</span>
              <button
                aria-label={tr("Dismiss error")}
                onClick={() => setError("")}
              >
                <X size={15} />
              </button>
            </div>
          )}

          <OperatingStrip operations={operations} ar={ar} />
          {page === "whatsapp" && (
            <WhatsAppStudio
              state={state}
              onUpdated={refresh}
              ar={ar}
              onBook={(lead, propertyId) =>
                open("appointment", {
                  lead_id: lead.id,
                  property_id: propertyId,
                  agent_id: lead.assigned_to,
                  start_at: "",
                  notes: "WhatsApp sandbox viewing",
                })
              }
            />
          )}
          {page === "overview" && (
            <>
              <div className="overview-grid">
                <section className="hero-card">
                  <div>
                    <span className="hero-label">
                      <span className="status-dot" />
                      {tr("YOUR NEXT OPPORTUNITY STARTS HERE")}
                    </span>
                    <h2>
                      {tr("Stay one step ahead.")}
                      <br />
                      <span>{tr("Let every lead count.")}</span>
                    </h2>
                    <p>
                      {localize(
                        metrics.missed_opportunities
                          ? `${metrics.missed_opportunities} lead needs attention. Your sales intelligence has a plan.`
                          : "Your sales intelligence is ready. Find the next action for every customer.",
                      )}
                    </p>
                    <button
                      className="hero-link"
                      onClick={() => navigate("assistant")}
                    >
                      {tr("Explore sales intelligence")}
                      <ArrowUpRight size={17} />
                    </button>
                  </div>
                  <div className="orbit-art" aria-hidden="true">
                    <div className="orbit o1" />
                    <div className="orbit o2" />
                    <div className="orbit o3" />
                    <div className="orbit-center">
                      <Sparkles size={40} />
                    </div>
                    <span className="orbit-node n1">
                      <UsersRound />
                    </span>
                    <span className="orbit-node n2">
                      <Building2 />
                    </span>
                    <span className="orbit-node n3">
                      <MessageSquare />
                    </span>
                    <div className="orbit-caption">
                      <Zap size={13} />
                      {tr("CONNECTED INTELLIGENCE")}
                    </div>
                  </div>
                </section>
                <section className="card day-card">
                  <div className="card-head">
                    <h3>{tr("On your radar")}</h3>
                    <CalendarDays size={19} />
                  </div>
                  <div className="radar-number">
                    {number(followups.length)}
                    <span>{tr("open follow-up tasks")}</span>
                  </div>
                  <p>{tr("Small actions. Meaningful momentum.")}</p>
                  <button className="button" onClick={() => navigate("tasks")}>
                    {tr("View your tasks")}
                    <ArrowRight size={16} />
                  </button>
                  <div className="radar-footer">
                    <span className="status-dot" />
                    {number(metrics.appointments)} {tr("recorded appointments")}
                  </div>
                </section>
              </div>
              <div className="stats-grid">
                {[
                  [
                    UsersRound,
                    "Total leads",
                    metrics.total_leads,
                    "From every connected source",
                    "إجمالي العملاء",
                  ],
                  [
                    Target,
                    "Qualified leads",
                    metrics.qualified,
                    "Qualification score of 65+",
                    "العملاء المؤهلون",
                  ],
                  [
                    TrendingUp,
                    "Lead conversion",
                    percent(metrics.conversion_rate),
                    "Won customers / total leads",
                    "معدل التحويل",
                  ],
                  [
                    Building2,
                    "Commission revenue",
                    money(metrics.revenue || 0, currency),
                    "From recorded won deals",
                    "إيراد العمولة",
                  ],
                ].map(([Icon, label, value, note], i) => {
                  const MetricIcon = Icon as typeof UsersRound;
                  return (
                    <section className="card stat" key={i}>
                      <div>
                        <span>{tr(String(label))}</span>
                        <MetricIcon size={18} />
                      </div>
                      <strong>{localize(String(value ?? 0))}</strong>
                      <small>{localize(String(note))}</small>
                    </section>
                  );
                })}
              </div>
              <div className="section-gap" style={{ marginBottom: 24 }}>
                <ActivityTrend leads={state.leads} ar={ar} />
              </div>
              <div className="two-col">
                <section className="card pipeline-card">
                  <div className="card-head">
                    <div>
                      <h3>{tr("Your sales pipeline")}</h3>
                      <p>{tr("From first hello to the next chapter.")}</p>
                    </div>
                    <button
                      className="text-button"
                      onClick={() => navigate("leads")}
                    >
                      {tr("View CRM")}
                      <ArrowUpRight size={14} />
                    </button>
                  </div>
                  <div className="pipeline-bars">
                    {Object.entries(metrics.pipeline || {}).map(
                      ([label, value], i) => (
                        <button
                          key={label}
                          onClick={() => {
                            setStage(label);
                            navigate("leads");
                          }}
                        >
                          <span className="bar-space">
                            <span
                              className={"bar bar-" + i}
                              style={{
                                height:
                                  Math.max(
                                    12,
                                    (Number(value) /
                                      Math.max(
                                        ...Object.values(metrics.pipeline).map(
                                          Number,
                                        ),
                                        1,
                                      )) *
                                      100,
                                  ) + "%",
                              }}
                            >
                              <b>{localize(String(value))}</b>
                            </span>
                          </span>
                          <small>{localize(label)}</small>
                        </button>
                      ),
                    )}
                  </div>
                  <div className="chart-footer">
                    <span>
                      {number(state.leads.length)} {tr("total customers")}
                    </span>
                    <span>
                      <span className="status-dot" />
                      {tr("Computed from CRM records")}
                    </span>
                  </div>
                </section>
                <section className="card attention-card">
                  <div className="card-head">
                    <div>
                      <h3>
                        <Sparkles size={17} />
                        {tr("A little intelligence goes a long way")}
                      </h3>
                      <p>{tr("Actions grounded in your actual CRM data.")}</p>
                    </div>
                  </div>
                  {state.insights.slice(0, 3).map((insight: Row, i: number) => (
                    <button
                      className="insight-row"
                      key={i}
                      onClick={() => {
                        setSelectedLead(insight.lead_id);
                        navigate("inbox");
                      }}
                    >
                      <span
                        className={
                          "insight-icon " +
                          (insight.type === "Leakage" ? "orange" : "green")
                        }
                      >
                        <Zap size={17} />
                      </span>
                      <span>
                        <strong>{insight.name}</strong>
                        <small>{localize(insight.action)}</small>
                      </span>
                      <ArrowUpRight size={16} />
                    </button>
                  ))}
                  <button
                    className="text-button insight-more"
                    onClick={() => navigate("assistant")}
                  >
                    {tr("See all recommendations")}
                    <ArrowRight size={15} />
                  </button>
                </section>
              </div>
              <section className="card">
                <div className="card-head">
                  <div>
                    <h3>{tr("Latest opportunities")}</h3>
                    <p>{tr("Meet the people behind your pipeline.")}</p>
                  </div>
                  <button
                    className="text-button"
                    onClick={() => navigate("leads")}
                  >
                    {tr("View all leads")}
                    <ArrowUpRight size={14} />
                  </button>
                </div>
                {leadTable(state.leads.slice(0, 5))}
              </section>
            </>
          )}

          {page === "leads" && (
            <>
              <div className="toolbar">
                <div className="tabs">
                  {["All", ...cfg.stages].map((s: string) => (
                    <button
                      key={s}
                      className={stage === s ? "selected" : ""}
                      onClick={() => setStage(s)}
                    >
                      {localize(s)}
                      <span>
                        {localize(
                          s === "All"
                            ? state.leads.length
                            : state.leads.filter((l: Row) => l.stage === s)
                                .length,
                        )}
                      </span>
                    </button>
                  ))}
                </div>
              </div>
              <div className="toolbar">
                <label className="search">
                  <Search size={17} />
                  <input
                    placeholder={tr("Search customers, locations, sources…")}
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                  />
                </label>
                <button
                  className="button"
                  onClick={() =>
                    open("deal", {
                      lead_id: "",
                      property_id: "",
                      amount: 0,
                      commission: 0,
                      status: "Open",
                      lost_reason: "",
                    })
                  }
                >
                  <TrendingUp size={16} />
                  {tr("Record deal")}
                </button>
              </div>
              <section className="card">
                {leadTable(
                  filtered(state.leads, [
                    "name",
                    "location",
                    "source",
                    "email",
                  ]).filter((l) => stage === "All" || l.stage === stage),
                )}
              </section>
              <section className="card section-gap">
                <div className="card-head">
                  <h3>{tr("Recorded deals")}</h3>
                  <span className="muted">
                    {tr("Revenue uses won commissions only")}
                  </span>
                </div>
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>{tr("Customer")}</th>
                        <th>{tr("Deal value")}</th>
                        <th>{tr("Commission")}</th>
                        <th>{tr("Status")}</th>
                        <th>{tr("Lost reason")}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {state.deals.map((d: Row) => (
                        <tr key={d.id}>
                          <td>{leadName(d.lead_id)}</td>
                          <td>{money(d.amount, currency)}</td>
                          <td>{money(d.commission, currency)}</td>
                          <td>
                            <Pill value={d.status} />
                          </td>
                          <td>{d.lost_reason || "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
            </>
          )}

          {page === "properties" && (
            <>
              <div className="toolbar">
                <label className="search">
                  <Search size={17} />
                  <input
                    placeholder={tr("Search inventory…")}
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                  />
                </label>
                <div className="heading-actions">
                  <button
                    className="button"
                    disabled={compare.length < 2}
                    onClick={() => open("compare")}
                  >
                    {tr("Compare (")}
                    {number(compare.length)})
                  </button>
                  {state.user.role === "admin" && (
                    <button
                      className="button primary"
                      onClick={() => open("property", emptyProperty)}
                    >
                      <Plus size={16} />
                      {tr("Add property")}
                    </button>
                  )}
                </div>
              </div>
              <div className="property-grid">
                {filtered(state.properties, [
                  "title",
                  "location",
                  "property_type",
                ]).map((p, i) => (
                  <article className="card property-card" key={p.id}>
                    <div className="property-image">
                      {p.image ? (
                        <img src={p.image} alt={p.title} />
                      ) : (
                        <PropertyArt variant={i} />
                      )}
                      <Pill value={p.status} />
                      <label className="compare-check">
                        <input
                          type="checkbox"
                          aria-label={tr("Compare {name}", { name: p.title })}
                          checked={compare.includes(p.id)}
                          onChange={(e) =>
                            setCompare(
                              e.target.checked
                                ? [...compare, p.id].slice(-4)
                                : compare.filter((id) => id !== p.id),
                            )
                          }
                        />
                      </label>
                    </div>
                    <div className="property-body">
                      <span className="eyebrow">
                        {p.location} ·{" "}
                        {localize(
                          p.intent === "rent" ? "FOR RENT" : "FOR SALE",
                        )}
                      </span>
                      <h3>{p.title}</h3>
                      <strong>
                        {money(p.price, currency)}
                        {p.intent === "rent" && <small> {tr("/ month")}</small>}
                      </strong>
                      <p className="property-facts">
                        <span>
                          {number(p.bedrooms)} {tr("beds")}
                        </span>
                        <b>·</b>
                        <span>
                          {number(p.size)} {tr("m²")}
                        </span>
                        <b>·</b>
                        <span>{localize(p.property_type)}</span>
                      </p>
                      <div className="amenities">
                        {p.amenities.map((a: string) => (
                          <span key={a}>{localize(a)}</span>
                        ))}
                      </div>
                      <div className="property-actions">
                        {state.user.role === "admin" && (
                          <button
                            className="text-button"
                            onClick={() => open("property", p)}
                          >
                            {tr("Edit details")}
                            <ArrowUpRight size={14} />
                          </button>
                        )}
                        <button
                          className="text-button"
                          onClick={() =>
                            run(async () => {
                              const result = await api(
                                "/copilot/marketing/" + p.id,
                                "POST",
                              );
                              open("marketing", { ...result, property: p });
                            }, "Marketing draft prepared")
                          }
                        >
                          {tr("Draft listing")}
                          <Sparkles size={14} />
                        </button>
                      </div>
                    </div>
                  </article>
                ))}
              </div>
            </>
          )}

          {page === "inbox" && (
            <section className="card inbox">
              <div className="inbox-list">
                <div className="inbox-heading">
                  <h3>{tr("Conversations")}</h3>
                  <span>{number(state.leads.length)}</span>
                </div>
                <label className="search">
                  <Search size={16} />
                  <input
                    placeholder={tr("Find a customer…")}
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                  />
                </label>
                {filtered(state.leads, ["name", "source"]).map((l, i) => (
                  <button
                    key={l.id}
                    className={
                      "conversation-preview " +
                      (selectedLead === l.id ? "chosen" : "")
                    }
                    onClick={() => setSelectedLead(l.id)}
                  >
                    <Avatar name={l.name} index={i} />
                    <span>
                      <strong>{l.name}</strong>
                      <small>
                        {localize(l.source)} · {localize(l.stage)}
                      </small>
                    </span>
                    <ChevronRight size={13} />
                  </button>
                ))}
              </div>
              <div className="conversation">
                {selected ? (
                  <>
                    <div className="conversation-header">
                      <Avatar name={selected.name} />
                      <div>
                        <h3>{selected.name}</h3>
                        <small>
                          {localize(selected.source)} ·{" "}
                          {selected.location || tr("Location to qualify")}
                        </small>
                      </div>
                      <Pill value={selected.stage} />
                    </div>
                    <div className="assistant-disclosure">
                      <ShieldCheck size={14} />
                      {tr(
                        "Rules assistant works now. Live language model needs authorization.",
                      )}
                    </div>
                    <div className="message-list">
                      {state.messages
                        .filter((m: Row) => m.lead_id === selectedLead)
                        .slice()
                        .reverse()
                        .map((m: Row) => (
                          <div className={"message " + m.direction} key={m.id}>
                            <p dir="auto">{m.body}</p>
                            <small>
                              {localize(
                                m.direction === "inbound"
                                  ? "Customer"
                                  : "Workspace",
                              )}{" "}
                              · {date(m.created_at)}
                            </small>
                          </div>
                        ))}
                      <div ref={chatBottom} />
                    </div>
                    <form className="composer" onSubmit={sendChat}>
                      <select
                        aria-label={tr("Conversation mode")}
                        value={chatMode}
                        onChange={(e) => setChatMode(e.target.value)}
                      >
                        <option value="assistant">
                          {tr("Test customer inquiry → assistant")}
                        </option>
                        <option value="human">{tr("Human reply")}</option>
                      </select>
                      <div>
                        <input
                          aria-label={tr("Message")}
                          value={chatText}
                          onChange={(e) => setChatText(e.target.value)}
                          placeholder={tr(
                            "Type an inquiry in English or Arabic…",
                          )}
                          required
                          maxLength={4000}
                        />
                        <button
                          className="button primary"
                          aria-label={tr("Send message")}
                          disabled={busy}
                        >
                          <Send size={18} />
                        </button>
                      </div>
                    </form>
                  </>
                ) : (
                  <div className="empty">
                    <MessageSquare size={36} />
                    <h3>{tr("Every conversation, in context.")}</h3>
                    <p>
                      {tr(
                        "Select a customer to see their conversation and next steps.",
                      )}
                    </p>
                  </div>
                )}
              </div>
              {selected && (
                <aside className="customer-context">
                  <span className="eyebrow">{tr("CUSTOMER CONTEXT")}</span>
                  <h3>{selected.name}</h3>
                  <div className="score-circle">
                    {localize(selected.score)}
                    <small>/ 100</small>
                  </div>
                  <p className="muted">{tr("Qualification score")}</p>
                  <dl>
                    <dt>{tr("Budget")}</dt>
                    <dd>{money(selected.budget, currency)}</dd>
                    <dt>{tr("Area")}</dt>
                    <dd>{selected.location || "To qualify"}</dd>
                    <dt>{tr("Agent")}</dt>
                    <dd>
                      {
                        state.users.find(
                          (u: Row) => u.id === selected.assigned_to,
                        )?.name
                      }
                    </dd>
                    <dt>{tr("Follow-up consent")}</dt>
                    <dd>
                      {localize(
                        selected.opted_out
                          ? "Opted out"
                          : selected.consent
                            ? "Recorded"
                            : "Not recorded",
                      )}
                    </dd>
                  </dl>
                  <button
                    className="button"
                    disabled={busy}
                    onClick={() =>
                      run(
                        () =>
                          api("/leads/" + selected.id + "/handoff", "POST", {
                            active: !state.conversation_controls?.some(
                              (c: Row) =>
                                c.lead_id === selected.id && c.human_active,
                            ),
                            reason: "Operator takeover",
                          }),
                        "Conversation ownership updated",
                      )
                    }
                  >
                    {localize(
                      state.conversation_controls?.some(
                        (c: Row) => c.lead_id === selected.id && c.human_active,
                      )
                        ? "Resume assistant"
                        : "Human takeover",
                    )}
                  </button>
                  <div style={{ height: 10 }} />
                  <button
                    className="button"
                    onClick={() =>
                      open("preferences", {
                        budget: selected.budget,
                        location: selected.location,
                        bedrooms: selected.bedrooms,
                        consent: !!selected.consent,
                        opted_out: !!selected.opted_out,
                      })
                    }
                  >
                    {tr("Edit preferences")}
                  </button>
                  <h4>{tr("Matching properties")}</h4>
                  {matches.map((p) => (
                    <div className="mini-property" key={p.id}>
                      <strong>{p.title}</strong>
                      <small>{money(p.price, currency)}</small>
                      <span>{p.reasons.map(localize).join(" · ")}</span>
                    </div>
                  ))}
                  {!matches.length && (
                    <p className="fine">
                      {tr(
                        "No available matches. Confirm preferences or review inventory.",
                      )}
                    </p>
                  )}
                  <button
                    className="button primary"
                    onClick={() => newBooking(selected)}
                  >
                    <CalendarDays size={16} />
                    {tr("Book viewing")}
                  </button>
                  {selected.source === "whatsapp" && (
                    <button
                      className="button section-gap"
                      onClick={() =>
                        open("template", {
                          lead_id: selected.id,
                          template_name: "",
                          language: "en",
                          parameter_values: "",
                        })
                      }
                    >
                      {tr("Queue approved template")}
                    </button>
                  )}
                </aside>
              )}
            </section>
          )}

          {page === "appointments" && (
            <>
              <div className="toolbar">
                <span className="muted">
                  {tr(
                    "All times display in your company timezone. Business hours:",
                  )}{" "}
                  {number(cfg.business_start)}:
                  {number(0, { minimumIntegerDigits: 2 })}–
                  {number(cfg.business_end)}:
                  {number(0, { minimumIntegerDigits: 2 })}{" "}
                  {localize(cfg.timezone)}.
                </span>
                <button className="button primary" onClick={() => newBooking()}>
                  <Plus size={16} />
                  {tr("Book viewing")}
                </button>
              </div>
              <div className="appointment-grid">
                {state.appointments.length === 0 && (
                  <section className="card empty">
                    <CalendarDays size={38} />
                    <h3>{tr("Your next meeting starts here.")}</h3>
                    <p>
                      {tr(
                        "Book a property viewing with a customer and sales agent.",
                      )}
                    </p>
                    <button
                      className="button primary"
                      onClick={() => newBooking()}
                    >
                      {tr("Book first viewing")}
                    </button>
                  </section>
                )}
                {state.appointments.map((a: Row) => (
                  <section className="card appointment-card" key={a.id}>
                    <div className="appointment-date">
                      <CalendarDays size={21} />
                      <strong>{date(a.start_at)}</strong>
                      <Pill value={a.status} />
                    </div>
                    <h3>{findProp(a.property_id)?.title}</h3>
                    <p>
                      {leadName(a.lead_id)} ·{" "}
                      {state.users.find((u: Row) => u.id === a.agent_id)?.name}
                    </p>
                    <p className="fine">
                      {a.notes || tr("Property viewing · 60 minutes")}
                    </p>
                    {a.status === "Booked" && (
                      <div className="appointment-actions">
                        <button
                          className="button"
                          onClick={() =>
                            open("appointment", {
                              id: a.id,
                              lead_id: a.lead_id,
                              property_id: a.property_id,
                              agent_id: a.agent_id,
                              start_at: "",
                              notes: a.notes,
                            })
                          }
                        >
                          {tr("Reschedule")}
                        </button>
                        <button
                          className="button"
                          disabled={busy}
                          onClick={() =>
                            run(
                              () =>
                                api(
                                  "/appointments/" + a.id + "/Completed",
                                  "PATCH",
                                ),
                              "Viewing completed; follow-up task created",
                            )
                          }
                        >
                          {tr("Complete")}
                        </button>
                        <button
                          className="text-button danger"
                          disabled={busy}
                          onClick={() =>
                            run(
                              () =>
                                api(
                                  "/appointments/" + a.id + "/Cancelled",
                                  "PATCH",
                                ),
                              "Appointment cancelled",
                            )
                          }
                        >
                          {tr("Cancel")}
                        </button>
                      </div>
                    )}
                  </section>
                ))}
              </div>
            </>
          )}

          {page === "tasks" && (
            <>
              <div className="toolbar">
                <span>
                  {number(followups.length)} {tr("pending tasks")}
                </span>
                <button
                  className="button primary"
                  onClick={() =>
                    open("task", { lead_id: "", title: "", due_at: "" })
                  }
                >
                  <Plus size={16} />
                  {tr("Add follow-up")}
                </button>
              </div>
              <section className="card">
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>{tr("Task")}</th>
                        <th>{tr("Customer")}</th>
                        <th>{tr("Due")}</th>
                        <th>{tr("Status")}</th>
                        <th>{tr("Action")}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {state.tasks.map((task: Row) => (
                        <tr key={task.id}>
                          <td>
                            <span className="table-task">
                              <Clock3 size={16} />
                              {localize(task.title)}
                            </span>
                          </td>
                          <td>{leadName(task.lead_id)}</td>
                          <td>{date(task.due_at)}</td>
                          <td>
                            <Pill value={task.status} />
                          </td>
                          <td>
                            {task.status === "Pending" && (
                              <button
                                className="text-button"
                                disabled={busy}
                                onClick={() =>
                                  run(
                                    () =>
                                      api(
                                        "/tasks/" + task.id + "/complete",
                                        "PATCH",
                                      ),
                                    "Task completed",
                                  )
                                }
                              >
                                <Check size={15} />
                                {tr("Complete")}
                              </button>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
            </>
          )}

          {page === "analytics" && (
            <>
              <div style={{ marginBottom: 24 }}>
                <ActivityTrend leads={state.leads} ar={ar} />
              </div>
              <div className="stats-grid">
                {[
                  [
                    "Recorded sales volume",
                    money(metrics.sales_volume || 0, currency),
                  ],
                  [
                    "Open deal value",
                    money(metrics.open_pipeline || 0, currency),
                  ],
                  [
                    "Viewing completion",
                    percent(metrics.appointment_conversion),
                  ],
                  [
                    "Average first reply",
                    metrics.average_response_seconds === null
                      ? "No paired replies"
                      : metrics.average_response_seconds + " sec",
                  ],
                ].map(([label, value]) => (
                  <section className="card stat" key={label}>
                    <span>{localize(label)}</span>
                    <strong>{localize(value)}</strong>
                    <small>{tr("Computed from recorded events")}</small>
                  </section>
                ))}
              </div>
              <div className="two-col">
                <section className="card">
                  <div className="card-head">
                    <h3>{tr("Lead sources")}</h3>
                    <Globe2 size={18} />
                  </div>
                  <div className="source-chart">
                    {Object.entries(metrics.sources || {}).map(
                      ([source, count], i) => (
                        <div key={source}>
                          <span>{localize(source)}</span>
                          <div>
                            <i
                              className={"bar-" + i}
                              style={{
                                width:
                                  (Number(count) /
                                    Math.max(metrics.total_leads, 1)) *
                                    100 +
                                  "%",
                              }}
                            />
                          </div>
                          <strong>{number(count)}</strong>
                        </div>
                      ),
                    )}
                  </div>
                </section>
                <section className="card">
                  <div className="card-head">
                    <h3>{tr("Team performance")}</h3>
                    <UsersRound size={18} />
                  </div>
                  <div className="table-wrap">
                    <table>
                      <thead>
                        <tr>
                          <th>{tr("Agent")}</th>
                          <th>{tr("Assigned")}</th>
                          <th>{tr("Won")}</th>
                        </tr>
                      </thead>
                      <tbody>
                        {metrics.agents?.map((a: Row) => (
                          <tr key={a.name}>
                            <td>{a.name}</td>
                            <td>{a.leads}</td>
                            <td>{a.won}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </section>
              </div>
              <section className="card roi-card section-gap">
                <div>
                  <span className="eyebrow">
                    {tr("PLAN WITH TRANSPARENT ASSUMPTIONS")}
                  </span>
                  <h3>{tr("What could better follow-up be worth?")}</h3>
                  <p className="muted">
                    {tr(
                      "A scenario calculator, not a revenue promise. Edit every assumption.",
                    )}
                  </p>
                  <div className="form-grid">
                    {Object.entries(roi).map(([key, value]) => (
                      <label className="field" key={key}>
                        {localize(
                          (
                            {
                              leads: "Monthly leads",
                              uplift: "Conversion increase (percentage points)",
                              commission: "Commission per won deal",
                              monthly: "Monthly operating cost",
                            } as Record<string, string>
                          )[key],
                        )}
                        <input
                          type="number"
                          min="0"
                          max={key === "uplift" ? 100 : undefined}
                          value={value}
                          onChange={(e) =>
                            setRoi({
                              ...roi,
                              [key]: Math.max(0, Number(e.target.value)),
                            })
                          }
                        />
                      </label>
                    ))}
                  </div>
                </div>
                <div className="roi-result">
                  <Sparkles size={24} />
                  <small>{tr("ILLUSTRATIVE NET MONTHLY VALUE")}</small>
                  <strong>
                    {money(
                      ((roi.leads * roi.uplift) / 100) * roi.commission -
                        roi.monthly,
                      currency,
                    )}
                  </strong>
                  <p>
                    {roi.leads} {tr("leads ×")} {roi.uplift}% ×{" "}
                    {money(roi.commission, currency)} −{" "}
                    {money(roi.monthly, currency)}
                  </p>
                </div>
              </section>
            </>
          )}

          {page === "agents" && (
            <>
              <div className="toolbar">
                <p className="muted">
                  {tr(
                    "New inquiries are assigned to the active agent with the fewest open leads.",
                  )}
                </p>
                {state.user.role === "admin" && (
                  <button
                    className="button primary"
                    onClick={() =>
                      open("user", {
                        name: "",
                        email: "",
                        password: "",
                        role: "agent",
                      })
                    }
                  >
                    <Plus size={16} />
                    {tr("Add team member")}
                  </button>
                )}
              </div>
              <div className="agent-grid">
                {state.users.map((u: Row, i: number) => (
                  <section className="card agent-card" key={u.id}>
                    <Avatar name={u.name} index={i} />
                    <h3>{u.name}</h3>
                    <p>{u.email}</p>
                    <Pill value={u.active ? u.role : "Inactive"} />
                    <div className="agent-stats">
                      <span>
                        <strong>
                          {
                            state.leads.filter(
                              (l: Row) => l.assigned_to === u.id,
                            ).length
                          }
                        </strong>
                        {tr("Assigned leads")}
                      </span>
                      <span>
                        <strong>
                          {
                            state.leads.filter(
                              (l: Row) =>
                                l.assigned_to === u.id && l.stage === "Won",
                            ).length
                          }
                        </strong>
                        {tr("Won customers")}
                      </span>
                    </div>
                    {state.user.role === "admin" &&
                      u.id !== state.user.id &&
                      !!u.active && (
                        <button
                          className="text-button danger"
                          disabled={busy}
                          onClick={() =>
                            run(
                              () =>
                                api("/users/" + u.id + "/deactivate", "PATCH"),
                              "User deactivated; sessions revoked",
                            )
                          }
                        >
                          {tr("Deactivate account")}
                        </button>
                      )}
                  </section>
                ))}
              </div>
            </>
          )}

          {page === "assistant" && (
            <>
              <div className="intelligence-header card">
                <div className="intelligence-logo">
                  <Sparkles size={28} />
                </div>
                <div>
                  <span className="eyebrow">
                    {cfg.assistant_name.toUpperCase()} {tr("SALES COPILOT")}
                  </span>
                  <h3>{tr("Know what matters. Act with confidence.")}</h3>
                  <p className="muted">
                    {tr(
                      "Recommendations use recorded preferences, inventory, and activity. A language model is optional and requires verified access.",
                    )}
                  </p>
                </div>
                <button className="button" onClick={() => navigate("settings")}>
                  {tr("Configure assistant")}
                  <Settings2 size={16} />
                </button>
              </div>
              <div className="insight-grid">
                {state.insights.map((i: Row) => (
                  <section className="card intelligence-card" key={i.lead_id}>
                    <div>
                      <span className="pill orange">{localize(i.type)}</span>
                      <span className="fine">
                        {localize(i.priority)} {tr("priority")}
                      </span>
                    </div>
                    <h3>{i.name}</h3>
                    <p>{localize(i.action)}</p>
                    <small>{localize(i.evidence)}</small>
                    <button
                      className="button"
                      onClick={() => {
                        setSelectedLead(i.lead_id);
                        navigate("inbox");
                      }}
                    >
                      {tr("Open customer context")}
                      <ArrowUpRight size={16} />
                    </button>
                  </section>
                ))}
              </div>
              <section className="card section-gap">
                <div className="card-head">
                  <h3>{tr("Inventory intelligence")}</h3>
                  <Building2 size={18} />
                </div>
                <div className="inventory-summary">
                  <span>
                    <strong>
                      {
                        state.properties.filter(
                          (p: Row) => p.status === "Available",
                        ).length
                      }
                    </strong>
                    {tr("Available properties")}
                  </span>
                  <span>
                    <strong>
                      {
                        state.insights.filter(
                          (i: Row) => i.type === "Inventory gap",
                        ).length
                      }
                    </strong>
                    {tr("Unmatched customer requirements")}
                  </span>
                  <span>
                    <strong>
                      {
                        state.insights.filter((i: Row) => i.type === "Leakage")
                          .length
                      }
                    </strong>
                    {tr("Leads at risk from inactivity")}
                  </span>
                </div>
              </section>
            </>
          )}

          {page === "automation" && (
            <>
              <WorkflowStudio ar={ar} />
              <div className="automation-callout">
                <Workflow size={23} />
                <div>
                  <h3>
                    {tr("One workflow engine. A connected customer journey.")}
                  </h3>
                  <p>
                    {tr(
                      "Consent-aware follow-up, re-engagement, reservations and reconciliation. Every module remains inactive until locally enabled.",
                    )}
                  </p>
                </div>
                <button
                  className="button primary"
                  disabled={busy}
                  onClick={() =>
                    run(
                      () => api("/automation/tick", "POST"),
                      "Due follow-ups evaluated; eligible messages queued",
                    )
                  }
                >
                  <Zap size={16} />
                  {tr("Evaluate due follow-ups")}
                </button>
              </div>
              <div className="two-col">
                <section className="card">
                  <div className="card-head">
                    <h3>{tr("Delivery outbox")}</h3>
                    <button
                      className="text-button"
                      disabled={busy}
                      onClick={() =>
                        run(async () => {
                          const result = await api(
                            "/integrations/dispatch",
                            "POST",
                          );
                          setNotice(
                            result.blocked || `${result.sent} messages sent`,
                          );
                        }, "Delivery gate checked")
                      }
                    >
                      {tr("Check delivery gate")}
                      <ShieldCheck size={15} />
                    </button>
                  </div>
                  <div className="table-wrap">
                    <table>
                      <thead>
                        <tr>
                          <th>{tr("Customer")}</th>
                          <th>{tr("Channel")}</th>
                          <th>{tr("Status")}</th>
                          <th>{tr("Attempts")}</th>
                        </tr>
                      </thead>
                      <tbody>
                        {state.outbox.map((o: Row) => (
                          <tr key={o.id}>
                            <td>
                              {leadName(o.lead_id)}
                              {o.error && (
                                <small className="row-note">
                                  {localize(o.error)}
                                </small>
                              )}
                            </td>
                            <td>{localize(o.channel)}</td>
                            <td>
                              <Pill value={o.status} />
                            </td>
                            <td>{number(o.attempts)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    {!state.outbox.length && (
                      <div className="empty compact">
                        <p>
                          {tr(
                            "No queued messages. Evaluate due tasks to populate this outbox.",
                          )}
                        </p>
                      </div>
                    )}
                  </div>
                </section>
                <section className="card">
                  <div className="card-head">
                    <h3>{tr("Safeguards")}</h3>
                    <ShieldCheck size={19} />
                  </div>
                  <div className="safeguards">
                    {[
                      "Tenant-scoped automation",
                      "Contact consent and opt-out checks",
                      "Idempotent event processing",
                      "Messaging window enforcement",
                      "Retries with backoff and attempt limits",
                      "Real delivery requires owner approval",
                    ].map((text) => (
                      <p key={text}>
                        <CheckCircle2 size={16} />
                        {localize(text)}
                      </p>
                    ))}
                  </div>
                </section>
              </div>
              <section className="card section-gap">
                <div className="card-head">
                  <h3>{tr("Operator incident queue")}</h3>
                  <span className="pill orange">
                    {number(operations.open_incidents || 0)} {tr("open")}
                  </span>
                </div>
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>{tr("Category")}</th>
                        <th>{tr("Workflow / execution")}</th>
                        <th>{tr("Status")}</th>
                        <th>{tr("Action")}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {state.incidents?.map((i: Row) => (
                        <tr key={i.id}>
                          <td>{localize(i.category)}</td>
                          <td>
                            {i.workflow_id || "Delivery outbox"} /{" "}
                            {i.execution_id || i.event_id}
                          </td>
                          <td>
                            <Pill value={i.status} />
                          </td>
                          <td>
                            {i.status === "Open" &&
                              state.user.role === "admin" && (
                                <button
                                  className="text-button"
                                  disabled={busy}
                                  onClick={() =>
                                    run(
                                      () =>
                                        api(
                                          "/incidents/" + i.id + "/resolve",
                                          "PATCH",
                                        ),
                                      "Incident resolved; no delivery retried",
                                    )
                                  }
                                >
                                  {tr("Mark reviewed")}
                                </button>
                              )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {!state.incidents?.length && (
                    <div className="empty compact">
                      <p>
                        {tr(
                          "No incidents recorded. Live provider execution remains unverified.",
                        )}
                      </p>
                    </div>
                  )}
                </div>
              </section>
              <section className="card section-gap">
                <div className="card-head">
                  <h3>{tr("Activity & automation log")}</h3>
                  <Activity size={18} />
                </div>
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>{tr("Event")}</th>
                        <th>{tr("Detail")}</th>
                        <th>{tr("Time")}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {state.activities.slice(0, 30).map((a: Row) => (
                        <tr key={a.id}>
                          <td>{localize(a.action)}</td>
                          <td>{auditDetail(a.action, a.detail)}</td>
                          <td>{date(a.created_at)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
            </>
          )}

          {page === "integrations" && (
            <>
              <div className="automation-callout">
                <MessageSquare size={23} />
                <div>
                  <h3>{tr("WhatsApp-first. Adviser-led.")}</h3>
                  <p>
                    {tr(
                      "Rehearse qualification, opt-out, real inventory matching and human handoff in a private sandbox.",
                    )}
                  </p>
                </div>
                <button
                  className="button primary"
                  onClick={() => navigate("whatsapp")}
                >
                  {tr("Open WhatsApp sandbox")}
                  <ArrowUpRight size={16} />
                </button>
              </div>
              <div className="connection-note">
                <ShieldCheck size={19} />
                <p>
                  {tr(
                    "Connection status reflects configuration, not verified access. Credentials belong in secure environment settings. No real messages are sent without owner approval.",
                  )}
                </p>
              </div>
              <div className="integration-grid">
                {state.integrations.map((i: Row) => (
                  <section className="card integration-card" key={i.name}>
                    <span className={"integration-icon " + i.name}>
                      {i.name === "website" ? (
                        <Globe2 size={23} />
                      ) : i.name === "n8n" ? (
                        <Workflow size={23} />
                      ) : i.name === "language_model" ? (
                        <Sparkles size={23} />
                      ) : (
                        <MessageSquare size={23} />
                      )}
                    </span>
                    <h3>
                      {localize(
                        (
                          {
                            website: "Website chat & forms",
                            n8n: "n8n Self-Hosted",
                            whatsapp: "WhatsApp Business",
                            telegram: "Telegram",
                            facebook: "Facebook Lead Ads & Messenger",
                            instagram: "Instagram Business",
                            email: "Email ingestion",
                            crm: "Connected CRM",
                            language_model: "Language model",
                          } as Record<string, string>
                        )[i.name],
                      )}
                    </h3>
                    <Pill value={i.status} />
                    <p className="muted">{localize(i.detail)}</p>
                    <div className="integration-actions">
                      <button
                        className="button"
                        onClick={() => open("integration", i)}
                      >
                        {localize(
                          i.name === "website"
                            ? "Open website chat"
                            : "Setup requirements",
                        )}
                        <ArrowUpRight size={15} />
                      </button>
                      {[
                        "n8n",
                        "whatsapp",
                        "telegram",
                        "language_model",
                      ].includes(i.name) && (
                        <button
                          className="text-button"
                          disabled={busy}
                          onClick={() =>
                            run(async () => {
                              const r = await api(
                                "/integrations/" + i.name + "/verify",
                                "POST",
                              );
                              if (!r.verified)
                                throw new Error(
                                  "Provider verification failed: HTTP " +
                                    r.http_status,
                                );
                            }, "Provider access verified in this request")
                          }
                        >
                          {tr("Verify access")}
                        </button>
                      )}
                    </div>
                  </section>
                ))}
              </div>
            </>
          )}

          {page === "settings" && (
            <>
              <section className="card onboarding">
                <div>
                  <span className="eyebrow">{tr("CLIENT ONBOARDING")}</span>
                  <h3>{tr("Your company. Your way of working.")}</h3>
                  <p>
                    {tr(
                      "Set your identity, add inventory, build your team, then authorize the channels you need.",
                    )}
                  </p>
                </div>
                <div className="onboarding-steps">
                  {[
                    [cfg.onboarding_complete, "Company identity"],
                    [state.properties.length > 0, "Property inventory"],
                    [state.users.length > 1, "Sales team"],
                    [false, "External channels"],
                  ].map(([done, label], i) => (
                    <button
                      key={i}
                      onClick={() =>
                        navigate(
                          ["settings", "properties", "agents", "integrations"][
                            i
                          ],
                        )
                      }
                    >
                      <span className={done ? "done" : ""}>
                        {done ? <Check size={15} /> : number(i + 1)}
                      </span>
                      {localize(String(label))}
                    </button>
                  ))}
                </div>
              </section>
              <SettingsForm
                settings={cfg}
                disabled={state.user.role !== "admin" || busy}
                onSave={(values) =>
                  run(
                    () => api("/settings", "PUT", values),
                    "Company configuration saved",
                  )
                }
              />
              <section className="card section-gap">
                <div className="card-head">
                  <h3>{tr("Workspace identifiers")}</h3>
                  <div className="heading-actions">
                    {!state.company.demo && (
                      <button
                        className="button"
                        onClick={() =>
                          open("password", {
                            current_password: "",
                            new_password: "",
                          })
                        }
                      >
                        {tr("Change password")}
                      </button>
                    )}
                    {state.user.role === "admin" && (
                      <button
                        className="button"
                        onClick={() =>
                          open("workspace", {
                            company_name: "",
                            slug: "",
                            owner_name: "",
                            owner_email: "",
                            owner_password: "",
                          })
                        }
                      >
                        {tr("Provision client workspace")}
                      </button>
                    )}
                  </div>
                </div>
                <div className="identifiers">
                  <p>
                    {tr("Sign-in workspace:")} <code>{state.company.slug}</code>
                  </p>
                  <p>
                    {tr("Integration tenant:")} <code>{state.company.id}</code>
                  </p>
                  <p className="fine">
                    {tr(
                      "Only bind external provider credentials to the tenant that owns those channels.",
                    )}
                  </p>
                </div>
              </section>
            </>
          )}

          <footer className="footer">
            <span>
              MADAR AI <b>·</b> {tr("Built for the way you grow.")}
            </span>
            <span>
              <ShieldCheck size={13} />
              {tr("Tenant-scoped workspace")}
              <span className="footer-separator">·</span>
              {"v1.1"}
            </span>
          </footer>
        </div>
      </main>
      {notice && (
        <div className="toast" role="status">
          <CheckCircle2 size={19} />
          {localize(notice)}
        </div>
      )}
      {modal && (
        <div className="modal-backdrop" onClick={() => setModal("")}>
          <section
            className={"modal " + (modal === "compare" ? "wide" : "")}
            role="dialog"
            aria-modal="true"
            aria-labelledby="modal-title"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="modal-header">
              <h2 id="modal-title">
                {localize(
                  (
                    {
                      lead: "Add a new lead",
                      property: form.id ? "Edit property" : "Add a property",
                      appointment: form.id
                        ? "Reschedule viewing"
                        : "Book a property viewing",
                      task: "Create follow-up task",
                      deal: "Record a deal",
                      user: "Add team member",
                      preferences: "Customer preferences",
                      reset: "Reset fictional demo",
                      compare: "Property comparison",
                      marketing: "Verified property marketing draft",
                      integration: "Integration setup",
                      template: "Approved WhatsApp template",
                      workspace: "Provision a client workspace",
                      password: "Change your password",
                    } as Record<string, string>
                  )[modal],
                )}
              </h2>
              <button
                className="icon-button"
                aria-label={tr("Close dialog")}
                onClick={() => setModal("")}
              >
                <X size={21} />
              </button>
              <LanguageSelector />
            </div>
            {error && <div className="alert">{errorText(error)}</div>}
            {[
              "lead",
              "property",
              "appointment",
              "task",
              "deal",
              "user",
              "preferences",
              "template",
              "workspace",
              "password",
            ].includes(modal) && (
              <form onSubmit={submit}>
                <div className="form-grid">
                  {modal === "lead" && (
                    <>
                      {field("Full name", "name", "text", true)}
                      {field("Phone", "phone", "tel")}
                      {field("Email", "email", "email")}
                      {select("Lead source", "source", [
                        "website",
                        "whatsapp",
                        "telegram",
                        "facebook",
                        "instagram",
                        "email",
                        "crm",
                      ])}
                      {field("Budget", "budget", "number")}
                      {field("Preferred area", "location")}
                      {select("Property type", "property_type", [
                        "Apartment",
                        "Villa",
                        "Office",
                        "Land",
                      ])}
                      {field("Bedrooms", "bedrooms", "number")}
                      {select("Intent", "intent", ["buy", "rent"])}
                      <label className="checkbox-field">
                        <input
                          type="checkbox"
                          checked={form.consent}
                          onChange={(e) => update("consent", e.target.checked)}
                        />
                        {tr("Follow-up consent recorded")}
                      </label>
                    </>
                  )}
                  {modal === "property" && (
                    <>
                      {field("Property title", "title", "text", true)}
                      {field("Location", "location", "text", true)}
                      {field(
                        "Price in company currency",
                        "price",
                        "number",
                        true,
                      )}
                      {field("Size (m²)", "size", "number", true)}
                      {field("Bedrooms", "bedrooms", "number")}
                      {select("Property type", "property_type", [
                        "Apartment",
                        "Villa",
                        "Office",
                        "Land",
                      ])}
                      {select("Listing intent", "intent", ["buy", "rent"])}
                      {select("Availability", "status", [
                        "Available",
                        "Reserved",
                        "Sold",
                        "Rented",
                      ])}
                      <label className="field">
                        {tr("Amenities (comma separated)")}
                        <input
                          value={form.amenities.join(",")}
                          onChange={(e) =>
                            update("amenities", e.target.value.split(","))
                          }
                        />
                      </label>
                      {field("Image HTTPS URL (optional)", "image", "url")}
                      <label className="field full">
                        {tr("Verified description")}
                        <textarea
                          value={form.description}
                          onChange={(e) =>
                            update("description", e.target.value)
                          }
                        />
                      </label>
                    </>
                  )}
                  {modal === "appointment" && (
                    <>
                      {select("Customer", "lead_id", state.leads)}
                      {select(
                        "Property",
                        "property_id",
                        state.properties.filter(
                          (p: Row) => p.status === "Available",
                        ),
                      )}
                      {select(
                        "Agent",
                        "agent_id",
                        state.users.filter((u: Row) => u.active),
                      )}
                      {field(
                        "Start time (your local timezone)",
                        "start_at",
                        "datetime-local",
                        true,
                      )}
                      {field("Notes", "notes")}
                    </>
                  )}
                  {modal === "task" && (
                    <>
                      {select("Customer", "lead_id", state.leads)}
                      {field("Task title", "title", "text", true)}
                      {field("Due time", "due_at", "datetime-local", true)}
                    </>
                  )}
                  {modal === "deal" && (
                    <>
                      {select("Customer", "lead_id", state.leads)}
                      {select(
                        "Property (optional)",
                        "property_id",
                        state.properties,
                        false,
                      )}
                      {field("Deal value", "amount", "number", true)}
                      {field(
                        "Commission earned if won",
                        "commission",
                        "number",
                      )}
                      {select("Status", "status", ["Open", "Won", "Lost"])}
                      {field("Reason if lost", "lost_reason")}
                    </>
                  )}
                  {modal === "user" && (
                    <>
                      {field("Full name", "name", "text", true)}
                      {field("Email", "email", "email", true)}
                      {field(
                        "Initial password (12+ characters)",
                        "password",
                        "password",
                        true,
                      )}
                      {select("Role", "role", ["agent", "admin"])}
                      <p className="fine full">
                        {tr(
                          "This creates a real account. It does not send an invitation email. Share access privately and rotate the initial password before use.",
                        )}
                      </p>
                    </>
                  )}
                  {modal === "preferences" && (
                    <>
                      {field("Budget", "budget", "number")}
                      {field("Preferred area", "location")}
                      {field("Minimum bedrooms", "bedrooms", "number")}
                      <label className="checkbox-field">
                        <input
                          type="checkbox"
                          checked={form.consent}
                          onChange={(e) => update("consent", e.target.checked)}
                        />
                        {tr("Follow-up consent")}
                      </label>
                      <label className="checkbox-field">
                        <input
                          type="checkbox"
                          checked={form.opted_out}
                          onChange={(e) =>
                            update("opted_out", e.target.checked)
                          }
                        />
                        {tr("Opted out")}
                      </label>
                    </>
                  )}
                  {modal === "workspace" && (
                    <>
                      {field("Company name", "company_name", "text", true)}
                      {field("Workspace slug", "slug", "text", true)}
                      {field("Owner name", "owner_name", "text", true)}
                      {field("Owner email", "owner_email", "email", true)}
                      {field(
                        "Owner initial password",
                        "owner_password",
                        "password",
                        true,
                      )}
                      <p className="fine full">
                        {tr(
                          "Creates a separate empty company with isolated data. Sign in using the workspace slug and its owner account.",
                        )}
                      </p>
                    </>
                  )}
                  {modal === "password" && (
                    <>
                      {field(
                        "Current password",
                        "current_password",
                        "password",
                        true,
                      )}
                      {field(
                        "New password (12+ characters)",
                        "new_password",
                        "password",
                        true,
                      )}
                    </>
                  )}
                  {modal === "template" && (
                    <>
                      {field(
                        "Meta-approved template name",
                        "template_name",
                        "text",
                        true,
                      )}
                      {field(
                        "Approved language code",
                        "language",
                        "text",
                        true,
                      )}
                      {field(
                        "Body parameters in approved order (separate with |)",
                        "parameter_values",
                      )}
                      <p className="fine full">
                        {tr(
                          "Supports approved text body parameters in the exact Meta-approved order; header/media/button parameters require another adapter. Requires recorded consent and owner-approved external delivery.",
                        )}
                      </p>
                    </>
                  )}
                </div>
                <div className="modal-footer">
                  <button
                    type="button"
                    className="button"
                    onClick={() => setModal("")}
                  >
                    {tr("Cancel")}
                  </button>
                  <button className="button primary" disabled={busy}>
                    {localize(busy ? "Saving…" : "Save")}
                    <Check size={16} />
                  </button>
                </div>
              </form>
            )}
            {modal === "reset" && (
              <>
                <p>
                  {tr(
                    "This resets only this isolated workspace’s fictional customers, properties, conversations, and appointments.",
                  )}
                </p>
                <div className="modal-footer">
                  <button className="button" onClick={() => setModal("")}>
                    {tr("Keep demo")}
                  </button>
                  <button
                    className="button primary"
                    disabled={busy}
                    onClick={() =>
                      run(async () => {
                        await api("/demo/reset", "POST");
                        setSelectedLead("");
                        setCompare([]);
                        setModal("");
                      }, "Fictional demo reset")
                    }
                  >
                    {tr("Reset fictional demo")}
                  </button>
                </div>
              </>
            )}
            {modal === "compare" && (
              <div className="comparison-grid">
                {state.properties
                  .filter((p: Row) => compare.includes(p.id))
                  .map((p: Row) => (
                    <div key={p.id}>
                      <h3>{p.title}</h3>
                      <PropertyArt />
                      <dl>
                        <dt>{tr("Price")}</dt>
                        <dd>{money(p.price, currency)}</dd>
                        <dt>{tr("Location")}</dt>
                        <dd>{p.location}</dd>
                        <dt>{tr("Area")}</dt>
                        <dd>
                          {number(p.size)} {tr("m²")}
                        </dd>
                        <dt>{tr("Bedrooms")}</dt>
                        <dd>{number(p.bedrooms)}</dd>
                        <dt>{tr("Price / m²")}</dt>
                        <dd>{money(p.price / p.size, currency)}</dd>
                        <dt>{tr("Amenities")}</dt>
                        <dd>{p.amenities.map(localize).join(tr(", "))}</dd>
                        <dt>{tr("Availability")}</dt>
                        <dd>{localize(p.status)}</dd>
                      </dl>
                    </div>
                  ))}
              </div>
            )}
            {modal === "marketing" && (
              <>
                <p className="fine">
                  {tr(
                    "Generated from verified listing fields. Review before publishing. No content has been published.",
                  )}
                </p>
                <textarea
                  className="marketing-output"
                  readOnly
                  value={
                    form.property
                      ? tr(
                          "Discover {title} in {location}. {area} m², {bedrooms} bedrooms. Listed at {price}. Features: {amenities}. Contact {company} to ask about current availability.",
                          {
                            title: form.property.title,
                            location: form.property.location,
                            area: number(form.property.size),
                            bedrooms: number(form.property.bedrooms),
                            price: money(form.property.price, currency),
                            amenities: form.property.amenities
                              .map(localize)
                              .join(tr(", ")),
                            company: state.company.name,
                          },
                        )
                      : form.draft
                  }
                />
                <button
                  className="button"
                  onClick={() =>
                    download("property-marketing-draft.json", form)
                  }
                >
                  <ArrowDownToLine size={16} />
                  {tr("Download draft")}
                </button>
              </>
            )}
            {modal === "integration" &&
              (form.name === "website" ? (
                <WebsiteChat slug={state.company.slug} onChange={refresh} />
              ) : (
                <>
                  <p>
                    {tr(
                      "Securely configure the following variable names for this tenant, then verify access. Never put credentials in source code or chat.",
                    )}
                  </p>
                  <div className="requirement-list">
                    {form.missing?.map((name: string) => (
                      <code key={name}>{name}</code>
                    ))}
                  </div>
                  <p className="fine">
                    {tr("Your tenant ID:")} {state.company.id}
                  </p>
                  <p>
                    {tr(
                      "n8n workflows and provider-specific setup instructions are included in the repository’s workflows and documentation folders. Production webhooks need a public HTTPS deployment approved by the owner.",
                    )}
                  </p>
                </>
              ))}
          </section>
        </div>
      )}
    </div>
  );

  function leadTable(leads: Row[]) {
    return (
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>{tr("Customer")}</th>
              <th>{tr("Source")}</th>
              <th>{tr("Budget")}</th>
              <th>{tr("Stage")}</th>
              <th>{tr("Score")}</th>
              <th>{tr("Assigned to")}</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {leads.map((l, i) => (
              <tr key={l.id}>
                <td>
                  <button
                    className="customer-cell"
                    onClick={() => {
                      setSelectedLead(l.id);
                      navigate("inbox");
                    }}
                  >
                    <Avatar name={l.name} index={i} />
                    <span>
                      <strong>{l.name}</strong>
                      <small>{l.location || tr("Location to qualify")}</small>
                    </span>
                  </button>
                </td>
                <td>
                  <span className="source-label">
                    <span className={"source-dot " + l.source} />
                    {localize(l.source)}
                  </span>
                </td>
                <td>{money(l.budget, currency)}</td>
                <td>
                  <select
                    className={"stage-select " + stageColors[l.stage]}
                    aria-label={tr("Stage for {name}", { name: l.name })}
                    value={l.stage}
                    disabled={busy}
                    onChange={(e) =>
                      run(
                        () =>
                          api("/leads/" + l.id, "PATCH", {
                            stage: e.target.value,
                          }),
                        "Pipeline stage updated",
                      )
                    }
                  >
                    {cfg.stages.map((s: string) => (
                      <option key={s} value={s}>
                        {localize(s)}
                      </option>
                    ))}
                  </select>
                </td>
                <td>
                  <div className="lead-score">
                    <span>{number(l.score)}</span>
                    <i>
                      <b style={{ width: l.score + "%" }} />
                    </i>
                  </div>
                </td>
                <td>
                  <select
                    className="agent-select"
                    aria-label={tr("Agent for {name}", { name: l.name })}
                    value={l.assigned_to}
                    disabled={busy}
                    onChange={(e) =>
                      run(
                        () =>
                          api("/leads/" + l.id, "PATCH", {
                            assigned_to: e.target.value,
                          }),
                        "Agent assignment updated",
                      )
                    }
                  >
                    {state!.users
                      .filter((u: Row) => u.active)
                      .map((u: Row) => (
                        <option key={u.id} value={u.id}>
                          {u.name}
                        </option>
                      ))}
                  </select>
                </td>
                <td>
                  <button
                    className="icon-button"
                    aria-label={tr("Open {name}", { name: l.name })}
                    onClick={() => {
                      setSelectedLead(l.id);
                      navigate("inbox");
                    }}
                  >
                    <ArrowUpRight size={17} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!leads.length && (
          <div className="empty compact">
            <p>{tr("No customers match this view.")}</p>
          </div>
        )}
      </div>
    );
  }
}

function SettingsForm({
  settings,
  disabled,
  onSave,
}: {
  settings: Row;
  disabled: boolean;
  onSave: (s: Row) => void;
}) {
  const [values, setValues] = useState(settings);
  const update = (key: string, value: unknown) =>
    setValues({ ...values, [key]: value });
  return (
    <form
      className="card settings-form section-gap"
      onSubmit={(e) => {
        e.preventDefault();
        onSave({ ...values, onboarding_complete: true });
      }}
    >
      <div className="card-head">
        <h3>{tr("Brand, business & assistant")}</h3>
        <Settings2 size={18} />
      </div>
      <fieldset disabled={disabled}>
        <div className="form-grid">
          {[
            ["Company name", "company_name"],
            ["Company details", "company_details"],
            ["Logo HTTPS URL", "logo_url"],
            ["Assistant name", "assistant_name"],
          ].map(([label, key]) => (
            <label className="field" key={key}>
              {localize(label)}
              <input
                value={values[key]}
                onChange={(e) => update(key, e.target.value)}
              />
            </label>
          ))}
          <label className="field">
            {tr("Brand accent")}
            <input
              type="color"
              value={values.brand_color}
              onChange={(e) => update("brand_color", e.target.value)}
            />
          </label>
          <label className="field">
            {tr("Currency")}
            <select
              aria-label={tr("Currency")}
              value={values.currency}
              onChange={(e) => update("currency", e.target.value)}
            >
              {["EGP", "AED", "SAR", "USD"].map((c) => (
                <option key={c} value={c}>
                  {localize(c)}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            {tr("Default customer language")}
            <select
              aria-label={tr("Default customer language")}
              value={values.language}
              onChange={(e) => update("language", e.target.value)}
            >
              <option value="en">{tr("English")}</option>
              <option value="ar">{tr("Arabic")}</option>
            </select>
          </label>
          <label className="field">
            {tr("Business timezone")}
            <select
              aria-label={tr("Business timezone")}
              value={values.timezone}
              onChange={(e) => update("timezone", e.target.value)}
            >
              {["Africa/Cairo", "Asia/Dubai", "Asia/Riyadh", "UTC"].map((c) => (
                <option key={c} value={c}>
                  {localize(c)}
                </option>
              ))}
            </select>
          </label>
          {[
            ["Business start hour", "business_start"],
            ["Business end hour", "business_end"],
            ["New lead follow-up delay (hours)", "followup_hours"],
          ].map(([label, key]) => (
            <label className="field" key={key}>
              {localize(label)}
              <input
                type="number"
                value={values[key]}
                onChange={(e) => update(key, Number(e.target.value))}
              />
            </label>
          ))}
          <label className="field">
            {tr("Pipeline stages (core stages retained)")}
            <input
              value={values.stages.join(", ")}
              onChange={(e) =>
                update(
                  "stages",
                  e.target.value
                    .split(",")
                    .map((s) => s.trim())
                    .filter(Boolean),
                )
              }
            />
          </label>
          <label className="field full">
            {tr("Assistant personality")}
            <textarea
              value={values.personality}
              onChange={(e) => update("personality", e.target.value)}
            />
          </label>
        </div>
        <div className="modal-footer">
          <button className="button primary">
            {tr("Save company settings")}
            <Check size={16} />
          </button>
        </div>
      </fieldset>
    </form>
  );
}

function WebsiteChat({
  slug,
  onChange,
}: {
  slug: string;
  onChange: () => Promise<unknown>;
}) {
  const [text, setText] = useState(""),
    [messages, setMessages] = useState<Row[]>([]),
    [session, setSession] = useState(""),
    [suggestions, setSuggestions] = useState<Row[]>([]),
    [slots, setSlots] = useState<Row[]>([]),
    [bookingProperty, setBookingProperty] = useState(""),
    [bookingNotice, setBookingNotice] = useState<{
      key: string;
      time?: string;
    } | null>(null),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [consent, setConsent] = useState(false);
  useEffect(() => {
    if (!session) return;
    const poll = async () => {
      try {
        const r = await api("/public/history", "POST", {
          tenant_slug: slug,
          session,
        });
        setMessages(r.messages);
      } catch {
        /* Preserve the conversation on transient errors. */
      }
    };
    const timer = setInterval(poll, 10000);
    return () => clearInterval(timer);
  }, [session, slug]);
  async function send(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const r = await api("/public/chat", "POST", {
        tenant_slug: slug,
        session,
        name: "Website demo visitor",
        text,
        consent,
      });
      setSession(r.session);
      setSuggestions(r.matches);
      setMessages([
        ...messages,
        { body: text, direction: "inbound" },
        ...(r.reply ? [{ body: r.reply, direction: "outbound" }] : []),
      ]);
      setText("");
      if (r.mode === "human-handoff")
        setBookingNotice({
          key: "Your message is recorded for your human adviser.",
        });
      await onChange();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="website-chat">
      <p className="fine">
        {tr(
          "This is the working public website chat. Inquiries create customers in this company’s CRM.",
        )}
      </p>
      <div className="message-list">
        {messages.length === 0 && (
          <div className="empty compact">
            <Sparkles size={27} />
            <p>
              {tr(
                "Try: “I want an apartment in New Cairo, budget 5 million, 3 bedrooms.”",
              )}
            </p>
          </div>
        )}
        {messages.map((m, i) => (
          <div className={"message " + m.direction} key={i}>
            <p dir="auto">{m.body}</p>
          </div>
        ))}
      </div>
      {suggestions.length > 0 && (
        <div className="chat-matches">
          {suggestions.map((p) => (
            <button
              className="chat-match"
              key={p.id}
              disabled={busy}
              onClick={async () => {
                setBusy(true);
                setError("");
                try {
                  const r = await api("/public/slots", "POST", {
                    tenant_slug: slug,
                    session,
                    property_id: p.id,
                  });
                  setSlots(r.slots);
                  setBookingProperty(p.id);
                } catch (e) {
                  setError((e as Error).message);
                } finally {
                  setBusy(false);
                }
              }}
            >
              <Building2 size={18} />
              <span>
                <strong>{p.title}</strong>
                <small>
                  {p.location} · {number(p.size)} {tr("m²")}
                </small>
              </span>
              <span>
                {tr("View times")}
                <ArrowUpRight size={14} />
              </span>
            </button>
          ))}
        </div>
      )}
      {bookingProperty && (
        <div className="slot-picker">
          <h4>{tr("Choose an available viewing time")}</h4>
          {slots.map((slot) => (
            <button
              className="button"
              key={slot.start_at}
              disabled={busy}
              onClick={async () => {
                setBusy(true);
                setError("");
                try {
                  const result = await api("/public/book", "POST", {
                    tenant_slug: slug,
                    session,
                    property_id: bookingProperty,
                    start_at: slot.start_at,
                  });
                  setBookingNotice({
                    key: "Viewing confirmed: {time}",
                    time: result.start_at,
                  });
                  setSlots([]);
                  setBookingProperty("");
                  await onChange();
                } catch (e) {
                  setError((e as Error).message);
                } finally {
                  setBusy(false);
                }
              }}
            >
              {date(slot.start_at)}
            </button>
          ))}
        </div>
      )}
      {bookingNotice && (
        <p className="booking-notice">
          <CheckCircle2 size={16} />
          {tr(bookingNotice.key, {
            time: bookingNotice.time ? date(bookingNotice.time) : "",
          })}
        </p>
      )}
      <form onSubmit={send}>
        <label className="checkbox-field">
          <input
            type="checkbox"
            disabled={!!session}
            checked={consent}
            onChange={(e) => setConsent(e.target.checked)}
          />
          {tr("I agree to follow-up about my property inquiry")}
        </label>
        <div className="composer">
          <div>
            <input
              aria-label={tr("Website inquiry")}
              placeholder={tr("Ask about a property…")}
              required
              value={text}
              onChange={(e) => setText(e.target.value)}
            />
            <button className="button primary" disabled={busy}>
              <Send size={17} />
              {tr("Send inquiry")}
            </button>
          </div>
        </div>
      </form>
      {error && <div className="alert">{errorText(error)}</div>}
    </div>
  );
}

function PublicChatPage() {
  const slug =
    new URLSearchParams(window.location.search).get("company") || "madar";
  const [company, setCompany] = useState<Row | null>(null),
    [error, setError] = useState("");
  useEffect(() => {
    api("/public/company/" + encodeURIComponent(slug))
      .then(setCompany)
      .catch((e) => setError(e.message));
  }, [slug]);
  setTimezone(company?.timezone || "Africa/Cairo");
  return (
    <div className="public-portal">
      <div
        className="public-portal-card"
        style={
          {
            "--company-accent":
              company?.brand_color?.toLowerCase() === "#b6ee6a"
                ? "#D8BE83"
                : company?.brand_color,
          } as React.CSSProperties
        }
      >
        <header>
          <LanguageSelector />
          <span className="brand-mark">
            <Building2 size={24} />
          </span>
          <div>
            <h1>{company?.company_name || tr("Property adviser")}</h1>
            <small>
              {company?.assistant_name || "Madar"}{" "}
              {tr("· Verified inventory assistant")}
            </small>
          </div>
        </header>
        {company?.demo && (
          <p className="public-demo">
            {tr("Fictional demonstration inventory")}
          </p>
        )}
        {error ? (
          <div className="alert">{errorText(error)}</div>
        ) : company ? (
          <WebsiteChat slug={slug} onChange={async () => {}} />
        ) : (
          <p>{tr("Opening chat…")}</p>
        )}
      </div>
    </div>
  );
}
