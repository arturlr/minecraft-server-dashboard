#!/bin/bash

# Build script for ECS metrics

set -e

echo "Building ECS Minecraft metrics..."

# Build the binary
cargo build --release

echo "Build complete: target/release/msd-ecs-metrics"

# Build Docker image if requested
if [ "$1" = "--docker" ]; then
    echo "Building Docker image..."
    docker build -t minecraft-dashboard/metrics:latest .
    echo "Docker image built: minecraft-dashboard/metrics:latest"
fi

echo "Done!"
