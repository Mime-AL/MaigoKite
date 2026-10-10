FROM golang:1.22-alpine AS go-builder

WORKDIR /build/gateway

COPY gateway/go.mod gateway/go.sum ./
RUN go mod download

COPY gateway/ ./
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o /out/maigokite-api ./cmd/gateway

FROM python:3.12-slim AS python-builder

WORKDIR /build

# Install uv (fast Python package manager)
RUN pip install --no-cache-dir uv

# Generate lockfile from pyproject.toml
COPY pyproject.toml ./
RUN uv lock

# Sync dependencies (main only for build stage)
RUN uv sync --frozen --no-dev

# Copy source and build wheel/sdist
COPY python/ ./python/
RUN uv build

FROM node:20-alpine AS vue-builder

WORKDIR /build

COPY web/package.json web/package-lock.json* ./
RUN npm ci

COPY web/ ./
RUN npm run build

FROM alpine:3.20

RUN apk add --no-cache nginx openssl

# Copy Go binary
COPY --from=go-builder /out/maigokite-api /usr/local/bin/maigokite-api

# Copy Python wheel (for runtime if needed)
COPY --from=python-builder /build/dist/*.whl /tmp/

# Copy Vue static files
COPY --from=vue-builder /build/dist /usr/share/nginx/html

# Nginx configuration
COPY deploy/nginx.conf /etc/nginx/http.d/default.conf

# Expose ports
EXPOSE 80 443

HEALTHCHECK --interval=30s --timeout=3s CMD wget -qO- http://localhost:80/health || exit 1

CMD ["nginx", "-g", "daemon off;"]
