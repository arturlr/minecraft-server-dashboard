# Multi-stage build for smaller final image
FROM rust:1.75-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    pkg-config \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy source code
COPY Cargo.toml .
COPY src/ src/

# Build the application
RUN cargo build --release

# Runtime stage
FROM debian:bookworm-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    ca-certificates \
    iproute2 \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN useradd -r -s /bin/false minecraft

# Copy the binary
COPY --from=builder /app/target/release/msd-ecs-metrics /usr/local/bin/minecraft-monitor

# Create directories
RUN mkdir -p /tmp && chown minecraft:minecraft /tmp

# Switch to non-root user
USER minecraft

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD minecraft-monitor --health-check

# Default command
CMD ["minecraft-monitor"]
