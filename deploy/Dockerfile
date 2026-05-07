# Stage 1: Frontend
FROM node:22-alpine AS fe
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci --legacy-peer-deps
COPY frontend/ ./
RUN npm run build

# Stage 2: Backend
FROM golang:1.25-alpine AS be
WORKDIR /src
COPY backend/go.mod backend/go.sum ./
RUN go mod download
COPY backend/ ./
COPY --from=fe /app/dist ./internal/api/static/dist
RUN CGO_ENABLED=0 go build -ldflags='-s -w' -o /out/make-story ./cmd/server

# Stage 3: Runtime
FROM gcr.io/distroless/static-debian12:nonroot
COPY --from=be /out/make-story /make-story
EXPOSE 8080
USER nonroot
ENTRYPOINT ["/make-story"]
