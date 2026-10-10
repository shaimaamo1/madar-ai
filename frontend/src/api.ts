export type Row = Record<string, any>;
export async function api(path: string, method = 'GET', body?: unknown): Promise<any> {
  const res = await fetch('/api' + path, { method, credentials: 'same-origin', headers: body === undefined ? {} : { 'Content-Type': 'application/json' }, body: body === undefined ? undefined : JSON.stringify(body) });
  const data = await res.json();
  if (!res.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Check the form fields and try again.');
  return data;
}
export function download(name: string, data: unknown) {
  const url = URL.createObjectURL(new Blob([typeof data === 'string' ? data : JSON.stringify(data, null, 2)], { type: 'application/json' }));
  const a = document.createElement('a'); a.href = url; a.download = name; a.click(); URL.revokeObjectURL(url);
}
export const money = (n: number, currency = 'EGP') => new Intl.NumberFormat('en', { style: 'currency', currency, maximumFractionDigits: 0 }).format(n);
export const date = (value: string) => new Date(value).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
