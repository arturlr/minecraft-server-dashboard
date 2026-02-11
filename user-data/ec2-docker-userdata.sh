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

install_aws_cli() {
    echo ">>> [FUNCTION START] install_aws_cli"
    if command_exists aws; then
        echo "AWS CLI already installed"
        aws --version
        echo "<<< [FUNCTION END] install_aws_cli (skipped - already installed)"
        return 0
    fi
    
    echo "Installing AWS CLI..."
    apt-get update && apt-get install -y awscli
    
    if command_exists aws; then
        echo "✓ AWS CLI installed successfully"
        aws --version
        echo "<<< [FUNCTION END] install_aws_cli"
        return 0
    else
        error_log "Failed to install AWS CLI"
        echo "<<< [FUNCTION END] install_aws_cli (FAILED)"
        return 1
    fi
}

install_docker() {
    echo ">>> [FUNCTION START] install_docker"
    echo "Installing Docker..."
    if command_exists docker; then
        echo "Docker already installed"
        echo "<<< [FUNCTION END] install_docker (skipped - already installed)"
        return 0
    fi
    apt-get update && apt-get install -y docker.io && systemctl start docker && systemctl enable docker
    echo "<<< [FUNCTION END] install_docker"
}

install_docker_compose() {
    echo ">>> [FUNCTION START] install_docker_compose"
    echo "Installing Docker Compose..."
    if command_exists docker-compose; then
        echo "Docker Compose already installed"
        echo "<<< [FUNCTION END] install_docker_compose (skipped - already installed)"
        return 0
    fi
    curl -L "https://github.com/docker/compose/releases/download/v${DOCKER_COMPOSE_VERSION}/docker-compose-linux-x86_64" \
        -o /usr/local/bin/docker-compose && chmod +x /usr/local/bin/docker-compose
    echo "<<< [FUNCTION END] install_docker_compose"
}

setup_ebs_volume() {
    echo ">>> [FUNCTION START] setup_ebs_volume"
    echo "Setting up EBS volume..."
    if mount | grep -q "$MOUNT_POINT"; then
        echo "Already mounted"
        echo "<<< [FUNCTION END] setup_ebs_volume (skipped - already mounted)"
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
        echo "EBS device not found, waiting..."
        MAX_WAIT=300
        WAIT=0
        SLEEP=2
        while [ ! -e "$EBS_DEVICE" ] && [ $WAIT -lt $MAX_WAIT ]; do
            sleep $SLEEP
            WAIT=$((WAIT + SLEEP))
            [ $SLEEP -lt 16 ] && SLEEP=$((SLEEP * 2))
        done
    fi
    
    [ ! -e "$EBS_DEVICE" ] && { error_log "EBS device not found"; echo "<<< [FUNCTION END] setup_ebs_volume (FAILED)"; return 1; }
    
    # Get UUID
    UUID=$(blkid -s UUID -o value "$EBS_DEVICE" 2>/dev/null)
    [ -z "$UUID" ] && mkfs -t ext4 "$EBS_DEVICE" && UUID=$(blkid -s UUID -o value "$EBS_DEVICE")
    
    mkdir -p "$MOUNT_POINT"
    mount "$EBS_DEVICE" "$MOUNT_POINT"
    grep -q "$UUID" /etc/fstab || echo "UUID=$UUID $MOUNT_POINT ext4 defaults,nofail 0 2" >> /etc/fstab
    echo "<<< [FUNCTION END] setup_ebs_volume"
}

download_docker_compose() {
    echo ">>> [FUNCTION START] download_docker_compose"
    echo "Downloading docker-compose.yml from S3..."
    
    # Validate SUPPORT_BUCKET is set
    if [ -z "$SUPPORT_BUCKET" ]; then
        error_log "SUPPORT_BUCKET environment variable is not set"
        echo "Available environment variables:"
        env | grep -E "(SUPPORT_BUCKET|AWS_|INSTANCE_)" || echo "No relevant env vars found"
        echo "<<< [FUNCTION END] download_docker_compose (FAILED - missing SUPPORT_BUCKET)"
        return 1
    fi
    
    echo "Source: s3://${SUPPORT_BUCKET}/docker-compose.yml"
    echo "Destination: /opt/minecraft-dashboard/docker-compose.yml"
    
    mkdir -p /opt/minecraft-dashboard && chmod 750 /opt/minecraft-dashboard
    
    if aws s3 cp "s3://${SUPPORT_BUCKET}/docker-compose.yml" /opt/minecraft-dashboard/docker-compose.yml --region "$AWS_REGION" 2>>"$SECURE_LOG"; then
        echo "✓ Successfully downloaded docker-compose.yml"
        ls -lh /opt/minecraft-dashboard/docker-compose.yml
        echo "<<< [FUNCTION END] download_docker_compose"
        return 0
    else
        error_log "Failed to download docker-compose.yml from S3"
        echo "Checking if file exists in S3..."
        aws s3 ls "s3://${SUPPORT_BUCKET}/docker-compose.yml" --region "$AWS_REGION" 2>&1 | tee -a "$SECURE_LOG"
        echo "Checking IAM permissions..."
        aws sts get-caller-identity 2>&1 | tee -a "$SECURE_LOG"
        echo "<<< [FUNCTION END] download_docker_compose (FAILED)"
        return 1
    fi
}

