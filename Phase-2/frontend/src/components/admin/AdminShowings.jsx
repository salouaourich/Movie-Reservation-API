// Admin: create new showings. Lists existing showings grouped by movie.
//
// Showings are loaded LAZILY per-movie (only when the admin expands a card).
// This keeps the initial page load at 2 API calls instead of 45+ which was
// the original perf bottleneck when the catalog grew.

import { useEffect, useState } from 'react';
import { api } from '../../api.js';

export default function AdminShowings() {
  const [movies, setMovies] = useState([]);
  const [halls, setHalls] = useState([]);
  const [showingsByMovie, setShowingsByMovie] = useState({});  // { [movie_id]: items[] | 'loading' | 'error' }
  const [expanded, setExpanded] = useState({});                // { [movie_id]: true }
  const [error, setError] = useState('');
  const [msg, setMsg] = useState('');
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    movie_id: '',
    hall_id: '',
    start_time: '',
    base_price: '13.00',
  });

  function load() {
    setLoading(true);
    Promise.all([api.listMovies('?page_size=100'), api.listHalls()])
      .then(([m, h]) => {
        setMovies(m.items);
        setHalls(h);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }
  useEffect(load, []);

  // Fetch showings for ONE movie only — triggered when the user expands it.
  async function fetchShowingsFor(movieId) {
    if (showingsByMovie[movieId] && showingsByMovie[movieId] !== 'error') return;
    setShowingsByMovie((prev) => ({ ...prev, [movieId]: 'loading' }));
    try {
      const r = await api.movieShowings(movieId);
      setShowingsByMovie((prev) => ({ ...prev, [movieId]: r.items }));
    } catch {
      setShowingsByMovie((prev) => ({ ...prev, [movieId]: 'error' }));
    }
  }

  function toggle(movieId) {
    const isOpen = expanded[movieId];
    setExpanded((prev) => ({ ...prev, [movieId]: !isOpen }));
    if (!isOpen) fetchShowingsFor(movieId);
  }

  async function submit(e) {
    e.preventDefault();
    setError(''); setMsg('');
    try {
      await api.createShowing({
        movie_id: Number(form.movie_id),
        hall_id: Number(form.hall_id),
        start_time: new Date(form.start_time).toISOString(),
        base_price: form.base_price,
      });
      setMsg('Showing created.');
      setShowForm(false);
      // Invalidate the cached showings for that movie so the next expand reloads.
      setShowingsByMovie((prev) => {
        const next = { ...prev };
        delete next[Number(form.movie_id)];
        return next;
      });
      setForm({ movie_id: '', hall_id: '', start_time: '', base_price: '13.00' });
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h2 style={{ margin: 0 }}>Showings</h2>
        <button onClick={() => setShowForm((v) => !v)}>+ New showing</button>
      </div>

      {error && <p className="error">{error}</p>}
      {msg && <p className="success">{msg}</p>}

      {showForm && (
        <form className="card" onSubmit={submit} style={{ marginBottom: 24 }}>
          <h3>New showing</h3>
          <div style={{ display: 'grid', gap: 12, gridTemplateColumns: '1fr 1fr' }}>
            <div>
              <label>Movie</label>
              <select value={form.movie_id} onChange={(e) => setForm({ ...form, movie_id: e.target.value })} required>
                <option value="">Choose a movie…</option>
                {movies.map((m) => <option key={m.id} value={m.id}>{m.title}</option>)}
              </select>
            </div>
            <div>
              <label>Hall</label>
              <select value={form.hall_id} onChange={(e) => setForm({ ...form, hall_id: e.target.value })} required>
                <option value="">Choose a hall…</option>
                {halls.map((h) => <option key={h.id} value={h.id}>{h.name} ({h.rows_count}×{h.cols_count})</option>)}
              </select>
            </div>
            <div>
              <label>Start time</label>
              <input type="datetime-local" value={form.start_time}
                     onChange={(e) => setForm({ ...form, start_time: e.target.value })} required />
            </div>
            <div>
              <label>Base price (USD $)</label>
              <input type="number" step="0.01" min="0" value={form.base_price}
                     onChange={(e) => setForm({ ...form, base_price: e.target.value })} required />
            </div>
          </div>
          <p className="muted" style={{ marginTop: 10 }}>
            Note: prices shown to customers will be base × tier multiplier (and ×1.5 for VIP seats).
          </p>
          <div style={{ marginTop: 14, display: 'flex', gap: 10 }}>
            <button type="submit">Create</button>
            <button type="button" className="secondary" onClick={() => setShowForm(false)}>Cancel</button>
          </div>
        </form>
      )}

      {loading && <p className="muted">Loading movies…</p>}

      {movies.map((m) => {
        const isOpen = !!expanded[m.id];
        const data = showingsByMovie[m.id];
        return (
          <div key={m.id} className="card" style={{ marginBottom: 12, padding: 14 }}>
            <button
              type="button"
              onClick={() => toggle(m.id)}
              style={{
                width: '100%',
                background: 'transparent',
                border: 'none',
                color: 'var(--text)',
                padding: 0,
                margin: 0,
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                cursor: 'pointer',
                fontSize: 16,
                fontWeight: 600,
                textAlign: 'left',
              }}
            >
              <span>{m.title}</span>
              <span className="muted" style={{ fontSize: 13 }}>
                {isOpen ? '▾ Hide showings' : '▸ Show showings'}
              </span>
            </button>

            {isOpen && (
              <div style={{ marginTop: 14 }}>
                {data === 'loading' && <p className="muted">Loading showings…</p>}
                {data === 'error' && <p className="error">Failed to load showings.</p>}
                {Array.isArray(data) && data.length === 0 && <p className="muted">No showings scheduled.</p>}
                {Array.isArray(data) && data.length > 0 && (
                  <div className="grid showings">
                    {data.map((s) => (
                      <div className="card" key={s.id}>
                        <strong>{new Date(s.start_time).toLocaleString()}</strong>
                        <div className="muted" style={{ marginTop: 4 }}>
                          {s.hall_name} · Base ${s.base_price} · {Math.round(s.occupancy_rate * 100)}% full
                        </div>
                        <div className="muted">
                          {s.seats_available} / {s.seats_total} seats free
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
