import { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { api } from '../api.js';

export default function Showings() {
  const { movieId } = useParams();
  const navigate = useNavigate();
  const [movie, setMovie] = useState(null);
  const [showings, setShowings] = useState([]);
  const [error, setError] = useState('');

  useEffect(() => {
    Promise.all([api.getMovie(movieId), api.movieShowings(movieId)])
      .then(([m, s]) => { setMovie(m); setShowings(s.items); })
      .catch((e) => setError(e.message));
  }, [movieId]);

  if (error) return <p className="error">{error}</p>;
  if (!movie) return <p className="muted">Loading…</p>;

  return (
    <div>
      <Link to="/">← Back</Link>
      <h1 style={{ marginTop: 12 }}>{movie.title}</h1>
      <p className="muted">{movie.genre} · {movie.rating} · {movie.duration_minutes} minutes</p>
      <p>{movie.description}</p>

      <h2 style={{ marginTop: 30 }}>Showings</h2>
      {showings.length === 0 && <p className="muted">No upcoming showings for this movie.</p>}
      <div className="grid showings">
        {showings.map((s) => (
          <div className="card" key={s.id} onClick={() => navigate(`/showings/${s.id}`)} style={{ cursor: 'pointer' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <strong>{new Date(s.start_time).toLocaleString()}</strong>
              <span className="muted">{s.hall_name}</span>
            </div>
            <div style={{ marginTop: 8 }} className="muted">
              {s.seats_available} of {s.seats_total} seats available
            </div>
            <div style={{ marginTop: 8 }}>
              Base price: <strong>${s.base_price}</strong>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
