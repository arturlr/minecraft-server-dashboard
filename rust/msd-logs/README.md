# msd-logs Docker Image

## Overview
Docker image for the msd-logs service that streams Minecraft server logs via HTTP API with JWT authentication.

## Changes from Original
- **File-based logging**: Reads from `/logs/latest.log` instead of journalctl
- **JWT secret validation**: Requires `JWT_SECRET` environment variable
- **Docker secrets support**: Can read JWT secret from Docker secrets file

## Build

### Local Build
```bash
cd docker/msd-logs
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
3. Non-root user (UID 1002, GID 1002)
4. wget included for health checks

### Image Size
- **Builder stage**: ~1.5GB (discarded)
- **Final image**: ~10-15MB

## Configuration

### Required Environment Variables
- `JWT_SECRET` - JWT secret for token validation (or use Docker secrets)

### Optional Environment Variables
- `LOG_SERVICE_PORT` - HTTP port (default: 25566)
- `LOG_FILE_PATH` - Path to Minecraft log file (default: /logs/latest.log)

### Docker Secrets
When using Docker secrets, the JWT_SECRET is read from `/run/secrets/jwt_secret`:
```yaml
secrets:
  - jwt_secret
```

## Running

### Local Test
```bash
# Create test log file
mkdir -p /tmp/test-logs
echo "Test log line 1" > /tmp/test-logs/latest.log
echo "Test log line 2" >> /tmp/test-logs/latest.log

# Run container
docker run --rm -p 25566:25566 \
  -e JWT_SECRET=test-secret \
  -v /tmp/test-logs:/logs:ro \
  msd-logs:latest
```

### Test Endpoints
```bash
# Health check
curl http://localhost:25566/health

# Get logs (requires JWT token)
TOKEN=$(echo -n '{"sub":"user@example.com","instance_id":"i-test"}' | base64)
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:25566/logs?lines=100"
```

### In Docker Compose
See `docker-compose.yml` in project root.

## API Endpoints

### GET /health
Health check endpoint (no authentication required).

**Response**: `200 OK` with body `"OK"`

### GET /logs?lines=N
Stream Minecraft logs (authentication required).

**Query Parameters**:
- `lines` - Number of lines to return (default: 100, max: 1000)

**Headers**:
- `Authorization: Bearer <JWT_TOKEN>` - Base64-encoded JWT token

**Response**: `200 OK` with log content as plain text

**JWT Token Format**:
```json
{
  "sub": "user@example.com",
  "instance_id": "i-1234567890abcdef0"
}
```

## Security

- Runs as non-root user (logs:logs, UID/GID 1002)
- Static binary with no runtime dependencies
- JWT token validation for log access
- Read-only volume mount for log files
- Minimal attack surface (Alpine base)

## Health Check

Built-in health check runs every 30 seconds:
```bash
wget --quiet --tries=1 --spider http://localhost:25566/health || exit 1
```

## Volume Mounts

The service requires a read-only mount of the Minecraft logs directory:
```yaml
volumes:
  - minecraft-logs:/logs:ro
```

The Minecraft container writes logs to this shared volume:
```yaml
volumes:
  - minecraft-logs:/data/logs
```

## Troubleshooting

### Check if log file exists
```bash
docker exec <container-id> ls -l /logs/latest.log
```

### View container logs
```bash
docker logs <container-id>
```

### Test log reading
```bash
docker exec <container-id> cat /logs/latest.log
```

### Verify JWT secret
```bash
# If using Docker secrets
docker exec <container-id> cat /run/secrets/jwt_secret
```

## CI/CD Integration

This image is built and pushed to ECR via CircleCI:
```yaml
- run:
    name: Build msd-logs
    command: |
      cd docker/msd-logs
      export ECR_REGISTRY=$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com
      export IMAGE_TAG=$CIRCLE_SHA1
      ./build.sh
      docker push $ECR_REGISTRY/msd-logs:$IMAGE_TAG
```
