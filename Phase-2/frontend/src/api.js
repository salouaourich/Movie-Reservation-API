// All HTTP calls go through here so the rest of the app stays clean.
// During dev, /api is proxied to http://localhost:8000 by vite.config.js.

// In dev: VITE_API_BASE is undefined → falls back to '/api' (Vite proxy handles it).
// In prod (Render): VITE_API_BASE = 'https://cinema-api-5mey.onrender.com/api'
const BASE = (import.meta.env.VITE_API_BASE ?? '/api') + '/v1';

function getToken() {
  return localStorage.getItem('token');
}

export function setToken(token) {
  if (token) localStorage.setItem('token', token);
  else localStorage.removeItem('token');
}

export function setRole(role) {
  if (role) localStorage.setItem('role', role);
  else localStorage.removeItem('role');
}

export function getRole() {
  return localStorage.getItem('role');
}

export function isLoggedIn() {
  return !!getToken();
}

export function isAdmin() {
  return getRole() === 'admin';
}

export function isCustomer() {
  return getRole() === 'customer';
}

export function logout() {
  setToken(null);
  setRole(null);
}

// Hard request timeout — if the backend hangs, fail fast (15 s) instead of
// leaving the UI stuck on "Loading…" forever.
const REQUEST_TIMEOUT_MS = 15_000;

async function request(path, { method = 'GET', body, auth = false } = {}) {
  const headers = { 'Content-Type': 'application/json' };
  if (auth) {
    const t = getToken();
    if (t) headers['Authorization'] = `Bearer ${t}`;
  }

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  let res;
  try {
    res = await fetch(BASE + path, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
      signal: controller.signal,
    });
  } catch (e) {
    clearTimeout(timer);
    if (e.name === 'AbortError') {
      throw new Error('Backend is not responding (timed out after 15 s). Is the API container running?');
    }
    throw new Error(`Network error: ${e.message}. Check that the API is running on port 8000.`);
  }
  clearTimeout(timer);

  if (res.status === 204) return null;

  let data = null;
  try { data = await res.json(); } catch { /* empty body */ }

  if (!res.ok) {
    // Auth endpoints (login/register) must NOT trigger global logout —
    // a 401 there just means "wrong password", not "session expired".
    const isAuthEndpoint = path.startsWith('/auth/login') || path.startsWith('/auth/register');

    // Session-expiry case: token rejected by backend.
    // Wipe local state and bounce to login so the user gets a clear path forward.
    if (res.status === 401 && auth && !isAuthEndpoint) {
      setToken(null);
      setRole(null);
      // Avoid redirect loop if we're already on /login
      if (!window.location.pathname.startsWith('/login')) {
        window.location.replace('/login?expired=1');
      }
    }

    const msg = data?.error?.message || `Request failed: ${res.status}`;
    const err = new Error(msg);
    err.code = data?.error?.code;
    err.details = data?.error?.details;
    err.status = res.status;
    throw err;
  }
  return data;
}

export const api = {
  // ---- Auth ----
  register: (body) => request('/auth/register', { method: 'POST', body }),
  login:    (body) => request('/auth/login',    { method: 'POST', body }),
  me:       ()     => request('/auth/me', { auth: true }),

  // ---- Movies (public reads, admin writes) ----
  listMovies:    (q = '') => request(`/movies${q}`),
  getMovie:      (id)     => request(`/movies/${id}`),
  movieShowings: (id)     => request(`/movies/${id}/showings`),
  createMovie:   (body)   => request('/movies', { method: 'POST', auth: true, body }),
  updateMovie:   (id, body) => request(`/movies/${id}`, { method: 'PATCH', auth: true, body }),
  deleteMovie:   (id)     => request(`/movies/${id}`, { method: 'DELETE', auth: true }),

  // ---- Halls (admin) ----
  listHalls:  ()        => request('/halls', { auth: true }),
  createHall: (body)    => request('/halls', { method: 'POST', auth: true, body }),

  // ---- Showings ----
  getShowing:    (id)        => request(`/showings/${id}`),
  seatMap:       (id)        => request(`/showings/${id}/seats`),
  createShowing: (body)      => request('/showings', { method: 'POST', auth: true, body }),
  holdSeats:     (id, seat_ids) => request(`/showings/${id}/holds`, {
    method: 'POST', auth: true, body: { seat_ids },
  }),
  releaseHolds:  (id, seat_ids) => request(`/showings/${id}/holds`, {
    method: 'DELETE', auth: true, body: { seat_ids },
  }),

  // ---- Bookings (customer) ----
  createBooking: (showing_id, seat_ids) => request('/bookings', {
    method: 'POST', auth: true, body: { showing_id, seat_ids },
  }),
  myBookings:    ()   => request('/bookings/me', { auth: true }),
  cancelBooking: (id) => request(`/bookings/${id}`, { method: 'DELETE', auth: true }),
  getTicket:     (id) => request(`/bookings/${id}/ticket`, { auth: true }),

  // ---- Payments ----
  stripeConfig: () => request('/payments/config'),
};
