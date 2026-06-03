import { Link, useNavigate } from 'react-router-dom';
import { isLoggedIn, isAdmin, isCustomer, getRole, logout } from '../api.js';

export default function Navbar() {
  const navigate = useNavigate();
  const loggedIn = isLoggedIn();
  const role = getRole();

  function doLogout() {
    logout();
    navigate('/');
    window.location.reload();
  }

  return (
    <div className="navbar">
      <Link to="/" className="brand">CINEMA</Link>
      <nav style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
        <Link to="/">Home</Link>

        {/* Customer-only links */}
        {isCustomer() && <Link to="/my-bookings">My Bookings</Link>}

        {/* Admin-only link */}
        {isAdmin() && <Link to="/admin">Admin</Link>}

        {loggedIn ? (
          <>
            <span style={{ marginLeft: 18, color: 'var(--text-secondary)', fontSize: 13 }}>
              {role === 'admin' ? 'Admin' : 'Customer'}
            </span>
            <a onClick={doLogout} style={{ cursor: 'pointer', marginLeft: 14 }}>Logout</a>
          </>
        ) : (
          <>
            <Link to="/login">Login</Link>
            <Link to="/register">Register</Link>
          </>
        )}
      </nav>
    </div>
  );
}
