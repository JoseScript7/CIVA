# ---- Build Stage ----
FROM golang:1.22-alpine AS builder

RUN apk add --no-cache git ca-certificates

WORKDIR /build

# Cache dependencies
COPY go.mod go.sum ./
RUN go mod download

# Build
COPY . .
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build \
    -ldflags="-w -s -X main.version=$(git describe --tags --always 2>/dev/null || echo 'dev')" \
    -o /sentinel cmd/sentinel/main.go

# ---- Runtime Stage ----
FROM alpine:3.19

RUN apk add --no-cache ca-certificates tzdata curl

# Non-root user
RUN addgroup -g 1000 -S sentinel && \
    adduser -u 1000 -S sentinel -G sentinel

WORKDIR /app

COPY --from=builder /sentinel .

# GeoIP database mount point
RUN mkdir -p /data

USER sentinel

EXPOSE 8001

HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -sf http://localhost:8001/health || exit 1

ENTRYPOINT ["./sentinel"]
