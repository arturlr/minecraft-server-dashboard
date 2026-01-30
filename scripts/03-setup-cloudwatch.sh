#!/bin/bash
set -e

SUPPORT_BUCKET=$1

if [ -z "$SUPPORT_BUCKET" ]; then
    echo "Usage: $0 <support-bucket>"
    exit 1
fi

# Function to detect the Linux distribution
detect_distro() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        DISTRO=$ID
    elif [ -f /etc/lsb-release ]; then
        . /etc/lsb-release
        DISTRO=$DISTRIB_ID
    elif [ -f /etc/debian_version ]; then
        DISTRO="debian"
    elif [ -f /etc/redhat-release ]; then
        DISTRO="rhel"
    else
        DISTRO=$(uname -s)
    fi
    echo $DISTRO
}

# Get region based on distro
DISTRO=$(detect_distro)
case $DISTRO in
    amzn*|rhel*|centos*)
        REGION=$(ec2metadata --availability-zone | sed 's/[a-z]$//')
        ;;
    ubuntu*|debian*)
        REGION=$(ec2-metadata --availability-zone | sed 's/[a-z]$//')
        ;;
    *)
        echo "Unsupported distribution: $DISTRO"
        exit 1
        ;;
esac

# Download CloudWatch agent config from S3 using instance profile
echo "Downloading CloudWatch agent configuration..."
aws s3 cp s3://${SUPPORT_BUCKET}/amazon-cloudwatch-agent.json /tmp/amazon-cloudwatch-agent.json --region $REGION

# Start CloudWatch agent with the config file
echo "Starting CloudWatch agent..."
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
  -a fetch-config \
  -m ec2 \
  -s \
  -c file:/tmp/amazon-cloudwatch-agent.json

# Check status
echo "Checking CloudWatch agent status..."
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -m ec2 -a status