# Multi-stage build for msd-logs
# Stage 1: Builder
FROM rust:latest AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y musl-tools pkg-config && rm -rf /var/lib/apt/lists/*

# Add musl target
RUN rustup target add x86_64-unknown-linux-musl

# Set working directory
WORKDIR /build

# Copy manifests and fetch dependencies (better layer caching)
COPY Cargo.toml Cargo.lock* ./
RUN mkdir -p src && echo "fn main() {}" > src/main.rs
RUN cargo fetch --target x86_64-unknown-linux-musl

# Copy source code (replaces dummy main.rs)
COPY src ./src

# Build static binary with musl target
RUN cargo build --release --target x86_64-unknown-linux-musl

# Stage 2: Runtime
FROM alpine:3.19

# Install runtime dependencies
RUN apk add --no-cache \
    ca-certificates \
    wget

# Create non-root user
RUN addgroup -g 1002 logs && \
    adduser -D -u 1002 -G logs logs

# Copy binary from builder
COPY --from=builder /build/target/x86_64-unknown-linux-musl/release/msd-logs /usr/local/bin/msd-logs

# Set ownership
RUN chown logs:logs /usr/local/bin/msd-logs && \
    chmod +x /usr/local/bin/msd-logs

# Switch to non-root user
USER logs

# Expose HTTP port
EXPOSE 25566

# Set environment variables (allow runtime override)
ENV LOG_SERVICE_PORT=25566
ENV LOG_FILE_PATH=/logs/latest.log

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost:25566/health || exit 1

# Run the binary
ENTRYPOINT ["/usr/local/bin/msd-logs"]