create_env_file() {
    echo ">>> [FUNCTION START] create_env_file"
    echo "Creating environment files and secrets..."
    mkdir -p /opt/minecraft-dashboard/secrets && chmod 700 /opt/minecraft-dashboard/secrets
    
    # JWT secret
    echo "Fetching JWT secret from SSM..."
    TEMP=$(mktemp -p /opt/minecraft-dashboard/secrets) && chmod 600 "$TEMP"
    aws ssm get-parameter --name "/minecraft-dashboard/jwt-secret" --with-decryption --region "$AWS_REGION" --query 'Parameter.Value' --output text > "$TEMP" 2>>"$SECURE_LOG"
    touch /opt/minecraft-dashboard/secrets/jwt_secret.txt && chmod 600 /opt/minecraft-dashboard/secrets/jwt_secret.txt
    cat "$TEMP" > /opt/minecraft-dashboard/secrets/jwt_secret.txt && rm -f "$TEMP"
    echo "✓ JWT secret saved"
    
    # RCON password
    echo "Fetching RCON password from SSM..."
    TEMP=$(mktemp -p /opt/minecraft-dashboard/secrets) && chmod 600 "$TEMP"
    aws ssm get-parameter --name "/minecraft-dashboard/rcon-password" --with-decryption --region "$AWS_REGION" --query 'Parameter.Value' --output text > "$TEMP" 2>>"$SECURE_LOG"
    touch /opt/minecraft-dashboard/secrets/rcon_password.txt && chmod 600 /opt/minecraft-dashboard/secrets/rcon_password.txt
    cat "$TEMP" > /opt/minecraft-dashboard/secrets/rcon_password.txt && rm -f "$TEMP"
    echo "✓ RCON password saved"
    
    # .env file
    echo "Creating .env file..."
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
    echo "✓ .env file created"
    echo "<<< [FUNCTION END] create_env_file"
}

install_cloudwatch_agent() {
    echo ">>> [FUNCTION START] install_cloudwatch_agent"
    if [ -f /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl ]; then
        echo "CloudWatch agent already installed"
        echo "<<< [FUNCTION END] install_cloudwatch_agent (skipped - already installed)"
        return 0
    fi
    echo "Installing CloudWatch agent..."
    wget https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb -O /tmp/cw.deb 2>>"$SECURE_LOG"
    dpkg -i /tmp/cw.deb
    echo "<<< [FUNCTION END] install_cloudwatch_agent"
}

ecr_login() {
    echo ">>> [FUNCTION START] ecr_login"
    echo "Logging into ECR registry: $ECR_REGISTRY"
    TEMP=$(mktemp) && chmod 600 "$TEMP"
    aws ecr get-login-password --region "$AWS_REGION" > "$TEMP" 2>>"$SECURE_LOG"
    docker login --username AWS --password-stdin "$ECR_REGISTRY" < "$TEMP" 2>>"$SECURE_LOG"
    rm -f "$TEMP"
    echo "<<< [FUNCTION END] ecr_login"
}

start_containers() {
    echo ">>> [FUNCTION START] start_containers"
    cd /opt/minecraft-dashboard || { error_log "Failed to cd to /opt/minecraft-dashboard"; echo "<<< [FUNCTION END] start_containers (FAILED)"; return 1; }
    
    if docker-compose ps | grep -q "Up"; then
        echo "Containers already running"
        echo "<<< [FUNCTION END] start_containers (skipped - already running)"
        return 0
    fi
    
    echo "Pulling Docker images..."
    docker-compose pull 2>>"$SECURE_LOG"
    echo "Starting containers..."
    docker-compose up -d 2>>"$SECURE_LOG"
    echo "<<< [FUNCTION END] start_containers"
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
    echo ">>> [FUNCTION START] verify_services"
    echo "Waiting 60 seconds for services to start..."
    sleep 60
    echo "Container status:"
    docker-compose ps
    echo "Checking ports..."
    ss -tuln | grep ":25565" && echo "✓ Minecraft ready" || echo "✗ Minecraft port not listening"
    ss -tuln | grep ":25566" && echo "✓ Logs ready" || echo "✗ Logs port not listening"
    echo "Checking health endpoint..."
    curl -s http://localhost:25566/health | grep -q "OK" && echo "✓ Health check passed" || echo "✗ Health check failed"
    echo "<<< [FUNCTION END] verify_services"
}

main() {
    install_aws_cli || exit_code=1
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
