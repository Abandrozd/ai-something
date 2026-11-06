FROM node:22-bookworm-slim

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

EXPOSE 5173

# Listen on all interfaces so the published port is reachable from the host.
# VITE_API_PROXY (set by Compose) points the dev proxy at the backend service.
CMD ["./node_modules/.bin/vite", "--host", "0.0.0.0", "--port", "5173", "--strictPort"]
