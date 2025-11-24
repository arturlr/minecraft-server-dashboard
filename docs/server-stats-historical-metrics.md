# Server Stats Dialog - Historical Metrics Feature

## Problem
The ServerStatsDialog was showing empty charts because it only subscribed to real-time metrics via AppSync subscriptions. Since metrics are published every 5 minutes, users had to wait up to 5 minutes to see any data when opening the dialog.

## Solution
Added a new GraphQL query `getServerMetrics` that fetches the last hour of historical metrics from CloudWatch when the dialog opens, providing immediate data visualization.

## Changes Made

### 1. New Lambda Function: `getServerMetrics`
**File**: `lambdas/getServerMetrics/index.py`

Fetches historical CloudWatch metrics for the last hour:
- **CPU**: `CPUUtilization` from `AWS/EC2` namespace
- **Memory**: `mem_used_percent` from `CWAgent` namespace (custom metric)
- **Network**: `NetworkPacketsIn` from `AWS/EC2` namespace
- **Users**: `UserCount` from `MinecraftDashboard` namespace (custom metric)

Returns data in ApexCharts format with 1-minute granularity.

### 2. GraphQL Schema Update
**File**: `appsync/schema.graphql`

Added new query:
```graphql
getServerMetrics(id: String!): ServerMetric
```

### 3. Frontend Query
**File**: `dashboard/src/graphql/queries.js`

Added `getServerMetrics` query to fetch historical data.

### 4. ServerCharts Component Updates
**File**: `dashboard/src/components/ServerCharts.vue`

- Added `loadHistoricalMetrics()` function to fetch data on mount
- Refactored metric processing into `processMetricData()` for reuse
- Fixed subscription lifecycle with proper watch and cleanup
- Fixed chart options mutation (direct property update instead of spreading)
- Added comprehensive logging for debugging

### 5. ServerStatsDialog Fix
**File**: `dashboard/src/components/ServerStatsDialog.vue`

Fixed invalid `variant="label"` prop on VChip components (changed to `variant="tonal"`).

### 6. Infrastructure Updates
**File**: `cfn/templates/lambdas.yaml`

Added:
- `GetServerMetrics` Lambda function resource
- `GetServerMetricsDataSource` AppSync data source
- `getServerMetricsFunction` AppSync function
- `getServerMetrics` resolver pipeline
- CloudWatch read permissions for the Lambda

## User Experience Improvement

**Before**: Users opened the dialog and saw empty charts for up to 5 minutes.

**After**: Users see the last hour of metrics immediately when opening the dialog, with real-time updates continuing via subscription.

## Deployment

To deploy these changes:

```bash
cd cfn
sam build
sam deploy
```

Then rebuild and deploy the frontend:

```bash
cd dashboard
npm run build
# Deploy to S3/CloudFront
```

## Technical Notes

- Historical data covers the last 1 hour with 1-minute intervals
- Real-time subscription continues to update charts as new metrics arrive
- Memory and User metrics require CloudWatch agent to be installed on EC2 instances
- If metrics don't exist, empty arrays are returned (graceful degradation)
