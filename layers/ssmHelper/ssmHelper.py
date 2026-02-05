import logging
import os

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class SSMHelper:
    def __init__(self, queue_url=None, bootstrap_doc_name=None):
        """Initialize SSM Helper (queue_url deprecated, kept for compatibility)."""
        logger.info("------- SSMHelper Class Initialization")
        self.bootstrap_doc_name = bootstrap_doc_name or os.getenv('BOOTSTRAP_SSM_DOC_NAME')
    
    def get_bootstrap_script(self, support_bucket, script_version, run_command, project_name, env_name):
        """Generate inline bootstrap script for AWS-RunShellScript."""
        return f"""#!/bin/bash
set +e

SCRIPT_VERSION="{script_version}"
REGION=$(curl -s http://169.254.169.254/latest/meta-data/placement/region)
INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)

echo "=== Bootstrap Script Version: $SCRIPT_VERSION ==="
echo "=== Instance: $INSTANCE_ID ==="
echo "[$(date)] Starting package installation"

# Update and install packages
apt-get update
apt-get install -y jq zip unzip net-tools wget screen openjdk-21-jre-headless

# Install AWS CLI
if ! command -v aws >/dev/null 2>&1; then
    mkdir -p /usr/share/collectd
    touch /usr/share/collectd/types.db
    curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
    unzip awscliv2.zip
    ./aws/install
    rm -rf aws awscliv2.zip
fi

echo "[$(date)] Packages installed"

# Download helper functions
aws s3 cp s3://{support_bucket}/scripts/$SCRIPT_VERSION/00-bootstrap-helper.sh /tmp/bootstrap-helper.sh --region $REGION
chmod +x /tmp/bootstrap-helper.sh
source /tmp/bootstrap-helper.sh {project_name} {env_name}

CRITICAL_FAILURE=0

# Setup Metrics
echo "=== Setting up Metrics ==="
aws s3 cp s3://{support_bucket}/scripts/$SCRIPT_VERSION/05-setup-metrics.sh /tmp/setup-metrics.sh --region $REGION
chmod +x /tmp/setup-metrics.sh
run_stage "metrics" /tmp/setup-metrics.sh {support_bucket} || echo "⚠ Metrics setup failed"

# Setup Log Server
echo "=== Setting up Log Server ==="
aws s3 cp s3://{support_bucket}/scripts/$SCRIPT_VERSION/07-setup-log-server.sh /tmp/setup-log-server.sh --region $REGION
chmod +x /tmp/setup-log-server.sh
run_stage "logs" /tmp/setup-log-server.sh {support_bucket} || echo "⚠ Log server setup failed"

# Setup Minecraft Service (CRITICAL)
echo "=== Setting up Minecraft Service ==="
aws s3 cp s3://{support_bucket}/scripts/$SCRIPT_VERSION/09-setup-minecraft-service.sh /tmp/setup-minecraft-service.sh --region $REGION
chmod +x /tmp/setup-minecraft-service.sh
if ! run_stage "minecraft" /tmp/setup-minecraft-service.sh "{run_command}"; then
    echo "✗ Minecraft setup failed - CRITICAL"
    CRITICAL_FAILURE=1
fi

# Update Status
aws s3 cp s3://{support_bucket}/scripts/$SCRIPT_VERSION/10-update-bootstrap-status.sh /tmp/update-bootstrap-status.sh --region $REGION
chmod +x /tmp/update-bootstrap-status.sh

if [ $CRITICAL_FAILURE -eq 0 ]; then
    /tmp/update-bootstrap-status.sh {project_name} {env_name}
    update_bootstrap_stage "complete" "completed"
    echo "=== Bootstrap completed successfully ==="
    exit 0
else
    update_bootstrap_stage "complete" "failed" "Critical stage failed"
    echo "=== Bootstrap FAILED ==="
    exit 1
fi
"""

