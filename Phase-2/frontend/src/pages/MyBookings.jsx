import { useEffect, useState } from 'react';
import { api } from '../api.js';
import BookingCard from '../components/BookingCard.jsx';

export default function MyBookings() {
  const [items, setItems] = useState([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  function load() {
    setLoading(true);
    api.myBookings()
      .then((d) => setItems(d.items))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }
  useEffect(load, []);

  async function cancel(id) {
    if (!confirm('Cancel this booking?')) return;
    try {
      await api.cancelBooking(id);
      load();
    } catch (e) {
      setError(e.message);
    }
  }

  return (
    <div>
      <h1>My Bookings</h1>
      {loading && <p className="muted">Loading…</p>}
      {error && <p className="error">{error}</p>}
      {!loading && items.length === 0 && <p className="muted">You haven't booked anything yet.</p>}
      {items.map((b) => <BookingCard key={b.id} booking={b} onCancel={cancel} />)}
    </div>
  );
}
