import { useEffect, useState, FormEvent } from "react";
import { api, Row } from "./api";
import { tr, errorText, useLanguage } from "./i18n";

export function TelegramSetup({
  demo,
  admin,
  refresh,
}: {
  demo: boolean;
  admin: boolean;
  refresh: () => Promise<void>;
}) {
  const { lang } = useLanguage();
  const [config, setConfig] = useState<Row | null>(null);
  const [token, setToken] = useState("");
  const [origin, setOrigin] = useState("");
  const [authorization, setAuthorization] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [text, setText] = useState("/start");
  const [eventId, setEventId] = useState(Date.now());
  const [result, setResult] = useState<Row | null>(null);
  useEffect(() => {
    if (demo || !admin) return;
    api("/telegram/setup")
      .then((c) => {
        setConfig(c);
        setOrigin(c.public_origin || "");
      })
      .catch((e) => setError(errorText(e.message)));
    const timer = window.setInterval(
      () =>
        api("/telegram/setup")
          .then(setConfig)
          .catch(() => {}),
      8000,
    );
    return () => window.clearInterval(timer);
  }, [demo, admin]);
  async function action(path: string, body?: Row, method = "POST") {
    setBusy(true);
    setError("");
    try {
      const r = await api(path, method, body);
      setConfig(r);
      setAuthorization(false);
      await refresh();
    } catch (e: any) {
      setError(errorText(e.message));
    } finally {
      setBusy(false);
    }
  }
  async function save(e: FormEvent) {
    e.preventDefault();
    const entered = token;
    setToken(""); // Never retain credentials in browser storage or subsequent UI state.
    setBusy(true);
    setError("");
    try {
      const saved = await api("/telegram/setup", "PUT", {
        public_origin: origin,
        ...(entered ? { token: entered } : {}),
      });
      setConfig(saved);
      const connected = await api("/telegram/connect", "POST", {
        replace_webhook: authorization,
      });
      setConfig(connected);
      setAuthorization(false);
      await refresh();
    } catch (e: any) {
      setError(errorText(e.message));
    } finally {
      setBusy(false);
    }
  }
  async function rehearse(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      setResult(
        await api("/sandbox/telegram", "POST", {
          update_id: eventId,
          chat_id: 101,
          text,
          language: lang,
        }),
      );
      await refresh();
    } catch (e: any) {
      setError(errorText(e.message));
    } finally {
      setBusy(false);
    }
  }
  if (!admin) return null;
  return (
    <section
      className="card section-gap"
      aria-label={tr("Telegram guided setup")}
    >
      <div className="card-head">
        <h3>{tr("Telegram guided setup")}</h3>
        <span className="muted">
          {tr("Local polling. Separate delivery permission.")}
        </span>
      </div>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      {demo ? (
        <>
          <p className="muted">
            {tr(
              "Fictional Telegram demo: no credentials, provider calls or delivery.",
            )}
          </p>
          <form onSubmit={rehearse} className="form-grid">
            <label>
              {tr("Update ID")}
              <input
                type="number"
                min="0"
                value={eventId}
                onChange={(e) => setEventId(Number(e.target.value))}
                required
              />
            </label>
            <label>
              {tr("Message")}
              <input
                value={text}
                onChange={(e) => setText(e.target.value)}
                maxLength={4000}
                required
              />
            </label>
            <button className="button primary" disabled={busy}>
              {tr("Simulate Telegram update")}
            </button>
            <button
              type="button"
              className="button"
              onClick={() => setEventId(Date.now())}
            >
              {tr("New update ID")}
            </button>
          </form>
          <p className="fine">
            {tr(
              "Try /start, property requirements, /subscribe, /handoff and /stop. Reuse an Update ID to verify duplicate prevention.",
            )}
          </p>
          {result && (
            <div role="status">
              <p>
                {result.duplicate
                  ? tr("Duplicate update ignored")
                  : tr("Deterministic assistant")}
              </p>
              <p style={{ whiteSpace: "pre-wrap" }}>{result.reply}</p>
            </div>
          )}
        </>
      ) : (
        <>
          <p className="muted">
            {tr(
              "Create a bot with @BotFather, then save its token here. It stays in private server storage and is never returned.",
            )}
          </p>
          <form onSubmit={save} className="form-grid">
            <label>
              {tr("Telegram bot token")}
              <input
                type="password"
                autoComplete="new-password"
                value={token}
                onChange={(e) => setToken(e.target.value)}
                required={!config?.configured}
                placeholder={
                  config?.configured
                    ? tr("Saved securely; leave blank to retain")
                    : ""
                }
                maxLength={140}
              />
            </label>
            <label>
              {tr("Public HTTPS origin (optional; local polling needs none)")}
              <input
                type="url"
                value={origin}
                onChange={(e) => setOrigin(e.target.value)}
                placeholder="https://telegram.example.com"
              />
            </label>
            <button className="button primary" disabled={busy}>
              {tr("Save and Connect")}
            </button>
          </form>
          <p className="fine">
            {tr(
              "Connect starts local long polling inside Docker. No public URL or tunnel is needed. Enable separately authorizes Telegram replies.",
            )}
          </p>
          {config && (
            <>
              <dl className="identifiers">
                <dt>{tr("Connection status")}</dt>
                <dd>
                  {config.polling_active
                    ? tr("Polling connection verified")
                    : config.connected
                      ? tr("Polling starting or reconnecting")
                      : tr("Disconnected")}
                  {config.connection_error
                    ? " — " + errorText(config.connection_error)
                    : ""}
                </dd>
                <dt>{tr("Bot verification")}</dt>
                <dd>
                  {config.verified ? tr("Verified") : tr("Not verified")}
                  {config.bot_username ? " @" + config.bot_username : ""}
                </dd>
                <dt>{tr("Webhook registration")}</dt>
                <dd>
                  {config.registered
                    ? tr("Registered; delivery must be tested locally")
                    : tr("Not registered")}
                </dd>
                <dt>{tr("Telegram delivery")}</dt>
                <dd>{config.enabled ? tr("Enabled") : tr("Disabled")}</dd>
                <dt>{tr("Response mode")}</dt>
                <dd>
                  {config.mode === "deterministic"
                    ? tr("Deterministic assistant")
                    : tr(
                        "Model-assisted interpretation; inventory-grounded replies",
                      )}
                </dd>
              </dl>
              <label>
                <input
                  type="checkbox"
                  checked={authorization}
                  onChange={(e) => setAuthorization(e.target.checked)}
                />
                {tr(
                  "I authorize the selected Telegram action: replace this bot’s webhook, register HTTPS, or enable real delivery.",
                )}
              </label>
              <div className="integration-actions">
                <button
                  className="button primary"
                  disabled={busy || !config.configured}
                  onClick={() =>
                    action("/telegram/connect", {
                      replace_webhook: authorization,
                    })
                  }
                >
                  {tr("Connect local polling")}
                </button>
                <button
                  className="button"
                  disabled={busy || !config.configured}
                  onClick={() => action("/telegram/test")}
                >
                  {tr("Test bot connectivity")}
                </button>
                <button
                  className="button"
                  disabled={
                    busy ||
                    !authorization ||
                    !config.verified ||
                    !config.public_origin
                  }
                  onClick={() =>
                    action("/telegram/register-webhook", { authorized: true })
                  }
                >
                  {tr("Register authorized webhook")}
                </button>
                <button
                  className="button"
                  disabled={
                    busy ||
                    (!config.enabled && (!authorization || !config.verified))
                  }
                  onClick={() =>
                    action(
                      "/telegram/delivery",
                      { authorized: !config.enabled },
                      "PUT",
                    )
                  }
                >
                  {config.enabled
                    ? tr("Disable Telegram delivery")
                    : tr("Enable Telegram delivery")}
                </button>
                <button
                  className="button"
                  disabled={busy || !authorization}
                  onClick={() =>
                    action("/telegram/disconnect", { authorized: true })
                  }
                >
                  {tr("Disconnect bot")}
                </button>
              </div>
              <p className="fine">
                {tr(
                  "Enabling Telegram does not enable WhatsApp or other channels. Existing n8n reconciliation retries eligible Telegram messages; uncertain delivery is held for review.",
                )}
              </p>
            </>
          )}
        </>
      )}
    </section>
  );
}
