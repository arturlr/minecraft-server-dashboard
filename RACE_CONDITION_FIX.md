# DynamoDB Atomic Counter Fix for EventBridge Rule Race Condition

## Problem
Multiple concurrent Lambda invocations could race when enabling/disabling the scheduled EventBridge rule.

## Solution
Implemented atomic DynamoDB counter using **existing CoreTable** with `PK=InstanceCounter, SK=METADATA`.

### How It Works
1. **Instance starts** → Increment counter atomically
2. **Instance stops** → Decrement counter atomically (with conditional check)
3. **Counter reaches 1** (from 0) → Enable EventBridge rule
4. **Counter reaches 0** (from 1) → Disable EventBridge rule

## Files Changed

### 1. `lambdas/ec2StateHandler/index.py`
- Added `ddbHelper` import
- Uses `ddb.table.update_item()` with `PK=InstanceCounter, SK=METADATA`
- Atomic counter logic with conditional decrement

### 2. `cfn/templates/lambdas.yaml`
- Added `CORE_TABLE_NAME` environment variable (already had permissions)

## Deployment Steps

1. **Deploy CloudFormation stack**:
   ```bash
   cd cfn
   sam build
   sam deploy
   ```

2. **Initialize counter** (one-time setup):
   ```bash
   aws dynamodb put-item \
     --table-name <ProjectName>-<EnvironmentName>-CoreTable \
     --item '{"PK": {"S": "InstanceCounter"}, "SK": {"S": "METADATA"}, "count": {"N": "0"}}'
   ```

3. **Verify**: Start/stop instances and check CloudWatch logs for:
   - `Instance counter: 1` → `Enabled EventBridge Rule (first instance)`
   - `Instance counter: 0` → `Disabled EventBridge Rule (last instance)`

## Cost Impact
Negligible - uses existing CoreTable with no additional resources.
