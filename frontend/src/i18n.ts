import { useSyncExternalStore } from "react";
import arabic from "./locales/ar.json";
import english from "./locales/en.json";

export type Language = "ar" | "en";
const translations: Record<string, string> = arabic;
const englishOverrides: Record<string, string> = english;
const listeners = new Set<() => void>();
const storageKey = "madar-language";
function readLanguage(): Language {
  try {
    return localStorage.getItem(storageKey) === "ar" ? "ar" : "en";
  } catch {
    return "en";
  }
}
let language: Language = typeof window === "undefined" ? "en" : readLanguage();
let timezone = "Africa/Cairo";
export function getLanguage() {
  return language;
}
export function locale() {
  return language === "ar" ? "ar-EG" : "en-GB";
}
export function setTimezone(value: string) {
  try {
    new Intl.DateTimeFormat("en", { timeZone: value });
    timezone = value;
  } catch {
    timezone = "Africa/Cairo";
  }
}
export function tr(
  key: string,
  values: Record<string, string | number> = {},
): string {
  const template =
    language === "ar"
      ? (translations[key] ?? key)
      : (englishOverrides[key] ?? key);
  return template.replace(/\{(\w+)\}/g, (token, name: string) =>
    String(values[name] ?? token),
  );
}
export function number(value: unknown, options: Intl.NumberFormatOptions = {}) {
  const numeric = Number(value);
  return Number.isFinite(numeric)
    ? new Intl.NumberFormat(locale(), options).format(numeric)
    : "—";
}
export function percent(value: unknown) {
  return number(Number(value) / 100, {
    style: "percent",
    maximumFractionDigits: 1,
  });
}
export function money(value: number, currency = "EGP") {
  try {
    return number(value, {
      style: "currency",
      currency,
      maximumFractionDigits: 0,
    });
  } catch {
    return number(value) + " " + currency;
  }
}
export function date(value: string, options: Intl.DateTimeFormatOptions = {}) {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.valueOf())) return "—";
  return new Intl.DateTimeFormat(locale(), {
    timeZone: timezone,
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    ...options,
  }).format(parsed);
}
export function localize(value: unknown): string {
  if (typeof value === "number") return number(value);
  if (value == null) return "";
  const text = String(value);
  if (translations[text] || englishOverrides[text]) return tr(text);
  if (/^-?\d+(?:\.\d+)?%$/.test(text)) return percent(parseFloat(text));
  if (/^-?\d+(?:\.\d+)?(?: sec)$/.test(text))
    return tr("{count} seconds", { count: number(parseFloat(text)) });
  if (/^-?\d+(?:\.\d+)?$/.test(text)) return number(text);
  const patterns: [RegExp, string][] = [
    [
      /^Provider rejected request \(HTTP (\d+)\)$/,
      "Provider rejected request (HTTP {count})",
    ],
    [/^HTTP (\d+)$/, "HTTP {count}"],
    [
      /^(\d+) lead needs attention\. Your sales intelligence has a plan\.$/,
      "{count} leads need attention. Your sales intelligence has a plan.",
    ],
    [/^(\d+) messages sent$/, "{count} messages sent"],
    [
      /^(\d+) messages queued; delivery requires approval$/,
      "{count} messages queued; delivery requires approval",
    ],
    [
      /^Recorded qualification score (\d+)\/100$/,
      "Recorded qualification score {count}/100",
    ],
    [/^(\d+) hours without activity$/, "{count} hours without activity"],
    [
      /^(\d+) hours without CRM activity in negotiation$/,
      "{count} hours without CRM activity in negotiation",
    ],
    [
      /^Provider verification failed: HTTP (\d+)$/,
      "Provider verification failed: HTTP {count}",
    ],
  ];
  for (const [pattern, key] of patterns) {
    const result = pattern.exec(text);
    if (result) return tr(key, { count: number(result[1]) });
  }
  // Company/customer-authored names, notes and custom stages stay in their source language.
  return text;
}
export function errorText(value: string) {
  if (!value) return "";
  if (translations[value]) return tr(value);
  if (/^Provider verification failed: HTTP \d+$/.test(value))
    return localize(value);
  return tr("The operation could not be completed. Please try again.");
}
function validationMessage(
  control: HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement,
) {
  control.setCustomValidity("");
  const validity = control.validity;
  const key = validity.valueMissing
    ? "Please complete this field."
    : validity.typeMismatch
      ? control instanceof HTMLInputElement && control.type === "email"
        ? "Enter a valid email address."
        : "Enter a valid URL."
      : validity.rangeUnderflow
        ? "Enter a value greater than or equal to {count}."
        : validity.rangeOverflow
          ? "Enter a value less than or equal to {count}."
          : validity.tooShort
            ? "Enter at least {count} characters."
            : validity.tooLong
              ? "Enter no more than {count} characters."
              : validity.stepMismatch || validity.badInput
                ? "Enter a valid number."
                : validity.patternMismatch
                  ? "Use the required format."
                  : "";
  const count =
    control instanceof HTMLInputElement ||
    control instanceof HTMLTextAreaElement
      ? validity.tooShort
        ? control.minLength
        : validity.tooLong
          ? control.maxLength
          : control instanceof HTMLInputElement
            ? validity.rangeUnderflow
              ? control.min
              : control.max
            : ""
      : "";
  if (key) control.setCustomValidity(tr(key, { count: number(count) }));
  return key;
}
function applyLanguage() {
  if (typeof document === "undefined") return;
  document.documentElement.lang = language;
  document.documentElement.dir = language === "ar" ? "rtl" : "ltr";
  document
    .querySelectorAll<
      HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement
    >("[data-madar-invalid]")
    .forEach(validationMessage);
}
export function setLanguage(value: Language) {
  if (value !== "ar" && value !== "en") return;
  language = value;
  try {
    localStorage.setItem(storageKey, value);
  } catch {
    /* Switching still works when storage is restricted. */
  }
  applyLanguage();
  listeners.forEach((listener) => listener());
}
export function useLanguage() {
  const lang = useSyncExternalStore(
    (listener) => {
      listeners.add(listener);
      return () => {
        listeners.delete(listener);
      };
    },
    getLanguage,
    () => "en" as Language,
  );
  return { lang, ar: lang === "ar", setLanguage };
}
if (typeof window !== "undefined") {
  applyLanguage();
  window.addEventListener("storage", (event) => {
    if (event.key === storageKey) {
      language = readLanguage();
      applyLanguage();
      listeners.forEach((listener) => listener());
    }
  });
  document.addEventListener(
    "invalid",
    (event) => {
      const control = event.target;
      if (
        control instanceof HTMLInputElement ||
        control instanceof HTMLSelectElement ||
        control instanceof HTMLTextAreaElement
      ) {
        control.dataset.madarInvalid = "true";
        validationMessage(control);
      }
    },
    true,
  );
  for (const name of ["input", "change"])
    document.addEventListener(
      name,
      (event) => {
        const control = event.target;
        if (
          (control instanceof HTMLInputElement ||
            control instanceof HTMLSelectElement ||
            control instanceof HTMLTextAreaElement) &&
          control.dataset.madarInvalid
        ) {
          if (!validationMessage(control)) delete control.dataset.madarInvalid;
        }
      },
      true,
    );
}

export function auditDetail(action: string, detail: string) {
  if (!detail) return tr("Recorded");
  if (action === "lead.updated")
    return detail.split(",").map(localize).join(tr(", "));
  if (action === "appointment.booked") return date(detail);
  return localize(detail);
}
