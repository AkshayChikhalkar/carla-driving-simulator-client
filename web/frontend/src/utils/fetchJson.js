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
  if (!headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  // Handle timeout
  let timeoutId;
  const controller = new AbortController();
  const { signal } = controller;

  if (options.timeout) {
    timeoutId = setTimeout(() => controller.abort(), options.timeout);
  }

  try {
    const resp = await fetch(url, { ...options, headers, signal });
    if (timeoutId) clearTimeout(timeoutId);

    if (!resp.ok) {
      const error = await resp.json().catch(() => ({ error: `HTTP Error ${resp.status}` }));
      const errorMessage = error.error || `HTTP Error ${resp.status}`;
      
      if (options.errorHandler) {
        return options.errorHandler(resp.status, new Error(errorMessage));
      }
      
      throw new Error(errorMessage);
    }
    
    return resp;
  } catch (error) {
    if (timeoutId) clearTimeout(timeoutId);
    
    if (error.name === 'AbortError') {
      throw new Error('Request timeout');
    }
    
    throw error;
  }
}


