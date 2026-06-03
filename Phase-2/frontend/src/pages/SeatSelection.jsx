import { useEffect, useState, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api, isLoggedIn } from '../api.js';
import SeatMap from '../components/SeatMap.jsx';
import PaymentForm from '../components/PaymentForm.jsx';

// step: 'selecting' | 'paying' | 'confirmed'
export default function SeatSelection() {
  const { showingId } = useParams();
  const navigate = useNavigate();

  const [data,     setData    ] = useState(null);
  const [selected, setSelected] = useState([]);
  const [error,    setError   ] = useState('');
  const [busy,     setBusy    ] = useState(false);
  const [step,     setStep    ] = useState('selecting');   // state machine
  const [pending,  setPending ] = useState(null);          // BookingPendingResponse

  function reload() {
    return api.seatMap(showingId)
      .then(setData)
      .catch((e) => setError(e.message));
  }
  useEffect(() => { reload(); /* eslint-disable-next-line */ }, [showingId]);

  function toggle(seat) {
    if (step !== 'selecting') return;
    setError('');
    setSelected((prev) =>
      prev.includes(seat.id) ? prev.filter((id) => id !== seat.id) : [...prev, seat.id],
    );
  }

  const total = useMemo(() => {
    if (!data) return 0;
    return data.seats
      .filter((s) => selected.includes(s.id))
      .reduce((sum, s) => sum + Number(s.price), 0);
  }, [data, selected]);

  // ── Step 1: hold seats then create pending booking ───────────────────────
  async function holdAndProceed() {
    if (!isLoggedIn()) { navigate('/login'); return; }
    if (selected.length === 0) return;
    setBusy(true); setError('');

    try {
      await api.holdSeats(Number(showingId), selected);
      const booking = await api.createBooking(Number(showingId), selected);
      // booking now contains client_secret — move to payment step
      setPending(booking);
      setStep('paying');
    } catch (e) {
      setError(e.message);
      try { await api.releaseHolds(Number(showingId), selected); } catch { /* ignore */ }
      await reload();
    } finally {
      setBusy(false);
    }
  }

  // ── Step 2: payment confirmed by Stripe ─────────────────────────────────
  function onPaymentSuccess({ ticketCode, total: paidTotal }) {
    setStep('confirmed');
    setSelected([]);
    reload();
    setPending((prev) => ({ ...prev, ticketCode, total: paidTotal }));
  }

  // ── Step 2: user cancels payment ─────────────────────────────────────────
  async function onPaymentCancel() {
    // Release the holds — the backend scheduler will expire the booking.
    try { await api.releaseHolds(Number(showingId), selected); } catch { /* ignore */ }
    setStep('selecting');
    setPending(null);
    setSelected([]);
    await reload();
  }

  // ── Render ───────────────────────────────────────────────────────────────
  if (!data) return <p className="muted">Loading seat map…</p>;

  // Confirmed screen
  if (step === 'confirmed' && pending) {
    return (
      <div>
        <h1 style={{ color: '#2a9d4e' }}>🎉 Booking confirmed!</h1>
        <p>Your ticket code: <strong style={{ fontSize: 22 }}>{pending.ticket_code}</strong></p>
        <p>Total paid: <strong>${Number(pending.total_price).toFixed(2)}</strong></p>
        <p className="muted">A receipt has been sent to your email by Stripe.</p>
        <div style={{ display: 'flex', gap: 12, marginTop: 20 }}>
          <button onClick={() => navigate('/bookings/me')}>View my bookings</button>
          <button onClick={() => { setStep('selecting'); setPending(null); }}>
            Book more seats
          </button>
        </div>
      </div>
    );
  }

  // Payment screen
  if (step === 'paying' && pending) {
    return (
      <div>
        <h1>Select your seats</h1>
        <PaymentForm
          clientSecret={pending.client_secret}
          total={pending.total_price}
          ticketCode={pending.ticket_code}
          expiresAt={pending.payment_expires_at}
          onSuccess={onPaymentSuccess}
          onCancel={onPaymentCancel}
        />
      </div>
    );
  }

  // Seat selection screen (default)
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

      <SeatMap data={data} selectedIds={selected} onToggle={toggle} />

      <div className="summary">
        <div>
          <strong>{selected.length}</strong> seat(s) selected
        </div>
        <div style={{ fontSize: 20, fontWeight: 700 }}>${total.toFixed(2)}</div>
        <button onClick={holdAndProceed} disabled={busy || selected.length === 0}>
          {busy ? 'Processing…' : 'Proceed to payment →'}
        </button>
      </div>
    </div>
  );
}
