#!/bin/bash
# Migrate existing bootstrap-based Minecraft server to Docker
# Usage: sudo bash migrate-to-docker.sh [--rollback|--cleanup]

set -euo pipefail

LOG_FILE="/var/log/minecraft-docker-migration.log"
touch "$LOG_FILE" && chmod 640 "$LOG_FILE"
exec 1> >(tee -a "$LOG_FILE")
exec 2>&1

# Cleanup trap
TEMP_FILES=""
cleanup() {
    [ -n "$TEMP_FILES" ] && rm -f $TEMP_FILES
}
trap cleanup EXIT

echo "=== Minecraft Docker Migration Started at $(date) ==="

# ============================================================
# HANDLE FLAGS FIRST
# ============================================================

if [ "${1:-}" = "--rollback" ]; then
    echo "--- Rolling back to systemd services ---"
    cd /opt/minecraft-dashboard && docker-compose down 2>/dev/null || true
    systemctl disable docker-update.service 2>/dev/null || true
    for svc in minecraft msd-metrics msd-logs; do
        systemctl enable "$svc" 2>/dev/null || true
        systemctl start "$svc" 2>/dev/null || true
    done
    echo "Rollback complete. Systemd services restored."
    exit 0
fi

if [ "${1:-}" = "--cleanup" ]; then
    echo "--- Cleaning up old systemd services ---"
    for svc in minecraft msd-metrics msd-logs; do
        systemctl stop "$svc" 2>/dev/null || true
        systemctl disable "$svc" 2>/dev/null || true
        rm -f "/etc/systemd/system/${svc}.service"
    done
    systemctl daemon-reload
    echo "Cleanup complete. Old services removed."
    exit 0
fi

# ============================================================
# CONFIGURATION & VALIDATION
# ============================================================

INSTANCE_ID=$(ec2-metadata --instance-id | cut -d ' ' -f 2)
AWS_REGION=$(ec2-metadata --availability-zone | cut -d ' ' -f 2 | sed 's/.$//')
SUPPORT_BUCKET="${SUPPORT_BUCKET:?SUPPORT_BUCKET required}"
ECR_REGISTRY="${ECR_REGISTRY:?ECR_REGISTRY required}"
MOUNT_POINT="/mnt/minecraft-world"
DOCKER_COMPOSE_DIR="/opt/minecraft-dashboard"
COMPOSE_VERSION="${COMPOSE_VERSION:-2.24.5}"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)

error_exit() {
    echo "ERROR: $1" >&2
    echo "Migration FAILED at $(date). Check $LOG_FILE"
    exit 1
}

# Validate inputs
[[ "$SUPPORT_BUCKET" =~ ^[a-zA-Z0-9._-]+$ ]] || error_exit "Invalid SUPPORT_BUCKET format"
[[ "$ECR_REGISTRY" =~ ^[0-9]+\.dkr\.ecr\.[a-z0-9-]+\.amazonaws\.com$ ]] || error_exit "Invalid ECR_REGISTRY format"
[[ "$INSTANCE_ID" =~ ^i-[a-f0-9]+$ ]] || error_exit "Invalid instance ID"

# Detect existing Minecraft data directory
MINECRAFT_DATA=""
for dir in /home/minecraft /opt/minecraft /srv/minecraft; do
    if [ -d "$dir" ]; then
        MINECRAFT_DATA=$(realpath "$dir")
        break
    fi
done

# ============================================================
# PRE-MIGRATION CHECKS
# ============================================================

echo "--- Pre-migration checks ---"

[ "$(id -u)" -eq 0 ] || error_exit "Must run as root"
[ -n "$MINECRAFT_DATA" ] || error_exit "No Minecraft data directory found"
echo "Found Minecraft data: $MINECRAFT_DATA"

# Verify server is stopped
systemctl is-active minecraft.service >/dev/null 2>&1 && error_exit "Minecraft is running. Stop the server first."

# Check disk space
WORLD_SIZE=$(du -sm "$MINECRAFT_DATA" 2>/dev/null | cut -f1) || error_exit "Cannot calculate world size"
AVAILABLE=$(df -m /mnt | tail -1 | awk '{print $4}')
NEEDED=$((WORLD_SIZE * 3))
echo "World: ${WORLD_SIZE}MB, Available: ${AVAILABLE}MB, Needed: ${NEEDED}MB"
[ "$AVAILABLE" -gt "$NEEDED" ] || error_exit "Insufficient disk space"

# Check ports available
ss -tuln | grep -q ":25565 " && error_exit "Port 25565 already in use"
ss -tuln | grep -q ":25566 " && error_exit "Port 25566 already in use"

# Test AWS access
aws sts get-caller-identity --region "$AWS_REGION" >/dev/null 2>&1 || error_exit "AWS credentials not available"

# ============================================================
# BACKUP
# ============================================================

echo "--- Backing up world data to S3 ---"
aws s3 sync "$MINECRAFT_DATA" "s3://${SUPPORT_BUCKET}/backups/${INSTANCE_ID}/${TIMESTAMP}/" --region "$AWS_REGION" \
    || error_exit "Backup to S3 failed"
echo "Backup: s3://${SUPPORT_BUCKET}/backups/${INSTANCE_ID}/${TIMESTAMP}/"

# ============================================================
# STOP EXISTING SERVICES
# ============================================================

