#!/bin/bash
set -e

PROJECT_NAME=$1
ENVIRONMENT_NAME=$2

if [ -z "$PROJECT_NAME" ] || [ -z "$ENVIRONMENT_NAME" ]; then
    echo "Usage: $0 <project-name> <environment-name>"
    exit 1
fi

echo "=== Updating Bootstrap Status in DynamoDB ==="

# Get instance ID and region
INSTANCE_ID=$(ec2metadata --instance-id)
REGION=$(ec2metadata --availability-zone | sed 's/[a-z]$//')
TABLE_NAME="${PROJECT_NAME}-${ENVIRONMENT_NAME}-CoreTable"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Verify CloudWatch agent is running
/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -m ec2 -a status
if /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -m ec2 -a status | jq -e '.status == "running"'; then
  echo "✓ CloudWatch agent is running"
else
  echo "ERROR: CloudWatch agent may not be running"
  exit 1
fi

# Verify msd-metrics binary exists and is executable
if [ ! -x /usr/local/bin/msd-metrics ]; then
  echo "ERROR: msd-metrics binary not found or not executable"
  exit 1
fi
echo "✓ msd-metrics binary is configured"

# Verify cron job is configured
if ! crontab -l | grep -q "msd-metrics"; then
  echo "ERROR: msd-metrics cron job not configured"
  exit 1
fi
echo "✓ msd-metrics cron job is configured"

# Update DynamoDB to mark as bootstrapped
echo "Updating DynamoDB table: $TABLE_NAME"
aws dynamodb update-item \
  --table-name "$TABLE_NAME" \
  --key "{\"PK\": {\"S\": \"SERVER#$INSTANCE_ID\"}, \"SK\": {\"S\": \"METADATA\"}}" \
  --update-expression "SET isBootstrapComplete = :bootstrapped, updatedAt = :timestamp" \
  --expression-attribute-values "{\":bootstrapped\": {\"BOOL\": true}, \":timestamp\": {\"S\": \"$TIMESTAMP\"}}" \
  --region "$REGION"

if [ $? -eq 0 ]; then
  echo "✓ Successfully marked instance as bootstrapped in DynamoDB"
  echo "Bootstrap process completed successfully!"
else
  echo "ERROR: Failed to update DynamoDB"
  exit 1
fi
