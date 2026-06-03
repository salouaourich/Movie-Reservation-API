// Admin dashboard. One page with three tabs:
//   1) Movies  — list, create, edit, soft-delete
//   2) Halls   — list, create (auto-generates seats)
//   3) Showings — list per movie, create
//
// All endpoints used here are admin-only on the backend.

import { useState } from 'react';
import { Navigate } from 'react-router-dom';
import { isAdmin } from '../api.js';
import AdminMovies from '../components/admin/AdminMovies.jsx';
import AdminHalls from '../components/admin/AdminHalls.jsx';
import AdminShowings from '../components/admin/AdminShowings.jsx';

export default function Admin() {
  // Hard gate — if you somehow land here without admin role, bounce to home.
  if (!isAdmin()) return <Navigate to="/" replace />;

  const [tab, setTab] = useState('movies');

  const tabs = [
    { id: 'movies',   label: 'Movies' },
    { id: 'halls',    label: 'Halls' },
    { id: 'showings', label: 'Showings' },
  ];

  return (
    <div>
      <h1>Admin Dashboard</h1>
      <p className="muted">Manage the catalog: movies, halls, and showings.</p>

      <div style={{ display: 'flex', gap: 8, margin: '20px 0', borderBottom: '1px solid #2a2a2a' }}>
        {tabs.map((t) => (
          <button
            key={t.id}
            className={tab === t.id ? '' : 'secondary'}
            onClick={() => setTab(t.id)}
            style={{ borderRadius: '6px 6px 0 0' }}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'movies' && <AdminMovies />}
      {tab === 'halls' && <AdminHalls />}
      {tab === 'showings' && <AdminShowings />}
    </div>
  );
}
