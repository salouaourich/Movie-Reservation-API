export default function BookingCard({ booking, onCancel }) {
  const isCancelled = booking.status === 'cancelled';
  const startsInPast = new Date(booking.start_time) <= new Date();

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
          <div className="muted">Status: {booking.status}</div>
          {!isCancelled && !startsInPast && (
            <button
              className="secondary"
              style={{ marginTop: 8 }}
              onClick={() => onCancel(booking.id)}
            >
              Cancel
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
