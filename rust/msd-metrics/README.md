# msd-metrics Docker Image

## Overview
Docker image for the msd-metrics service that collects and sends server metrics to CloudWatch.

## Build

### Local Build
```bash
cd docker/msd-metrics
./build.sh
```

### Build with ECR Tag
```bash
export ECR_REGISTRY=123456789012.dkr.ecr.us-west-2.amazonaws.com
export IMAGE_TAG=v1.0.0
./build.sh
```

## Image Details

### Base Images
- **Builder**: `rust:1.70-alpine` - Rust compiler with Alpine Linux
- **Runtime**: `alpine:3.19` - Minimal Alpine Linux

### Build Process
1. Multi-stage build for minimal image size
2. Static binary compiled with musl target (no runtime dependencies)
3. Non-root user (UID 1001, GID 1001)
4. CA certificates included for AWS API calls

### Image Size
- **Builder stage**: ~1.5GB (discarded)
- **Final image**: ~15-20MB

## Configuration

### Required Environment Variables
- `INSTANCE_ID` - EC2 instance ID
- `AWS_REGION` - AWS region (e.g., us-west-2)
- `CLOUDWATCH_NAMESPACE` - CloudWatch namespace (default: MinecraftDashboard)

### Optional Environment Variables
- `RUST_LOG` - Log level (default: info)

## Running

### Local Test
```bash
docker run --rm \
  -e INSTANCE_ID=i-1234567890abcdef0 \
  -e AWS_REGION=us-west-2 \
  -e CLOUDWATCH_NAMESPACE=MinecraftDashboard \
  msd-metrics:latest
```

### With AWS Credentials
```bash
docker run --rm \
  -e INSTANCE_ID=i-1234567890abcdef0 \
  -e AWS_REGION=us-west-2 \
  -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID \
  -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY \
  msd-metrics:latest
```

### In Docker Compose
See `docker-compose.yml` in project root.

## Metrics Collected

The service collects and sends the following metrics every 60 seconds:

- **CPU Usage**: Percentage of CPU utilization
- **Memory Usage**: Used memory in MB and percentage
- **Network I/O**: Bytes sent/received
- **Active Users**: Number of connected Minecraft players

## Health Check

Built-in health check runs every 60 seconds:
```bash
pgrep -x msd-metrics || exit 1
```

## Security

- Runs as non-root user (metrics:metrics, UID/GID 1001)
- Static binary with no runtime dependencies
- Minimal attack surface (Alpine base)
- No shell included in final image

## Troubleshooting

### Check if binary exists
```bash
docker run --rm msd-metrics:latest ls -l /usr/local/bin/msd-metrics
```

### View logs
```bash
docker logs <container-id>
```

### Test AWS connectivity
```bash
docker run --rm \
  -e INSTANCE_ID=test \
  -e AWS_REGION=us-west-2 \
  msd-metrics:latest
```

## CI/CD Integration

This image is built and pushed to ECR via CircleCI:
```yaml
- run:
    name: Build msd-metrics
    command: |
      cd docker/msd-metrics
      export ECR_REGISTRY=$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com
      export IMAGE_TAG=$CIRCLE_SHA1
      ./build.sh
      docker push $ECR_REGISTRY/msd-metrics:$IMAGE_TAG
```
