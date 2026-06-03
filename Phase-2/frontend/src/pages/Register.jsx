import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api, setToken, setRole } from '../api.js';

function validateFullName(name) {
  const v = name.trim();
  if (!v) return 'Full name is required';
  if (v.length < 3) return 'Must be at least 3 characters';
  if (v.length > 50) return 'Must be 50 characters or fewer';
  if (!/^[a-zA-Z\s'\-]+$/.test(v)) return "Only letters, spaces, hyphens, and apostrophes allowed";
  return '';
}

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
  if (pw.length > 128) return 'Must be 128 characters or fewer';
  if (!/[A-Z]/.test(pw)) return 'Must include at least one uppercase letter';
  if (!/[a-z]/.test(pw)) return 'Must include at least one lowercase letter';
  if (!/[0-9]/.test(pw)) return 'Must include at least one number';
  return '';
}

function passwordStrength(pw) {
  if (!pw) return 0;
  let score = 0;
  if (pw.length >= 8) score++;
  if (pw.length >= 12) score++;
  if (/[A-Z]/.test(pw)) score++;
  if (/[a-z]/.test(pw)) score++;
  if (/[0-9]/.test(pw)) score++;
  if (/[^A-Za-z0-9]/.test(pw)) score++;
  return score;
}

const STRENGTH_LABELS = ['', 'Weak', 'Weak', 'Fair', 'Good', 'Strong', 'Very strong'];
const STRENGTH_COLORS = ['', '#e53935', '#e53935', '#f9a825', '#66bb6a', '#4caf50', '#2e7d32'];

export default function Register() {
  const navigate = useNavigate();
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [touched, setTouched] = useState({});
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const fieldErrors = {
    fullName: validateFullName(fullName),
    email: validateEmail(email),
    password: validatePassword(password),
    confirm: !confirm ? 'Please confirm your password' : password !== confirm ? 'Passwords do not match' : '',
  };

  const strength = passwordStrength(password);
  const isFormValid = !fieldErrors.fullName && !fieldErrors.email && !fieldErrors.password && !fieldErrors.confirm;

  function touch(field) {
    setTouched(t => ({ ...t, [field]: true }));
  }

  function fieldClass(field) {
    if (!touched[field]) return '';
    return fieldErrors[field] ? 'input-error' : 'input-valid';
  }

  async function submit(e) {
    e.preventDefault();
    setTouched({ fullName: true, email: true, password: true, confirm: true });
    if (!isFormValid) return;
    setBusy(true);
    setError('');
    try {
      await api.register({ email, password, full_name: fullName.trim() });
      const res = await api.login({ email, password });
      setToken(res.access_token);
      setRole('customer');
      navigate('/');
      window.location.reload();
    } catch (err) {
      const detail = err.details?.errors?.[0]?.msg;
      setError(detail || err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="auth-form" onSubmit={submit}>
      <h2>Create an account</h2>
      {error && <p className="error">{error}</p>}

      {/* Full name */}
      <div className="field">
        <label>Full name</label>
        <input
          value={fullName}
          onChange={e => setFullName(e.target.value)}
          onBlur={() => touch('fullName')}
          className={fieldClass('fullName')}
          placeholder="e.g. Jane Smith"
          maxLength={50}
        />
        {touched.fullName && fieldErrors.fullName
          ? <p className="field-error">{fieldErrors.fullName}</p>
          : <p className="field-hint">{fullName.trim().length}/50 characters</p>
        }
      </div>

      {/* Email */}
      <div className="field">
        <label>Email</label>
        <input
          type="text"
          value={email}
          onChange={e => setEmail(e.target.value)}
          onBlur={() => touch('email')}
          className={fieldClass('email')}
          placeholder="you@example.com"
        />
        {touched.email && fieldErrors.email && <p className="field-error">{fieldErrors.email}</p>}
      </div>

      {/* Password */}
      <div className="field">
        <label>Password</label>
        <input
          type="password"
          value={password}
          onChange={e => setPassword(e.target.value)}
          onBlur={() => touch('password')}
          className={fieldClass('password')}
          placeholder="Min 8 chars, upper, lower, number"
        />
        {touched.password && fieldErrors.password && (
          <p className="field-error">{fieldErrors.password}</p>
        )}

        {/* Strength bar */}
        {password && (
          <div style={{ marginTop: 8 }}>
            <div style={{ display: 'flex', gap: 4, marginBottom: 4 }}>
              {[1, 2, 3, 4, 5, 6].map(i => (
                <div
                  key={i}
                  style={{
                    flex: 1, height: 4, borderRadius: 2,
                    background: i <= strength ? STRENGTH_COLORS[strength] : '#333',
                    transition: 'background 0.2s',
                  }}
                />
              ))}
            </div>
            <p style={{ fontSize: 11, color: STRENGTH_COLORS[strength], margin: 0 }}>
              {STRENGTH_LABELS[strength]}
            </p>
          </div>
        )}

        {/* Requirement checklist */}
        <ul className="pw-rules">
          <li style={{ color: password.length >= 8 ? '#4ade80' : '#B3B3B3' }}>
            {password.length >= 8 ? '✓' : '○'} At least 8 characters
          </li>
          <li style={{ color: /[A-Z]/.test(password) ? '#4ade80' : '#B3B3B3' }}>
            {/[A-Z]/.test(password) ? '✓' : '○'} Uppercase letter
          </li>
          <li style={{ color: /[a-z]/.test(password) ? '#4ade80' : '#B3B3B3' }}>
            {/[a-z]/.test(password) ? '✓' : '○'} Lowercase letter
          </li>
          <li style={{ color: /[0-9]/.test(password) ? '#4ade80' : '#B3B3B3' }}>
            {/[0-9]/.test(password) ? '✓' : '○'} At least one number
          </li>
        </ul>
      </div>

      {/* Confirm password */}
      <div className="field">
        <label>Confirm password</label>
        <input
          type="password"
          value={confirm}
          onChange={e => setConfirm(e.target.value)}
          onBlur={() => touch('confirm')}
          className={touched.confirm ? (fieldErrors.confirm ? 'input-error' : 'input-valid') : ''}
          placeholder="Repeat your password"
        />
        {touched.confirm && fieldErrors.confirm && (
          <p className="field-error">{fieldErrors.confirm}</p>
        )}
      </div>

      <button disabled={busy} style={{ marginTop: 8 }}>
        {busy ? 'Creating…' : 'Register'}
      </button>
      <p className="muted" style={{ marginTop: 14 }}>
        Already have an account? <Link to="/login">Sign in</Link>
      </p>
    </form>
  );
}
