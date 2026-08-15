export const now = () => Math.floor(Date.now() / 1000);
export const uid = (prefix) => `${prefix}_${crypto.randomUUID().replaceAll('-', '')}`;

export async function sha256(value) {
  const bytes = new TextEncoder().encode(value);
  const digest = await crypto.subtle.digest('SHA-256', bytes);
  return [...new Uint8Array(digest)].map(x => x.toString(16).padStart(2, '0')).join('');
}

export function json(data, status = 200, headers = {}) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store', ...headers }
  });
}

export async function bodyJson(request) {
  try { return await request.json(); } catch { return null; }
}
