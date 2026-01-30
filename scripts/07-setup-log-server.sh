#!/bin/bash
set -e

SUPPORT_BUCKET=$1
PROJECT_NAME=$2
ENVIRONMENT_NAME=$3

if [ -z "$SUPPORT_BUCKET" ] || [ -z "$PROJECT_NAME" ] || [ -z "$ENVIRONMENT_NAME" ]; then
    echo "Usage: $0 <support-bucket> <project-name> <environment-name>"
    exit 1
fi

# Get region (works for both Amazon Linux and Ubuntu)
if command -v ec2metadata &> /dev/null; then
    REGION=$(ec2metadata --availability-zone | sed 's/[a-z]$//')
else
    REGION=$(ec2-metadata --availability-zone | sed 's/[a-z]$//')
fi

echo "=== Setting up Minecraft Log Server ==="

if [ ! -f /usr/local/bin/msd-logs ]; then
  aws s3 cp s3://${SUPPORT_BUCKET}/msd-logs /usr/local/bin/msd-logs --region $REGION
  chmod +x /usr/local/bin/msd-logs
  echo "✓ msd-logs binary installed"
else
  echo "✓ msd-logs binary already exists"
fi

# Get Cognito User Pool ID from SSM
COGNITO_USER_POOL_ID=$(aws ssm get-parameter \
  --name "/${PROJECT_NAME}/${ENVIRONMENT_NAME}/cognito-user-pool-id" \
  --query 'Parameter.Value' \
  --output text \
  --region $REGION)

cat > /etc/systemd/system/msd-logs.service <<EOF
[Unit]
Description=Minecraft Log Server
After=network.target

[Service]
Type=simple
User=root
Environment="AWS_REGION=$REGION"
Environment="COGNITO_USER_POOL_ID=$COGNITO_USER_POOL_ID"
ExecStart=/usr/local/bin/msd-logs
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable msd-logs.service
systemctl start msd-logs.service

echo "✓ Log server service created and started"
systemctl status msd-logs.service --no-pager
