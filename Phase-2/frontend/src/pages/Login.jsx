import { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { api, setToken, setRole } from '../api.js';

const KNOWN_EMAIL_DOMAINS = new Set([
  // Google
  'gmail.com', 'googlemail.com', 'google.com',
  // Microsoft
  'hotmail.com', 'hotmail.co.uk', 'hotmail.fr', 'hotmail.de', 'hotmail.it', 'hotmail.es',
  'outlook.com', 'outlook.fr', 'outlook.de', 'outlook.co.uk', 'outlook.es', 'outlook.it',
  'live.com', 'live.co.uk', 'live.fr', 'live.de', 'live.it', 'msn.com', 'microsoft.com',
  // Yahoo
  'yahoo.com', 'yahoo.co.uk', 'yahoo.fr', 'yahoo.de', 'yahoo.it', 'yahoo.es', 'ymail.com',
  // Apple
  'icloud.com', 'me.com', 'mac.com', 'apple.com',
  // Privacy-focused
  'protonmail.com', 'proton.me', 'tutanota.com', 'tutamail.com',
  // Other popular
  'aol.com', 'mail.com', 'gmx.com', 'gmx.de', 'gmx.net',
  'zoho.com', 'fastmail.com', 'yandex.ru', 'yandex.com', 'mail.ru',
  // Regional
  'web.de', 'freenet.de', 'orange.fr', 'sfr.fr', 'free.fr', 'laposte.net',
  'libero.it', 'virgilio.it', 'qq.com', '163.com', 'naver.com',
  'rediffmail.com', 'uol.com.br',
]);

function validateEmail(email) {
  if (!email) return 'Email is required';

  const parts = email.split('@');
  if (parts.length !== 2) return 'Email must contain exactly one @';
  const [local, domain] = parts;
  const domainLower = domain.toLowerCase();

  if (local.length < 3) return 'Email must have at least 3 characters before @';
  if (!/^[a-zA-Z0-9._%+\-]+$/.test(local)) return 'Email contains invalid characters before @';
  if (local.startsWith('.') || local.endsWith('.') || local.includes('..'))
    return 'Email cannot have leading, trailing, or consecutive dots';

  const domainParts = domainLower.split('.');
  if (domainParts.length < 2) return 'Email must include a domain (e.g. @gmail.com)';

  const tld = domainParts[domainParts.length - 1];
  const mainDomain = domainParts[domainParts.length - 2] || '';

  if (!/^[a-zA-Z]{2,}$/.test(tld)) return 'Domain extension must be letters only (e.g. .com, .net)';
  if (!/^[a-zA-Z0-9\-]+$/.test(mainDomain)) return 'Enter a valid email address';

  // Always accept institutional TLDs
  if (['edu', 'ac', 'gov', 'mil'].includes(tld)) return '';

  // Accept known providers
  if (KNOWN_EMAIL_DOMAINS.has(domainLower)) return '';

  // Unknown domain: require at least 6 chars to filter short fake ones (htmil, hmt, xyz, etc.)
  if (mainDomain.length < 6)
    return 'Please use a real email address (e.g. gmail.com, yahoo.com, outlook.com)';

  return '';
}

function validatePassword(pw) {
  if (!pw) return 'Password is required';
  if (pw.length < 8) return 'Must be at least 8 characters';
  return '';
}

// The ONLY credentials accepted when signing in via the Admin button.
const ADMIN_EMAIL = 'admin@cinema.com';
const ADMIN_PASSWORD = 'admin1234';

export default function Login() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const wasExpired = searchParams.get('expired') === '1';
  const [mode, setMode] = useState('customer');     // 'customer' | 'admin'
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [touched, setTouched] = useState({});
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const emailError = validateEmail(email);
  const passwordError = validatePassword(password);

  function touch(field) {
    setTouched(t => ({ ...t, [field]: true }));
  }

  function fieldClass(err, field) {
    if (!touched[field]) return '';
    return err ? 'input-error' : 'input-valid';
  }

  async function finishLogin(token) {
    setToken(token);
    const me = await api.me();
    setRole(me.role);
    navigate(me.role === 'admin' ? '/admin' : '/');
    window.location.reload();
  }

  async function submit(e) {
    e.preventDefault();
    setTouched({ email: true, password: true });
    if (emailError || passwordError) return;

    // In admin mode, ONLY the seeded admin credentials are accepted.
    if (mode === 'admin' && (email !== ADMIN_EMAIL || password !== ADMIN_PASSWORD)) {
      setError('Invalid admin credentials. Access denied.');
      return;
    }

    setBusy(true);
    setError('');
    try {
      const res = await api.login({ email, password });
      await finishLogin(res.access_token);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  function switchMode(newMode) {
    setMode(newMode);
    setEmail('');
    setPassword('');
    setTouched({});
    setError('');
  }

  return (
    <div className="auth-form">
      <h2>Sign in {mode === 'admin' ? '— Admin' : ''}</h2>

      {wasExpired && (
        <div style={{
          background: 'rgba(249,168,37,0.15)',
          border: '1px solid #f9a825',
          color: '#f9a825',
          padding: '10px 12px',
          borderRadius: 8,
          marginBottom: 16,
          fontSize: 13,
        }}>
          Your session has expired. Please sign in again.
        </div>
      )}

      <div style={{ display: 'flex', gap: 10, marginBottom: 18 }}>
        <button
          type="button"
          onClick={() => switchMode('admin')}
          disabled={busy}
          className={mode === 'admin' ? '' : 'secondary'}
          style={{ flex: 1 }}
        >
          🛡️ Admin
        </button>
        <button
          type="button"
          onClick={() => switchMode('customer')}
          disabled={busy}
          className={mode === 'customer' ? '' : 'secondary'}
          style={{ flex: 1 }}
        >
          🎬 Customer
        </button>
      </div>

      {mode === 'admin' ? (
        <div style={{
          background: 'rgba(229,9,20,0.10)',
          border: '1px solid var(--accent)',
          color: 'var(--text)',
          padding: '10px 12px',
          borderRadius: 8,
          marginBottom: 16,
          fontSize: 13,
        }}>
          🛡️ Admin sign-in. Enter your administrator email and password.
        </div>
      ) : (
        <p className="muted" style={{ fontSize: 12, marginBottom: 16 }}>
          Customer sign-in. Enter your account email and password, or <Link to="/register">register</Link>.
        </p>
      )}

      <form onSubmit={submit}>
        {error && <p className="error">{error}</p>}

        {/* Email */}
        <div className="field">
          <label>Email</label>
          <input
            type="text"
            value={email}
            onChange={e => setEmail(e.target.value)}
            onBlur={() => touch('email')}
            className={fieldClass(emailError, 'email')}
            placeholder="you@example.com"
          />
          {touched.email && emailError && <p className="field-error">{emailError}</p>}
        </div>

        {/* Password */}
        <div className="field">
          <label>Password</label>
          <input
            type="password"
            value={password}
            onChange={e => setPassword(e.target.value)}
            onBlur={() => touch('password')}
            className={fieldClass(passwordError, 'password')}
            placeholder="Enter your password"
          />
          {touched.password && passwordError && <p className="field-error">{passwordError}</p>}
        </div>

        <button disabled={busy} style={{ marginTop: 8 }}>
          {busy ? 'Signing in…' : 'Sign in'}
        </button>
        <p className="muted" style={{ marginTop: 14 }}>
          No account? <Link to="/register">Register as customer</Link>
        </p>
      </form>
    </div>
  );
}
