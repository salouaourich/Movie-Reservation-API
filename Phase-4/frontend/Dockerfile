# Build the React (Vite) frontend, then serve with nginx.
#
# Two stages: node builds the static bundle, nginx serves it.
# VITE_API_BASE is baked in at build time — pass it via --build-arg in
# docker-compose / Render so the SPA knows where the API lives.

# ---------- Stage 1: build ----------
FROM node:20-alpine AS build

WORKDIR /app

ARG VITE_API_BASE=/api
ENV VITE_API_BASE=${VITE_API_BASE}

COPY package.json package-lock.json* ./
RUN npm ci || npm install

COPY . .
RUN npm run build


# ---------- Stage 2: serve ----------
FROM nginx:1.27-alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget -qO- http://127.0.0.1/ >/dev/null 2>&1 || exit 1
