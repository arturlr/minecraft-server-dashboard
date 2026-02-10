#!/bin/bash
set -e

SUPPORT_BUCKET=$1

if [ -z "$SUPPORT_BUCKET" ]; then
    echo "Usage: $0 <support-bucket>"
    exit 1
fi

REGION=$(ec2metadata --availability-zone | sed 's/[a-z]$//')

if [ ! -f /usr/local/bin/msd-metrics ]; then
  # Download msd-metrics binary
  aws s3 cp s3://${SUPPORT_BUCKET}/msd-metrics /usr/local/bin/msd-metrics --region $REGION
  chmod +x /usr/local/bin/msd-metrics
  echo "msd-metrics binary installed"
fi

# Check if cron entry already exists before adding it
if ! crontab -l 2>/dev/null | grep -qF "/usr/local/bin/msd-metrics"; then
  (crontab -l 2>/dev/null; echo "*/1 * * * * /usr/local/bin/msd-metrics >/dev/null 2>&1") | crontab -
  echo "metrics cron job added"
else
  echo "metrics cron job already exists, skipping"
fi

# Display current crontab
echo ""
echo "=== Current Crontab ==="
crontab -l