echo "--- Stopping existing services ---"
for svc in minecraft msd-metrics msd-logs; do
    if systemctl is-enabled "$svc" 2>/dev/null; then
        systemctl stop "$svc" 2>/dev/null || true
        systemctl disable "$svc"
        echo "Disabled $svc (kept for rollback)"
    fi
done

# ============================================================
# INSTALL DOCKER
# ============================================================

echo "--- Installing Docker ---"
if ! command -v docker >/dev/null 2>&1; then
    yum update -y && yum install -y docker
fi
systemctl start docker && systemctl enable docker

echo "--- Installing Docker Compose ---"
if ! command -v docker-compose >/dev/null 2>&1; then
    curl -L "https://github.com/docker/compose/releases/download/v${COMPOSE_VERSION}/docker-compose-linux-x86_64" \
        -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
fi

# ============================================================
# SETUP DOCKER ENVIRONMENT
# ============================================================

echo "--- Setting up Docker environment ---"
mkdir -p "$DOCKER_COMPOSE_DIR/secrets" "$MOUNT_POINT"
chmod 750 "$DOCKER_COMPOSE_DIR"
chmod 700 "$DOCKER_COMPOSE_DIR/secrets"

# Download docker-compose.yml with retry
for i in 1 2 3; do
    aws s3 cp "s3://${SUPPORT_BUCKET}/docker-compose.yml" "$DOCKER_COMPOSE_DIR/docker-compose.yml" --region "$AWS_REGION" && break
    [ "$i" -eq 3 ] && error_exit "Failed to download docker-compose.yml after 3 attempts"
    sleep $((i * 5))
done

# Fetch secrets atomically
fetch_secret() {
    local name="$1" dest="$2"
    local tmp
    tmp=$(mktemp) && chmod 600 "$tmp"
    TEMP_FILES="$TEMP_FILES $tmp"
    aws ssm get-parameter --name "$name" --with-decryption --region "$AWS_REGION" \
        --query 'Parameter.Value' --output text > "$tmp" \
        || error_exit "Failed to fetch secret: $name"
    mv "$tmp" "$dest"
    chmod 600 "$dest"
}

fetch_secret "/minecraft-dashboard/jwt-secret" "$DOCKER_COMPOSE_DIR/secrets/jwt_secret.txt"
fetch_secret "/minecraft-dashboard/rcon-password" "$DOCKER_COMPOSE_DIR/secrets/rcon_password.txt"

# Create .env
cat > "$DOCKER_COMPOSE_DIR/.env" <<EOF
AWS_REGION=$AWS_REGION
INSTANCE_ID=$INSTANCE_ID
ECR_REGISTRY=$ECR_REGISTRY
IMAGE_TAG=latest
MINECRAFT_VERSION=LATEST
MINECRAFT_MEMORY=2G
MINECRAFT_TYPE=VANILLA
TIMEZONE=America/Los_Angeles
EOF
chmod 600 "$DOCKER_COMPOSE_DIR/.env"

# ============================================================
# COPY WORLD DATA
# ============================================================

echo "--- Copying world data to $MOUNT_POINT ---"
rsync -a "$MINECRAFT_DATA/" "$MOUNT_POINT/" || error_exit "Failed to copy world data"

# Verify key files exist
[ -f "$MOUNT_POINT/server.properties" ] || echo "WARNING: server.properties not found in world data"
echo "World data copied"

# ============================================================
# CREATE SYSTEMD BOOT SERVICE
# ============================================================

echo "--- Creating Docker update service ---"
cat > /etc/systemd/system/docker-update.service << 'EOF'
[Unit]
Description=Pull and start Docker containers on boot
After=docker.service network-online.target
Requires=docker.service
Wants=network-online.target

[Service]
Type=oneshot
WorkingDirectory=/opt/minecraft-dashboard
ExecStartPre=/usr/local/bin/docker-compose pull
ExecStart=/usr/local/bin/docker-compose up -d
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable docker-update.service

# ============================================================
# ECR LOGIN AND START CONTAINERS
# ============================================================

echo "--- Logging into ECR ---"
aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "$ECR_REGISTRY"

echo "--- Starting containers ---"
cd "$DOCKER_COMPOSE_DIR"
docker-compose pull
docker-compose up -d

# ============================================================
# VERIFICATION
# ============================================================

echo "--- Verifying (waiting 60s for startup) ---"
sleep 60

ERRORS=0

RUNNING=$(docker-compose ps --format json 2>/dev/null | grep -c '"running"' || echo 0)
if [ "$RUNNING" -ge 2 ]; then
    echo "✓ $RUNNING containers running"
else
    echo "✗ Only $RUNNING containers running"
    ERRORS=$((ERRORS + 1))
fi

if ss -tuln | grep -q ":25565"; then
    echo "✓ Minecraft port 25565 listening"
else
    echo "✗ Port 25565 not listening (may still be starting)"
    ERRORS=$((ERRORS + 1))
fi

if curl -sf http://localhost:25566/health >/dev/null 2>&1; then
    echo "✓ msd-logs health check passed"
else
    echo "✗ msd-logs health check failed"
    ERRORS=$((ERRORS + 1))
fi

docker-compose ps

echo ""
echo "=== Migration Complete at $(date) ==="

if [ "$ERRORS" -gt 0 ]; then
    echo "WARNING: $ERRORS checks failed. Containers may still be starting."
    echo "Check: docker-compose ps"
else
    echo "✓ All checks passed!"
fi

echo ""
echo "ROLLBACK:  sudo bash $0 --rollback"
echo "CLEANUP:   sudo bash $0 --cleanup"
