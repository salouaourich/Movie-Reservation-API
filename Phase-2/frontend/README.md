# Frontend — Cinema Reservation

React + Vite single-page app. Talks to the FastAPI backend at `/api/v1`
(proxied to `http://localhost:8000` during dev — see `vite.config.js`).

## Run locally

```bash
npm install
npm run dev
```

Open http://localhost:5173

The backend must be running on http://localhost:8000 (start it with `docker compose up` from the project root).
