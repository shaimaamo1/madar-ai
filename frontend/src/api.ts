import { money, date } from "./i18n";
export { money, date };
export type Row = Record<string, any>;
export async function api(
  path: string,
  method = "GET",
  body?: unknown,
): Promise<any> {
  let res: Response;
  try {
    res = await fetch("/api" + path, {
      method,
      credentials: "same-origin",
      headers: body === undefined ? {} : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new Error("Unable to connect. Check your connection and try again.");
  }
  let data: any;
  try {
    data = await res.json();
  } catch {
    throw new Error(
      "The server returned an unexpected response. Please try again.",
    );
  }
  if (!res.ok)
    throw new Error(
      typeof data.detail === "string"
        ? data.detail
        : "Check the form fields and try again.",
    );
  return data;
}
export function download(name: string, data: unknown) {
  const url = URL.createObjectURL(
    new Blob(
      [typeof data === "string" ? data : JSON.stringify(data, null, 2)],
      { type: "application/json" },
    ),
  );
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  URL.revokeObjectURL(url);
}
