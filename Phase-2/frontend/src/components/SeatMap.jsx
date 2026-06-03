// Interactive seat grid. Receives the seat-map response from the API and
// raises onSelect(seat) when the customer toggles an available seat.

export default function SeatMap({ data, selectedIds, onToggle }) {
  if (!data) return null;

  // Group seats by row_label for rendering.
  const rows = {};
  for (const s of data.seats) {
    if (!rows[s.row_label]) rows[s.row_label] = [];
    rows[s.row_label].push(s);
  }
  const rowLabels = Object.keys(rows).sort();

  return (
    <div className="seatmap-wrap">
      <div className="screen">SCREEN</div>

      <div className="seat-grid">
        {rowLabels.map((label) => (
          <div className="seat-row" key={label}>
            <div className="row-label">{label}</div>
            {rows[label]
              .sort((a, b) => a.seat_number - b.seat_number)
              .map((seat) => {
                const isSelected = selectedIds.includes(seat.id);
                const cls = [
                  'seat',
                  seat.status,
                  seat.seat_type === 'vip' ? 'vip' : '',
                  isSelected ? 'selected' : '',
                ].filter(Boolean).join(' ');
                return (
                  <button
                    key={seat.id}
                    className={cls}
                    disabled={seat.status !== 'available'}
                    onClick={() => onToggle(seat)}
                    title={`${seat.row_label}${seat.seat_number} · ${seat.seat_type} · $${seat.price}`}
                  >
                    {seat.seat_number}
                  </button>
                );
              })}
            <div className="row-label">{label}</div>
          </div>
        ))}
      </div>

      <div className="legend">
        <span><span className="swatch" style={{ background: '#2e7d32' }}></span>Available</span>
        <span><span className="swatch" style={{ background: '#f9a825' }}></span>Held</span>
        <span><span className="swatch" style={{ background: '#555' }}></span>Booked</span>
        <span><span className="swatch" style={{ background: 'var(--accent)' }}></span>Selected</span>
        <span><span className="swatch" style={{ background: 'transparent', boxShadow: 'inset 0 0 0 2px gold' }}></span>VIP</span>
      </div>
    </div>
  );
}
