import { Routes, Route, Navigate } from 'react-router-dom';
import Navbar from './components/Navbar.jsx';
import Home from './pages/Home.jsx';
import Showings from './pages/Showings.jsx';
import SeatSelection from './pages/SeatSelection.jsx';
import MyBookings from './pages/MyBookings.jsx';
import Login from './pages/Login.jsx';
import Register from './pages/Register.jsx';
import Admin from './pages/Admin.jsx';
import { isLoggedIn, isAdmin, isCustomer } from './api.js';

function RequireLogin({ children }) {
  return isLoggedIn() ? children : <Navigate to="/login" replace />;
}

function RequireCustomer({ children }) {
  if (!isLoggedIn()) return <Navigate to="/login" replace />;
  if (!isCustomer()) return <Navigate to="/" replace />;
  return children;
}

function RequireAdmin({ children }) {
  if (!isLoggedIn()) return <Navigate to="/login" replace />;
  if (!isAdmin()) return <Navigate to="/" replace />;
  return children;
}

export default function App() {
  return (
    <>
      <Navbar />
      <div className="container">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/movies/:movieId/showings" element={<Showings />} />
          <Route path="/showings/:showingId" element={<SeatSelection />} />
          <Route path="/my-bookings" element={<RequireCustomer><MyBookings /></RequireCustomer>} />
          <Route path="/admin" element={<RequireAdmin><Admin /></RequireAdmin>} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </div>
    </>
  );
}
