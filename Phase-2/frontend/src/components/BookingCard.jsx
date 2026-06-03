export default function BookingCard({ booking, onCancel }) {
  const isCancelled  = booking.status === 'cancelled';
  const isPending    = booking.status === 'pending_payment';
  const startsInPast = new Date(booking.start_time) <= new Date();

  // Always allow cancelling a pending_payment booking (the user hasn't paid
  // yet — they shouldn't be stuck with it just because the showing time has
  // passed in the seed data). For confirmed bookings, keep the original rule
  // (can't cancel once the showing started).
  const canCancel = !isCancelled && (isPending || !startsInPast);

  // Style the status badge by state.
  const statusColor = isCancelled
    ? '#888'
    : isPending
      ? '#f9a825'   // amber for pending
      : '#2a9d4e';  // green for confirmed

  return (
    <div className="card" style={{ marginBottom: 16 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}>
        <div>
          <h3 style={{ margin: '0 0 4px' }}>{booking.movie_title}</h3>
          <div className="muted">
            {booking.hall_name} · {new Date(booking.start_time).toLocaleString()}
          </div>
          <div className="muted" style={{ marginTop: 4 }}>
            Ticket: <strong style={{ color: 'var(--text)' }}>{booking.ticket_code}</strong>
          </div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: 20, fontWeight: 700 }}>${booking.total_price}</div>
          <div style={{ color: statusColor, fontWeight: 600, fontSize: 13, marginTop: 2 }}>
            {isPending
              ? '⏳ Awaiting payment'
              : isCancelled
                ? '✗ Cancelled'
                : '✓ Confirmed'}
          </div>
          {canCancel && (
            <button
              className="secondary"
              style={{ marginTop: 8 }}
              onClick={() => onCancel(booking.id)}
            >
              {isPending ? 'Cancel booking' : 'Cancel'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
