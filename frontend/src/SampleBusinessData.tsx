import { useState } from "react";
import { api, Row } from "./api";
import { tr, number, errorText } from "./i18n";

export function SampleBusinessData({
  data,
  refresh,
}: {
  data: Row;
  refresh: () => Promise<void>;
}) {
  const [action, setAction] = useState<"load" | "remove" | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const blocked = Object.values(data.removal_dependencies || {}).some(
    (count) => Number(count) > 0,
  );
  async function submit() {
    if (!action || !confirmed || busy) return;
    setBusy(true);
    setError("");
    try {
      await api(`/sample-data/${action}`, "POST", { confirmed: true });
      await refresh();
      setAction(null);
      setConfirmed(false);
    } catch (e) {
      setError(errorText((e as Error).message));
    } finally {
      setBusy(false);
    }
  }
  return (
    <section
      className="card section-gap"
      aria-label={tr("Sample business data")}
    >
      <div className="card-head">
        <h3>{tr("Sample business data")}</h3>
      </div>
      <div className="identifiers">
        <p>
          {tr(
            "Sample data copies fictional inventory and CRM records into this workspace. Telegram settings stay unchanged. Fictional customers never receive external messages; sample staff cannot sign in.",
          )}
        </p>
        <p className="fine">
          {tr("Sample / Fictional")} · {tr("AI-generated illustrative image")}
        </p>
        {data.loaded && (
          <p role="status">
            {tr("Sample dataset loaded")}:{" "}
            {Object.entries(data.counts || {})
              .filter(([key]) =>
                [
                  "properties",
                  "leads",
                  "appointments",
                  "tasks",
                  "users",
                  "messages",
                ].includes(key),
              )
              .map(([key, count]) => `${tr(key)}: ${number(Number(count))}`)
              .join(" · ")}
          </p>
        )}
        {blocked && (
          <p role="status">
            {tr(
              "Sample removal is blocked because real records or pending Telegram selections depend on this inventory. Keep the dataset or resolve those dependencies first.",
            )}
          </p>
        )}
        <div className="heading-actions">
          <button
            className="button primary"
            disabled={busy}
            onClick={() => {
              setAction("load");
              setConfirmed(false);
              setError("");
            }}
          >
            {tr("Load Sample Business Data")}
          </button>
          {data.loaded && (
            <button
              className="button"
              disabled={busy || blocked}
              onClick={() => {
                setAction("remove");
                setConfirmed(false);
                setError("");
              }}
            >
              {tr("Remove Sample Business Data")}
            </button>
          )}
        </div>
        {action && (
          <div
            role="dialog"
            aria-modal="false"
            aria-labelledby="sample-confirm-title"
            className="section-gap"
          >
            <h4 id="sample-confirm-title">
              {tr(
                action === "load"
                  ? "Confirm sample import"
                  : "Confirm sample removal",
              )}
            </h4>
            <p>
              {tr(
                action === "load"
                  ? "This imports 30 fictional properties, 40 customers, 25 conversations, 15 viewings, 20 tasks and five inactive sample staff profiles. Existing records are preserved. Running again creates no duplicates. No messages or calendar bookings are sent."
                  : "Only tracked imported sample records will be removed. Real customers, conversations and appointments remain untouched. Removal is blocked when real records depend on sample data.",
              )}
            </p>
            <label>
              <input
                type="checkbox"
                checked={confirmed}
                disabled={busy}
                onChange={(e) => setConfirmed(e.target.checked)}
              />{" "}
              {tr(
                "I understand these records are fictional and authorize this action.",
              )}
            </label>
            <div className="heading-actions section-gap">
              <button
                className="button"
                disabled={busy}
                onClick={() => {
                  setAction(null);
                  setConfirmed(false);
                }}
              >
                {tr("Cancel")}
              </button>
              <button
                className="button primary"
                disabled={!confirmed || busy}
                onClick={submit}
              >
                {tr(
                  busy
                    ? "Processing sample data"
                    : action === "load"
                      ? "Confirm import"
                      : "Confirm removal",
                )}
              </button>
            </div>
          </div>
        )}
        {error && <p role="alert">{error}</p>}
      </div>
    </section>
  );
}
