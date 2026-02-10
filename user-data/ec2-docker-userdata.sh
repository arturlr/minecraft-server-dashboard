#!/bin/bash
# EC2 User Data Script for Minecraft Dashboard Docker Setup
# Fixed version with idempotency, secure secret handling, and proper error handling

set -o pipefail

LOG_FILE="/var/log/minecraft-docker-setup.log"
SECURE_LOG="/var/log/minecraft-docker-setup-secure.log"
exec 1> >(tee -a "$LOG_FILE")
exec 2>&1

echo "=== Minecraft Dashboard Docker Setup Started at $(date) ==="

# Configuration
INSTANCE_ID="${INSTANCE_ID:-$(curl -s http://169.254.169.254/latest/meta-data/instance-id)}"
AWS_REGION="${AWS_REGION:-$(curl -s http://169.254.169.254/latest/meta-data/placement/region)}"
SUPPORT_BUCKET="${SUPPORT_BUCKET}"
ECR_REGISTRY="${ECR_REGISTRY}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
EBS_DEVICE="${EBS_DEVICE:-/dev/xvdf}"
MOUNT_POINT="/mnt/minecraft-world"
DOCKER_COMPOSE_VERSION="${DOCKER_COMPOSE_VERSION:-2.24.5}"

echo "Instance ID: $INSTANCE_ID"
echo "Region: $AWS_REGION"

error_log() {
    echo "ERROR: $1" | tee -a "$SECURE_LOG" >&2
}

command_exists() {
    command -v "$1" >/dev/null 2>&1
}

install_docker() {
    echo "Installing Docker..."
    if command_exists docker; then
        echo "Docker already installed"
        return 0
    fi
    apt-get update && apt-get install -y docker.io && systemctl start docker && systemctl enable docker
}

install_docker_compose() {
    echo "Installing Docker Compose..."
    if command_exists docker-compose; then
        echo "Docker Compose already installed"
        return 0
    fi
    curl -L "https://github.com/docker/compose/releases/download/v${DOCKER_COMPOSE_VERSION}/docker-compose-linux-x86_64" \
        -o /usr/local/bin/docker-compose && chmod +x /usr/local/bin/docker-compose
}

setup_ebs_volume() {
    echo "Setting up EBS volume..."
    if mount | grep -q "$MOUNT_POINT"; then
        echo "Already mounted"
        return 0
    fi
    
    # Try multiple device names
    for device in /dev/xvdf /dev/nvme1n1 /dev/sdf; do
        if [ -e "$device" ]; then
            EBS_DEVICE="$device"
            echo "Found EBS device: $EBS_DEVICE"
            break
        fi
    done
    
    # Wait with exponential backoff if not found
    if [ ! -e "$EBS_DEVICE" ]; then
        MAX_WAIT=300
        WAIT=0
        SLEEP=2
        while [ ! -e "$EBS_DEVICE" ] && [ $WAIT -lt $MAX_WAIT ]; do
            sleep $SLEEP
            WAIT=$((WAIT + SLEEP))
            [ $SLEEP -lt 16 ] && SLEEP=$((SLEEP * 2))
        done
    fi
    
    [ ! -e "$EBS_DEVICE" ] && { error_log "EBS device not found"; return 1; }
    
    # Get UUID
    UUID=$(blkid -s UUID -o value "$EBS_DEVICE" 2>/dev/null)
    [ -z "$UUID" ] && mkfs -t ext4 "$EBS_DEVICE" && UUID=$(blkid -s UUID -o value "$EBS_DEVICE")
    
    mkdir -p "$MOUNT_POINT"
    mount "$EBS_DEVICE" "$MOUNT_POINT"
    grep -q "$UUID" /etc/fstab || echo "UUID=$UUID $MOUNT_POINT ext4 defaults,nofail 0 2" >> /etc/fstab
}

download_docker_compose() {
    mkdir -p /opt/minecraft-dashboard && chmod 750 /opt/minecraft-dashboard
    aws s3 cp "s3://${SUPPORT_BUCKET}/docker-compose.yml" /opt/minecraft-dashboard/docker-compose.yml --region "$AWS_REGION" 2>>"$SECURE_LOG"
}

