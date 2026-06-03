// Admin: list halls and create new ones (seats auto-generated).

import { useEffect, useState } from 'react';
import { api } from '../../api.js';

export default function AdminHalls() {
  const [halls, setHalls] = useState([]);
  const [error, setError] = useState('');
  const [msg, setMsg] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ name: '', rows_count: 8, cols_count: 10 });

  function load() {
    api.listHalls()
      .then(setHalls)
      .catch((e) => setError(e.message));
  }
  useEffect(load, []);

  async function submit(e) {
    e.preventDefault();
    setError(''); setMsg('');
    try {
      await api.createHall({
        name: form.name,
        rows_count: Number(form.rows_count),
        cols_count: Number(form.cols_count),
        // seats omitted -> backend auto-generates rows_count x cols_count standard seats.
      });
      setMsg(`Hall "${form.name}" created with ${form.rows_count * form.cols_count} seats.`);
      setShowForm(false);
      setForm({ name: '', rows_count: 8, cols_count: 10 });
      load();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h2 style={{ margin: 0 }}>Halls</h2>
        <button onClick={() => setShowForm((v) => !v)}>+ New hall</button>
      </div>

      {error && <p className="error">{error}</p>}
      {msg && <p className="success">{msg}</p>}

      {showForm && (
        <form className="card" onSubmit={submit} style={{ marginBottom: 24 }}>
          <h3>New hall</h3>
          <div style={{ display: 'grid', gap: 12, gridTemplateColumns: '2fr 1fr 1fr' }}>
            <div>
              <label>Hall name</label>
              <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
            </div>
            <div>
              <label>Rows</label>
              <input type="number" min="1" max="26" value={form.rows_count}
                     onChange={(e) => setForm({ ...form, rows_count: e.target.value })} required />
            </div>
            <div>
              <label>Columns</label>
              <input type="number" min="1" value={form.cols_count}
                     onChange={(e) => setForm({ ...form, cols_count: e.target.value })} required />
            </div>
          </div>
          <p className="muted" style={{ marginTop: 10 }}>
            {form.rows_count * form.cols_count} standard seats will be auto-generated.
          </p>
          <div style={{ marginTop: 14, display: 'flex', gap: 10 }}>
            <button type="submit">Create</button>
            <button type="button" className="secondary" onClick={() => setShowForm(false)}>Cancel</button>
          </div>
        </form>
      )}

      <div className="grid showings">
        {halls.map((h) => (
          <div key={h.id} className="card">
            <h3 style={{ marginBottom: 4 }}>{h.name}</h3>
            <div className="muted">
              {h.rows_count} × {h.cols_count} = {h.rows_count * h.cols_count} seats
            </div>
            <div className="muted" style={{ marginTop: 6 }}>
              VIP seats: {h.seats?.filter((s) => s.seat_type === 'vip').length || 0}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
