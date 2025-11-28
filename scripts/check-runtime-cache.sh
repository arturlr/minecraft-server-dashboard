#!/bin/bash

# Script to check and populate running minutes cache
# Usage: ./scripts/check-runtime-cache.sh [stack-name]

set -e

STACK_NAME="${1:-minecraftserverdashboard-dev}"

echo "=== Checking Running Minutes Cache Status ==="
echo "Stack: $STACK_NAME"
echo ""

# Get Lambda function name
LAMBDA_NAME=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --query "Stacks[0].Outputs[?OutputKey=='CalculateMonthlyRuntime'].OutputValue" \
  --output text 2>/dev/null || echo "")

if [ -z "$LAMBDA_NAME" ]; then
  echo "❌ CalculateMonthlyRuntime Lambda not found in stack outputs"
  echo "   The Lambda may not be deployed yet."
  echo ""
  echo "To deploy, run:"
  echo "  cd cfn && sam build && sam deploy"
  exit 1
fi

echo "✅ Found Lambda: $LAMBDA_NAME"
echo ""

# Check EventBridge rule
RULE_NAME="${STACK_NAME}-MonthlyRuntimeCalculationRule"
RULE_STATUS=$(aws events describe-rule \
  --name "$RULE_NAME" \
  --query "State" \
  --output text 2>/dev/null || echo "NOT_FOUND")

if [ "$RULE_STATUS" = "ENABLED" ]; then
  echo "✅ EventBridge rule is ENABLED"
elif [ "$RULE_STATUS" = "DISABLED" ]; then
  echo "⚠️  EventBridge rule is DISABLED"
  echo "   To enable: aws events enable-rule --name $RULE_NAME"
elif [ "$RULE_STATUS" = "NOT_FOUND" ]; then
  echo "❌ EventBridge rule not found: $RULE_NAME"
else
  echo "⚠️  EventBridge rule status: $RULE_STATUS"
fi
echo ""

# Check recent Lambda invocations
echo "Checking recent Lambda invocations..."
RECENT_INVOCATIONS=$(aws logs filter-log-events \
  --log-group-name "/aws/lambda/$(basename $LAMBDA_NAME)" \
  --start-time $(($(date +%s) - 86400))000 \
  --filter-pattern "calculateMonthlyRuntime Lambda started" \
  --query "events[*].timestamp" \
  --output text 2>/dev/null | wc -w || echo "0")

if [ "$RECENT_INVOCATIONS" -gt 0 ]; then
  echo "✅ Lambda has been invoked $RECENT_INVOCATIONS times in the last 24 hours"
else
  echo "⚠️  No Lambda invocations found in the last 24 hours"
  echo "   The cache may not be populated yet."
fi
echo ""

# Manually invoke Lambda to populate cache
echo "=== Manually Invoking Lambda to Populate Cache ==="
echo "This will calculate and cache running minutes for all servers..."
echo ""

RESPONSE=$(aws lambda invoke \
  --function-name "$LAMBDA_NAME" \
  --payload '{}' \
  --cli-binary-format raw-in-base64-out \
  /tmp/lambda-response.json 2>&1)

if [ $? -eq 0 ]; then
  echo "✅ Lambda invoked successfully"
  echo ""
  echo "Response:"
  cat /tmp/lambda-response.json | jq '.' 2>/dev/null || cat /tmp/lambda-response.json
  echo ""
  
  # Check for errors in response
  if grep -q '"statusCode": 200' /tmp/lambda-response.json; then
    echo "✅ Cache population completed successfully"
    echo ""
    echo "The running minutes should now appear in your dashboard."
    echo "Refresh your browser to see the updated values."
  else
    echo "⚠️  Lambda execution may have encountered errors"
    echo "   Check CloudWatch logs for details:"
    echo "   aws logs tail /aws/lambda/$(basename $LAMBDA_NAME) --follow"
  fi
else
  echo "❌ Failed to invoke Lambda"
  echo "$RESPONSE"
  exit 1
fi

rm -f /tmp/lambda-response.json

echo ""
echo "=== Next Steps ==="
echo "1. Refresh your dashboard to see updated running times"
echo "2. The cache will automatically update every hour"
echo "3. To check logs: aws logs tail /aws/lambda/$(basename $LAMBDA_NAME) --follow"
