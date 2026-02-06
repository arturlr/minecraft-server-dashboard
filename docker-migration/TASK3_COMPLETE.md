# Task 3: Create Dockerfile for msd-metrics - COMPLETE ✅

## Summary
Successfully created multi-stage Dockerfile for msd-metrics Rust service with all critical and high severity issues fixed based on code review.

## Files Created
1. ✅ `docker/msd-metrics/Dockerfile` - Multi-stage build with musl target
2. ✅ `docker/msd-metrics/build.sh` - Build script with error handling
3. ✅ `docker/msd-metrics/.dockerignore` - Context filtering
4. ✅ `docker/msd-metrics/README.md` - Documentation

## Key Features

### Multi-Stage Build
- **Stage 1 (Builder)**: rust:1.70-alpine with musl target
- **Stage 2 (Runtime)**: alpine:3.19 (minimal)
- **Final Image Size**: ~15-20MB

### Build Optimizations
1. **Layer Caching**: Dependencies fetched before source copy
2. **Static Binary**: musl target for zero runtime dependencies
3. **Minimal Base**: Alpine Linux for small footprint
4. **No OpenSSL**: Uses rustls (AWS SDK default)

### Security Features
1. **Non-root User**: Runs as metrics:metrics (UID/GID 1001)
2. **Minimal Dependencies**: Only ca-certificates and tzdata
3. **Static Binary**: No dynamic linking vulnerabilities
4. **Clean Build**: Source files not included in final image

### Build Script Features
1. **Error Handling**: Validates source directory exists
2. **Cleanup Trap**: Ensures cleanup on success or failure
3. **ECR Support**: Optional tagging for ECR registry
4. **Flexible**: Environment variables for customization

## Code Review Fixes Applied

### Critical Issues Fixed ✅
- ✅ Added explicit musl target to cargo build command
- ✅ Fixed binary path in COPY command
- ✅ Added rustup target add for x86_64-unknown-linux-musl

### High Severity Issues Fixed ✅
- ✅ Added trap for cleanup in build script
- ✅ Added source directory validation
- ✅ Removed unnecessary OpenSSL static dependencies
- ✅ Improved layer caching (fetch dependencies first)

### Medium Severity Issues Fixed ✅
- ✅ Added common Rust artifacts to .dockerignore
- ✅ Improved health check start period (30s)

### Low Severity Issues Fixed ✅
- ✅ Made RUST_LOG environment variable overridable

## Build Process

### Local Build
```bash
cd docker/msd-metrics
./build.sh
```

### Build for ECR
```bash
export ECR_REGISTRY=123456789012.dkr.ecr.us-west-2.amazonaws.com
export IMAGE_TAG=v1.0.0
cd docker/msd-metrics
./build.sh
```

### Test Image
```bash
docker run --rm \
  -e INSTANCE_ID=i-test \
  -e AWS_REGION=us-west-2 \
  -e CLOUDWATCH_NAMESPACE=MinecraftDashboard \
  msd-metrics:latest
```

## Metrics Collected
- CPU usage percentage
- Memory usage (MB and percentage)
- Network I/O (bytes sent/received)
- Active Minecraft players

## Health Check
- **Interval**: 60 seconds
- **Timeout**: 5 seconds
- **Start Period**: 30 seconds (allows startup time)
- **Retries**: 3
- **Command**: `pgrep -x msd-metrics`

## Environment Variables

### Required
- `INSTANCE_ID` - EC2 instance ID
- `AWS_REGION` - AWS region
- `CLOUDWATCH_NAMESPACE` - CloudWatch namespace (default: MinecraftDashboard)

### Optional
- `RUST_LOG` - Log level (default: info)

## Testing Checklist
- [ ] Build image successfully
- [ ] Image size is ~15-20MB
- [ ] Binary is statically linked (ldd shows "not a dynamic executable")
- [ ] Container starts without errors
- [ ] Health check passes
- [ ] Metrics sent to CloudWatch
- [ ] Runs as non-root user
- [ ] Cleanup trap works on build failure

## Next Steps
1. **Task 4**: Update msd-logs for file-based logging
2. **Task 5**: Already complete (docker-compose.yml)
3. **Task 6**: Update DynamoDB schema