create_env_file() {
    mkdir -p /opt/minecraft-dashboard/secrets && chmod 700 /opt/minecraft-dashboard/secrets
    
    # JWT secret
    TEMP=$(mktemp -p /opt/minecraft-dashboard/secrets) && chmod 600 "$TEMP"
    aws ssm get-parameter --name "/minecraft-dashboard/jwt-secret" --with-decryption --region "$AWS_REGION" --query 'Parameter.Value' --output text > "$TEMP" 2>>"$SECURE_LOG"
    touch /opt/minecraft-dashboard/secrets/jwt_secret.txt && chmod 600 /opt/minecraft-dashboard/secrets/jwt_secret.txt
    cat "$TEMP" > /opt/minecraft-dashboard/secrets/jwt_secret.txt && rm -f "$TEMP"
    
    # RCON password
    TEMP=$(mktemp -p /opt/minecraft-dashboard/secrets) && chmod 600 "$TEMP"
    aws ssm get-parameter --name "/minecraft-dashboard/rcon-password" --with-decryption --region "$AWS_REGION" --query 'Parameter.Value' --output text > "$TEMP" 2>>"$SECURE_LOG"
    touch /opt/minecraft-dashboard/secrets/rcon_password.txt && chmod 600 /opt/minecraft-dashboard/secrets/rcon_password.txt
    cat "$TEMP" > /opt/minecraft-dashboard/secrets/rcon_password.txt && rm -f "$TEMP"
    
    # .env file
    touch /opt/minecraft-dashboard/.env && chmod 600 /opt/minecraft-dashboard/.env
    cat > /opt/minecraft-dashboard/.env <<EOF
AWS_REGION=$AWS_REGION
INSTANCE_ID=$INSTANCE_ID
ECR_REGISTRY=$ECR_REGISTRY
IMAGE_TAG=$IMAGE_TAG
MINECRAFT_VERSION=LATEST
MINECRAFT_MEMORY=2G
MINECRAFT_TYPE=VANILLA
TIMEZONE=America/Los_Angeles
EOF
}

install_cloudwatch_agent() {
    [ -f /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl ] && return 0
    wget https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb -O /tmp/cw.deb 2>>"$SECURE_LOG"
    dpkg -i /tmp/cw.deb
}

ecr_login() {
    TEMP=$(mktemp) && chmod 600 "$TEMP"
    aws ecr get-login-password --region "$AWS_REGION" > "$TEMP" 2>>"$SECURE_LOG"
    docker login --username AWS --password-stdin "$ECR_REGISTRY" < "$TEMP" 2>>"$SECURE_LOG"
    rm -f "$TEMP"
}

start_containers() {
    cd /opt/minecraft-dashboard || return 1
    docker-compose ps | grep -q "Up" && return 0
    docker-compose pull 2>>"$SECURE_LOG" && docker-compose up -d 2>>"$SECURE_LOG"
}

create_docker_update_service() {
    echo "Creating systemd service for Docker updates on boot..."
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
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable docker-update.service
    echo "✓ Docker update service created and enabled"
}

verify_services() {
    sleep 60
    docker-compose ps
    ss -tuln | grep ":25565" && echo "✓ Minecraft ready"
    ss -tuln | grep ":25566" && echo "✓ Logs ready"
    curl -s http://localhost:25566/health | grep -q "OK" && echo "✓ Health check passed"
}

main() {
    install_docker || exit_code=1
    install_docker_compose || exit_code=1
    setup_ebs_volume || exit_code=1
    download_docker_compose || exit_code=1
    create_env_file || exit_code=1
    install_cloudwatch_agent || exit_code=1
    ecr_login || exit_code=1
    create_docker_update_service || exit_code=1
    start_containers || exit_code=1
    verify_services || exit_code=1
    echo "=== Setup Complete at $(date) ==="
}

main
