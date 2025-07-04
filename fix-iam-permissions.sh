#!/bin/bash

# Script to fix IAM permissions for the ServerAction Lambda
# This script updates the CloudFormation stack to fix the "Fix It" button issue

echo "🔧 Fixing IAM permissions for ServerAction Lambda..."

# Navigate to the CloudFormation directory
cd cfn

# Check if samconfig.toml exists
if [ ! -f "samconfig.toml" ]; then
    echo "❌ Error: samconfig.toml not found. Please run this script from the project root."
    exit 1
fi

echo "📦 Building SAM application..."
sam build

if [ $? -ne 0 ]; then
    echo "❌ Error: SAM build failed"
    exit 1
fi

echo "🚀 Deploying updated CloudFormation stack..."
sam deploy

if [ $? -eq 0 ]; then
    echo "✅ Successfully updated IAM permissions!"
    echo "🎯 The 'Fix It' button should now work properly."
    echo ""
    echo "📋 What was fixed:"
    echo "   - Added iam:PassRole permission for the EC2 instance role"
    echo "   - ServerAction Lambda can now attach IAM profiles to EC2 instances"
    echo ""
    echo "🔄 Please test the 'Fix It' button in your dashboard."
else
    echo "❌ Error: Deployment failed"
    exit 1
fi