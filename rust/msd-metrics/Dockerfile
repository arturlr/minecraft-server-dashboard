# Multi-stage build for msd-metrics
# Stage 1: Builder
FROM rust:1.85-alpine AS builder

# Install build dependencies
RUN apk add --no-cache \
    musl-dev \
    pkgconfig

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
    tzdata

# Create non-root user
RUN addgroup -g 1001 metrics && \
    adduser -D -u 1001 -G metrics metrics

# Copy binary from builder
COPY --from=builder /build/target/x86_64-unknown-linux-musl/release/msd-metrics /usr/local/bin/msd-metrics

# Set ownership
RUN chown metrics:metrics /usr/local/bin/msd-metrics && \
    chmod +x /usr/local/bin/msd-metrics

# Switch to non-root user
USER metrics

# Set environment variables (allow runtime override)
ENV RUST_LOG=${RUST_LOG:-info}

# Health check - verify process is running
HEALTHCHECK --interval=60s --timeout=5s --start-period=30s --retries=3 \
    CMD pgrep -x msd-metrics || exit 1

# Run the binary
ENTRYPOINT ["/usr/local/bin/msd-metrics"]
