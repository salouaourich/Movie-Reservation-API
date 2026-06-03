import { useNavigate } from 'react-router-dom';

// Build a self-contained SVG poster from the movie title.
// No external service required — guaranteed to render even offline.
// Returns a data: URL that can be used as an <img src>.
function generatePoster(title) {
  const safeTitle = (title || 'Movie').trim();
  // Word-wrap the title onto up to 4 lines so long titles still fit.
  const words = safeTitle.split(/\s+/);
  const lines = [];
  let current = '';
  for (const w of words) {
    if ((current + ' ' + w).trim().length > 14 && current) {
      lines.push(current.trim());
      current = w;
    } else {
      current = (current + ' ' + w).trim();
    }
    if (lines.length === 3) break;
  }
  if (current) lines.push(current.trim());
  const displayLines = lines.slice(0, 4);

  // Pick an accent shade from the title hash so each placeholder feels unique.
  let hash = 0;
  for (let i = 0; i < safeTitle.length; i++) hash = (hash * 31 + safeTitle.charCodeAt(i)) >>> 0;
  const hue = hash % 360;

  const titleSvg = displayLines
    .map((line, i) => {
      const y = 360 + i * 60 - (displayLines.length - 1) * 30;
      const escaped = line.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
      return `<text x="250" y="${y}" font-family="Georgia,serif" font-size="44" font-weight="700" fill="#fff" text-anchor="middle">${escaped}</text>`;
    })
    .join('');

  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="500" height="750" viewBox="0 0 500 750">
    <defs>
      <linearGradient id="g" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%"   stop-color="hsl(${hue},45%,18%)"/>
        <stop offset="55%"  stop-color="hsl(${hue},35%,10%)"/>
        <stop offset="100%" stop-color="#0a0a0a"/>
      </linearGradient>
      <radialGradient id="r" cx="50%" cy="35%" r="55%">
        <stop offset="0%"   stop-color="rgba(229,9,20,0.35)"/>
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

export default function MovieCard({ movie }) {
  const navigate = useNavigate();
  const fallback = generatePoster(movie.title);
  return (
    <div className="movie-card" onClick={() => navigate(`/movies/${movie.id}/showings`)}>
      <img
        src={movie.poster_url || fallback}
        alt={movie.title}
        loading="lazy"
        decoding="async"
        onError={(e) => {
          if (e.target.src !== fallback) e.target.src = fallback;
        }}
      />
      <div className="meta">
        <h3>{movie.title}</h3>
        <div className="muted">
          {movie.genre || '—'} · {movie.rating || '—'} · {movie.duration_minutes}m
        </div>
      </div>
    </div>
  );
}
