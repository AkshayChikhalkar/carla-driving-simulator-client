export async function fetchJson(url, options = {}) {
  const headers = new Headers(options.headers || {});
  const token = sessionStorage.getItem('access_token');
  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`);
  }
  const tenant = sessionStorage.getItem('tenant_id');
  if (tenant && !headers.has('X-Tenant-Id')) {
    headers.set('X-Tenant-Id', tenant);
  }
  if (!headers.has('Content-Type') && options.body) {
    headers.set('Content-Type', 'application/json');
  }
  const resp = await fetch(url, { ...options, headers });
  return resp;
}


