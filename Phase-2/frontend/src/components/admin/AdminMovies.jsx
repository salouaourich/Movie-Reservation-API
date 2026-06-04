// Admin: list / create / edit / delete movies.

import { useEffect, useRef, useState } from 'react';
import { api } from '../../api.js';

// Same self-contained SVG generator as MovieCard.jsx so the admin sees
// the exact same nice placeholder when a poster URL is missing or broken.
function generatePoster(title) {
  const safeTitle = (title || 'Movie').trim();
  const words = safeTitle.split(/\s+/);
  const lines = [];
  let current = '';
  for (const w of words) {
    if ((current + ' ' + w).trim().length > 14 && current) {
      lines.push(current.trim()); current = w;
    } else {
      current = (current + ' ' + w).trim();
    }
    if (lines.length === 3) break;
  }
  if (current) lines.push(current.trim());
  const displayLines = lines.slice(0, 4);
  let hash = 0;
  for (let i = 0; i < safeTitle.length; i++) hash = (hash * 31 + safeTitle.charCodeAt(i)) >>> 0;
  const hue = hash % 360;
  const titleSvg = displayLines.map((line, i) => {
    const y = 360 + i * 60 - (displayLines.length - 1) * 30;
    const escaped = line.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    return `<text x="250" y="${y}" font-family="Georgia,serif" font-size="44" font-weight="700" fill="#fff" text-anchor="middle">${escaped}</text>`;
  }).join('');
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="500" height="750" viewBox="0 0 500 750">
    <defs>
      <linearGradient id="g" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="hsl(${hue},45%,18%)"/>
        <stop offset="55%" stop-color="hsl(${hue},35%,10%)"/>
        <stop offset="100%" stop-color="#0a0a0a"/>
      </linearGradient>
      <radialGradient id="r" cx="50%" cy="35%" r="55%">
        <stop offset="0%" stop-color="rgba(229,9,20,0.35)"/>
        <stop offset="100%" stop-color="rgba(229,9,20,0)"/>
      </radialGradient>
    </defs>
    <rect width="500" height="750" fill="url(#g)"/>
    <rect width="500" height="750" fill="url(#r)"/>
    <text x="250" y="110" font-family="Arial,sans-serif" font-size="14" font-weight="600" letter-spacing="6" fill="#E50914" text-anchor="middle">CINEMA</text>
    <line x1="180" y1="135" x2="320" y2="135" stroke="#E50914" stroke-width="2"/>
    ${titleSvg}
    <text x="250" y="680" font-family="Arial,sans-serif" font-size="12" letter-spacing="3" fill="rgba(255,255,255,0.45)" text-anchor="middle">NOW SHOWING</text>
  </svg>`;
  return `data:image/svg+xml;utf8,${encodeURIComponent(svg)}`;
}

// Max upload size — 1 MB raw. Base64 inflates this by ~33% in the request body.
const MAX_POSTER_BYTES = 1 * 1024 * 1024;
const ALLOWED_POSTER_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/gif'];

// Read a File from the upload <input> and return a base64 data URL string
// that can be stored in the existing poster_url field (no new endpoint needed).
function fileToDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(new Error('Could not read the file.'));
    reader.readAsDataURL(file);
  });
}

// Resize + recompress the uploaded image down to a movie-poster-sized JPEG
// (max 500×750, ~80 KB instead of 1 MB+) so the POST request travels fast
// even on Render's free tier and well within Cloudflare's body limits.
async function compressPoster(file) {
  const dataUrl = await fileToDataUrl(file);

  const img = await new Promise((resolve, reject) => {
    const i = new Image();
    i.onload  = () => resolve(i);
    i.onerror = () => reject(new Error('Could not decode the image.'));
    i.src = dataUrl;
  });

  // Target poster dimensions — keep the original aspect ratio.
  const MAX_W = 500;
  const MAX_H = 750;
  let { width, height } = img;
  const scale = Math.min(MAX_W / width, MAX_H / height, 1);
  width  = Math.round(width  * scale);
  height = Math.round(height * scale);

  const canvas = document.createElement('canvas');
  canvas.width  = width;
  canvas.height = height;
  const ctx = canvas.getContext('2d');
  ctx.fillStyle = '#000';                  // black background for transparent images
  ctx.fillRect(0, 0, width, height);
  ctx.drawImage(img, 0, 0, width, height);

  // JPEG 0.82 is a sweet spot — visually indistinguishable, ~85 KB on a typical
  // 500×750 poster (vs. ~1 MB+ raw upload).
  return canvas.toDataURL('image/jpeg', 0.82);
}

const emptyForm = {
  title: '',
  description: '',
  duration_minutes: 120,
  genre: '',
  rating: '',
  poster_url: '',
};

export default function AdminMovies() {
  const [items, setItems] = useState([]);
  const [error, setError] = useState('');
  const [msg, setMsg] = useState('');
  const [editing, setEditing] = useState(null);  // movie being edited, or null
  const [form, setForm] = useState(emptyForm);
  const [showForm, setShowForm] = useState(false);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef(null);

  async function handlePosterFile(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    setError('');
    if (!ALLOWED_POSTER_TYPES.includes(file.type)) {
      setError('Poster must be a JPG, PNG, WEBP, or GIF image.');
      e.target.value = '';
      return;
    }
    if (file.size > MAX_POSTER_BYTES) {
      setError(`Image is too large (${(file.size / 1024 / 1024).toFixed(1)} MB). Max 1 MB.`);
      e.target.value = '';
      return;
    }
    setUploading(true);
    try {
      // Compress to a small JPEG so the POST body stays small (~85 KB) — large
      // base64 uploads otherwise stall on Render's free tier.
      const dataUrl = await compressPoster(file);
      setForm((f) => ({ ...f, poster_url: dataUrl }));
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  }

  function clearPoster() {
    setForm((f) => ({ ...f, poster_url: '' }));
    if (fileInputRef.current) fileInputRef.current.value = '';
  }

  function load() {
    // page_size=100 is the backend's hard cap (le=100). Use it so newly
    // created movies aren't hidden behind default pagination.
    api.listMovies('?page_size=100')
      .then((d) => setItems(d.items))
      .catch((e) => setError(e.message));
  }
  useEffect(load, []);

  function startCreate() {
    setEditing(null);
    setForm(emptyForm);
    setShowForm(true);
    setMsg(''); setError('');
  }

  function startEdit(m) {
    setEditing(m);
    setForm({
      title: m.title,
      description: m.description || '',
      duration_minutes: m.duration_minutes,
      genre: m.genre || '',
      rating: m.rating || '',
      poster_url: m.poster_url || '',
    });
    setShowForm(true);
    setMsg(''); setError('');
  }

  async function submit(e) {
    e.preventDefault();
    setError(''); setMsg('');
    try {
      const payload = {
        ...form,
        duration_minutes: Number(form.duration_minutes),
      };
      if (editing) {
        await api.updateMovie(editing.id, payload);
        setMsg(`Movie "${form.title}" updated.`);
      } else {
        await api.createMovie(payload);
        setMsg(`Movie "${form.title}" created.`);
      }
      setShowForm(false);
      load();
    } catch (err) {
      setError(err.message);
    }
  }

  async function remove(m) {
    if (!confirm(`Soft-delete "${m.title}"? (sets is_active=false)`)) return;
    try {
      await api.deleteMovie(m.id);
      setMsg(`Deleted "${m.title}".`);
      load();
    } catch (e) {
      setError(e.message);
    }
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h2 style={{ margin: 0 }}>Movies</h2>
        <button onClick={startCreate}>+ New movie</button>
      </div>

      {error && <p className="error">{error}</p>}
      {msg && <p className="success">{msg}</p>}

      {showForm && (
        <form className="card" onSubmit={submit} style={{ marginBottom: 24 }}>
          <h3>{editing ? `Edit: ${editing.title}` : 'New movie'}</h3>
          <div style={{ display: 'grid', gap: 12, gridTemplateColumns: '1fr 1fr' }}>
            <div>
              <label>Title</label>
              <input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} required />
            </div>
            <div>
              <label>Duration (min)</label>
              <input type="number" min="1" value={form.duration_minutes}
                     onChange={(e) => setForm({ ...form, duration_minutes: e.target.value })} required />
            </div>
            <div>
              <label>Genre</label>
              <input value={form.genre} onChange={(e) => setForm({ ...form, genre: e.target.value })} placeholder="action, drama, …" />
            </div>
            <div>
              <label>Rating</label>
              <input value={form.rating} onChange={(e) => setForm({ ...form, rating: e.target.value })} placeholder="PG, PG-13, R" />
            </div>
            <div style={{ gridColumn: '1 / span 2' }}>
              <label>Movie poster</label>
              <div style={{ display: 'flex', gap: 14, alignItems: 'flex-start' }}>
                {/* Live preview */}
                <div style={{
                  width: 110,
                  height: 165,
                  borderRadius: 6,
                  background: '#1a1a1a',
                  border: '1px dashed #333',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#666',
                  fontSize: 11,
                  textAlign: 'center',
                  overflow: 'hidden',
                  flexShrink: 0,
                }}>
                  {form.poster_url ? (
                    <img
                      src={form.poster_url}
                      alt="poster preview"
                      style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                      onError={(e) => { e.target.style.display = 'none'; }}
                    />
                  ) : (
                    <span>No poster<br/>selected</span>
                  )}
                </div>

                {/* Inputs */}
                <div style={{ flex: 1 }}>
                  <p className="muted" style={{ fontSize: 12, margin: '0 0 6px' }}>
                    Upload an image from your computer (JPG, PNG, WEBP, GIF — max 1 MB):
                  </p>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/jpeg,image/png,image/webp,image/gif"
                    onChange={handlePosterFile}
                    disabled={uploading}
                    style={{ marginBottom: 10 }}
                  />

                  <p className="muted" style={{ fontSize: 12, margin: '8px 0 6px' }}>
                    …or paste an image URL:
                  </p>
                  <input
                    type="text"
                    placeholder="https://example.com/poster.jpg"
                    value={form.poster_url.startsWith('data:') ? '' : form.poster_url}
                    onChange={(e) => setForm({ ...form, poster_url: e.target.value })}
                  />

                  {form.poster_url && (
                    <button
                      type="button"
                      className="secondary"
                      onClick={clearPoster}
                      style={{ marginTop: 10, fontSize: 12, padding: '6px 12px' }}
                    >
                      Remove poster
                    </button>
                  )}
                  {uploading && <p className="muted" style={{ marginTop: 6, fontSize: 12 }}>Reading image…</p>}
                </div>
              </div>
            </div>
            <div style={{ gridColumn: '1 / span 2' }}>
              <label>Description</label>
              <textarea rows="3" value={form.description}
                        onChange={(e) => setForm({ ...form, description: e.target.value })} />
            </div>
          </div>
          <div style={{ marginTop: 14, display: 'flex', gap: 10 }}>
            <button type="submit">{editing ? 'Save' : 'Create'}</button>
            <button type="button" className="secondary" onClick={() => setShowForm(false)}>Cancel</button>
          </div>
        </form>
      )}

      <div className="grid movies">
        {items.map((m) => {
          const fallback = generatePoster(m.title);
          return (
            <div key={m.id} className="movie-card" style={{ cursor: 'default' }}>
              <img
                src={m.poster_url || fallback}
                alt={m.title}
                loading="lazy"
                decoding="async"
                onError={(e) => { if (e.target.src !== fallback) e.target.src = fallback; }}
              />
              <div className="meta">
                <h3>{m.title}</h3>
                <div className="muted" style={{ marginBottom: 10 }}>
                  {m.genre || '—'} · {m.rating || '—'} · {m.duration_minutes}m
                  {!m.is_active && (
                    <span style={{ color: '#f9a825', marginLeft: 6 }}>· inactive</span>
                  )}
                </div>
                <div style={{ display: 'flex', gap: 8 }}>
                  <button
                    className="secondary"
                    onClick={() => startEdit(m)}
                    style={{ flex: 1, padding: '6px 10px', fontSize: 13 }}
                  >
                    Edit
                  </button>
                  <button
                    className="secondary"
                    onClick={() => remove(m)}
                    style={{ flex: 1, padding: '6px 10px', fontSize: 13 }}
                  >
                    Delete
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
