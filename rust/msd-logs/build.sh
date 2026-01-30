#!/bin/bash
set -e

echo "Building msd-logs..."

# Build for x86_64 Linux
cargo build --release --target x86_64-unknown-linux-musl

# Copy binary to project root
cp target/x86_64-unknown-linux-musl/release/msd-logs ../../msd-logs

echo "✓ Binary built: msd-logs"
