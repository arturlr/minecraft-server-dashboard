# Action Status Cleanup

## Summary
Removed the `ServerActionStatusTable` and related resolvers since action status was not being used by the frontend and was incorrectly configured to write to the wrong table.

## Changes Made

### 1. DynamoDB (`cfn/templates/dynamodb.yaml`)
- ❌ Removed `ServerActionStatusTable` resource
- ❌ Removed table exports

### 2. AppSync Configuration (`cfn/templates/lambdas.yaml`)
- ❌ Removed `ServerActionStatusTable` data source
- ❌ Removed `putServerActionStatusFunction` 
- ❌ Removed `getServerActionStatusFunction`
- ❌ Removed `putServerActionStatus` mutation resolver
- ❌ Removed `getServerActionStatus` query resolver

### 3. GraphQL Schema (`appsync/schema.graphql`)
- ✅ Kept `ServerActionStatus` type (for future use)
- ✅ Kept `onPutServerActionStatus` subscription (for future use)
- ❌ Commented out `putServerActionStatus` mutation
- ❌ Commented out `getServerActionStatus` query

### 4. Lambda Functions
- **`lambdas/serverAction/index.py`**: Simplified `send_status_to_appsync()` to only log status
- **`lambdas/serverActionProcessor/index.py`**: Simplified `send_to_appsync()` to only log status

## Current Behavior

### Action Status Tracking
- ✅ Status is **logged to CloudWatch** for monitoring
- ❌ Status is **not persisted** to DynamoDB
- ❌ Status is **not broadcast** via GraphQL subscriptions
- ✅ Frontend shows generic success/failure messages

### Real-time Updates (Still Working)
- ✅ `onChangeState` subscription - EC2 state changes (running/stopped)
- ✅ `onPutServerMetric` subscription - Performance metrics every 2 minutes

## Future Enhancement Path

If you want to add real-time action status tracking later:

1. **Recreate the table** with proper schema
2. **Implement subscription broadcast** (no persistence needed)
3. **Update frontend** to subscribe to `onPutServerActionStatus`
4. **Show real-time status** like "Starting server..." → "Server started!"

## Monitoring

Action status can still be monitored via:
- **CloudWatch Logs**: Search for "Action status:" in Lambda logs
- **CloudWatch Metrics**: Lambda invocations, errors, duration
- **CloudTrail**: API calls to EC2, EventBridge, etc.
