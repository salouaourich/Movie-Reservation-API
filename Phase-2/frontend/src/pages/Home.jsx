import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, isLoggedIn, isAdmin, isCustomer } from '../api.js';
import MovieCard from '../components/MovieCard.jsx';

export default function Home() {
  const [movies, setMovies] = useState([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // page_size=100 is the backend's hard cap (le=100). Use it so newly
    // created movies aren't hidden behind default pagination.
    api.listMovies('?page_size=100')
      .then((data) => setMovies(data.items))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      {/* Welcome / role banner. Logged-out visitors see two role buttons so the
          choice is obvious. Logged-in users see a single, role-tailored CTA. */}
      {!isLoggedIn() && (
        <div className="card" style={{ marginBottom: 24, padding: 24, textAlign: 'center' }}>
          <h2 style={{ marginBottom: 6 }}>Welcome to Cinema</h2>
          <p className="muted" style={{ marginBottom: 20 }}>
            Pick your role to continue.
          </p>
          <div style={{ display: 'flex', gap: 14, justifyContent: 'center', flexWrap: 'wrap' }}>
            <Link to="/register">
              <button>🎬 Continue as Customer</button>
            </Link>
            <Link to="/login">
              <button className="secondary">🛡️ Sign in as Admin</button>
            </Link>
          </div>
        </div>
      )}

      {isAdmin() && (
        <div className="card" style={{ marginBottom: 24, padding: 18, display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}>
          <div>
            <strong>You're signed in as admin.</strong>
            <div className="muted">Manage movies, halls, and showings from the dashboard.</div>
          </div>
          <Link to="/admin"><button>Go to Admin Dashboard →</button></Link>
        </div>
      )}

      {isCustomer() && (
        <div className="card" style={{ marginBottom: 24, padding: 18, display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}>
          <div>
            <strong>Welcome back!</strong>
            <div className="muted">Pick a movie below to see showtimes, or check your bookings.</div>
          </div>
          <Link to="/my-bookings"><button className="secondary">My Bookings</button></Link>
        </div>
      )}

      <h1>Now Showing</h1>
      {loading && <p className="muted">Loading…</p>}
      {error && <p className="error">{error}</p>}
      <div className="grid movies">
        {movies.map((m) => <MovieCard key={m.id} movie={m} />)}
      </div>
      {!loading && movies.length === 0 && <p className="muted">No movies yet — ask an admin to seed some.</p>}
    </div>
  );
}
