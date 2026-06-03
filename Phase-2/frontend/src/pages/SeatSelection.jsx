import { useEffect, useState, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api, isLoggedIn } from '../api.js';
import SeatMap from '../components/SeatMap.jsx';

export default function SeatSelection() {
  const { showingId } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [selected, setSelected] = useState([]);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [busy, setBusy] = useState(false);

  // Load seat map (and re-load after holds/booking).
  function reload() {
    return api.seatMap(showingId)
      .then(setData)
      .catch((e) => setError(e.message));
  }
  useEffect(() => { reload(); /* eslint-disable-next-line */ }, [showingId]);

  // Click toggles a seat in/out of selection.
  function toggle(seat) {
    setError(''); setSuccess('');
    setSelected((prev) =>
      prev.includes(seat.id) ? prev.filter((id) => id !== seat.id) : [...prev, seat.id],
    );
  }

  // Sum of prices for selected seats (from the seat map response, not stored).
  const total = useMemo(() => {
    if (!data) return 0;
    return data.seats
      .filter((s) => selected.includes(s.id))
      .reduce((sum, s) => sum + Number(s.price), 0);
  }, [data, selected]);

  async function holdAndBook() {
    if (!isLoggedIn()) { navigate('/login'); return; }
    if (selected.length === 0) return;
    setBusy(true); setError(''); setSuccess('');
    try {
      // 1) Acquire holds (atomic — all-or-nothing).
      await api.holdSeats(Number(showingId), selected);
      // 2) Confirm the booking immediately. In a real flow there'd be a
      //    payment step between these two calls.
      const booking = await api.createBooking(Number(showingId), selected);
      setSuccess(`Booking confirmed! Ticket code: ${booking.ticket_code}. Total: $${booking.total_price}`);
      setSelected([]);
      await reload();
    } catch (e) {
      setError(e.message);
      // If the booking failed, free any holds we may have grabbed.
      try { await api.releaseHolds(Number(showingId), selected); } catch { /* ignore */ }
      await reload();
    } finally {
      setBusy(false);
    }
  }

  if (!data) return <p className="muted">Loading seat map…</p>;

  return (
    <div>
      <h1>Select your seats</h1>
      <div className="muted" style={{ marginBottom: 8 }}>
        {data.hall.name} · Base price: ${data.base_price} ·{' '}
        Occupancy: {(data.occupancy_rate * 100).toFixed(0)}%{' '}
        <span className={`tier-badge tier-${data.pricing_tier}`}>{data.pricing_tier.toUpperCase()}</span>{' '}
        (×{data.tier_multiplier})
      </div>

      {error && <p className="error">{error}</p>}
      {success && <p className="success">{success}</p>}

      <SeatMap data={data} selectedIds={selected} onToggle={toggle} />

      <div className="summary">
        <div>
          <strong>{selected.length}</strong> seat(s) selected
        </div>
        <div style={{ fontSize: 20, fontWeight: 700 }}>${total.toFixed(2)}</div>
        <button onClick={holdAndBook} disabled={busy || selected.length === 0}>
          {busy ? 'Processing…' : 'Hold & Book'}
        </button>
      </div>
    </div>
  );
}
