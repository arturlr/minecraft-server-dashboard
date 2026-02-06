# Task 2: Configure itzg/minecraft-server Image

## Overview
Using the official `itzg/minecraft-server` Docker image instead of building a custom Dockerfile. This provides a mature, well-maintained solution with extensive configuration options.

## Configuration

### Docker Compose Service
- **Image**: `itzg/minecraft-server:latest` (from Docker Hub)
- **Container Name**: `minecraft`
- **Port**: 25565 (Minecraft server)
- **Volumes**:
  - `/mnt/minecraft-world:/data` - Persistent world data on EBS
  - `minecraft-logs:/data/logs` - Shared logs volume (read by msd-logs)

### Environment Variables

#### Required
- `EULA=TRUE` - Auto-accept Minecraft EULA
- `INSTANCE_ID` - EC2 instance ID (for CloudWatch)
- `AWS_REGION` - AWS region (for CloudWatch)
- `JWT_SECRET` - Secret for msd-logs authentication

#### Minecraft Configuration
- `VERSION` - Minecraft version (default: LATEST)
  - Examples: `LATEST`, `1.20.4`, `1.19.2`
- `MEMORY` - JVM memory allocation (default: 2G)
  - Examples: `2G`, `4G`, `8G`
- `TYPE` - Server type (default: VANILLA)
  - Options: `VANILLA`, `PAPER`, `FORGE`, `FABRIC`, `SPIGOT`, `BUKKIT`
- `ENABLE_RCON` - Enable remote console (default: true)
- `RCON_PASSWORD` - RCON password (default: minecraft)
- `LOG_TIMESTAMP` - Add timestamps to logs (default: true)
- `TZ` - Timezone (default: UTC)

#### ECR Configuration
- `ECR_REGISTRY` - ECR registry URL for custom images
- `IMAGE_TAG` - Docker image tag (default: latest)

### Health Check
- **Command**: `mc-health` (built-in itzg health check)
- **Interval**: 30 seconds
- **Timeout**: 10 seconds
- **Retries**: 3
- **Start Period**: 120 seconds (allows server startup time)

### Resource Limits
- **CPU Limit**: 2 cores
- **Memory Limit**: 3GB
- **CPU Reservation**: 1 core
- **Memory Reservation**: 2GB

### Logging
- **Driver**: awslogs (CloudWatch Logs)
- **Log Group**: `/minecraft-dashboard/minecraft`
- **Log Stream**: `${INSTANCE_ID}`

## itzg/minecraft-server Features

### Advantages
1. **100M+ pulls** - Battle-tested and widely used
2. **Active maintenance** - Regular updates and bug fixes
3. **Auto-downloads** - Automatically downloads server.jar
4. **Multiple server types** - Supports Vanilla, Paper, Forge, Fabric, etc.
5. **Built-in RCON** - Remote console for server management
6. **Health checks** - Built-in `mc-health` command
7. **Backup utilities** - Built-in backup scripts
8. **Plugin support** - Easy plugin/mod installation
9. **World management** - Automatic world download from URLs

### Configuration Flexibility
Change server type by updating environment variable:
```bash
# Switch to Paper (optimized Vanilla)
MINECRAFT_TYPE=PAPER

# Switch to Forge (with mods)
MINECRAFT_TYPE=FORGE
FORGE_VERSION=47.2.0

# Switch to Fabric (with mods)
MINECRAFT_TYPE=FABRIC
```

## Service Dependencies

### minecraft → msd-logs
- msd-logs reads from `minecraft-logs` volume
- Minecraft writes logs to `/data/logs/latest.log`
- msd-logs mounts volume as read-only

### minecraft → msd-metrics
- msd-metrics monitors system resources
- No direct dependency, runs independently

## Testing Locally

### Prerequisites
```bash
# Create .env file
cp .env.example .env

# Edit .env with your values
vim .env
```

### Start Services
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f minecraft

# Check health
docker-compose ps
```

### Connect to Server
```bash
# Get container IP (if not using host network)
docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' minecraft

# Connect with Minecraft client
# Server address: localhost:25565 (or EC2 public IP)
```

### Test RCON
```bash
# Install rcon-cli
docker exec minecraft rcon-cli

# Run commands
> list
> say Hello from RCON!
```

### Verify Logs
```bash
# Check log file exists
docker exec minecraft ls -lh /data/logs/

# View latest log
docker exec minecraft tail -f /data/logs/latest.log
```

## Deployment Checklist
- [x] docker-compose.yml created
- [x] .env.example created
- [x] Environment variables documented
- [x] Health checks configured
- [x] CloudWatch logging configured
- [x] Resource limits set
- [x] Volume mounts configured
- [x] Security fixes applied (Docker secrets, bridge network)
- [x] setup-secrets.sh script created
- [x] .gitignore updated to exclude secrets
- [ ] Run setup-secrets.sh to generate secrets
- [ ] Test locally with docker-compose up
- [ ] Verify Minecraft server starts
- [ ] Verify logs written to shared volume
- [ ] Verify health check passes
- [ ] Connect with Minecraft client

## Security Improvements Applied
1. **Docker Secrets**: RCON password and JWT secret use Docker secrets instead of environment variables
2. **Bridge Network**: Replaced host networking with isolated bridge network
3. **Resource Reservations**: Added minimum CPU/memory guarantees
4. **Health Dependencies**: msd-logs waits for minecraft to be healthy
5. **Auto-Create Log Groups**: CloudWatch log groups created automatically
6. **Secure Secret Generation**: setup-secrets.sh generates 256-bit random secrets
7. **Version 3.9**: Upgraded from deprecated 3.8
8. **Exact Health Checks**: pgrep uses -x flag for exact process matching
9. **Named Volume with Bind**: minecraft-data volume binds to /mnt/minecraft-world for EBS persistence

## Next Steps
1. **Task 3**: Create Dockerfile for msd-metrics
2. **Task 4**: Update msd-logs for file-based logging
3. **Task 5**: Already complete (docker-compose.yml created)
4. **Task 6**: Update DynamoDB schema
