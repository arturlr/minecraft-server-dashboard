# Design Document: User-Based Auto-Shutdown

## Overview

The User-Based Auto-Shutdown feature provides automatic EC2 instance termination based on active Minecraft player connections. The system monitors TCP connections on port 25565, publishes metrics to CloudWatch, and uses CloudWatch Alarms to trigger EC2 stop actions when player count falls below a configured threshold for a sustained period.

This design leverages existing AWS services (CloudWatch, EventBridge, EC2) and integrates seamlessly with the current Minecraft Server Dashboard architecture, including the Vue.js frontend, AppSync GraphQL API, Lambda functions, and EC2 instance management.

## Architecture

### High-Level Flow

```
┌─────────────────┐
│  Vue.js UI      │
│ ServerSettings  │
└────────┬────────┘
         │ GraphQL Mutation
         │ (putServerConfig)
         ▼
┌─────────────────┐
│   AppSync API   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  ec2ActionValidator   │
│    Lambda       │
└────────┬────────┘
         │ SQS Message
         ▼
┌─────────────────┐
│ec2ActionValidator     │
│  Processor      │
│    Lambda       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────────┐
│  EC2 Instance   │◄─────│  CloudWatch      │
│  - Tags Updated │      │  Alarm           │
│  - Alarm Config │      │  (UserCount)     │
└────────┬────────┘      └──────────────────┘
         │                        ▲
         │ Cron (every minute)    │
         ▼                        │
┌─────────────────┐              │
│ port_count.sh   │──────────────┘
│  Script         │   Publishes Metric
└─────────────────┘
```

### Component Interaction

1. **Frontend (ServerSettings.vue)**: User configures threshold and evaluation period
2. **AppSync API**: Validates and routes configuration request
3. **ec2ActionValidator Lambda**: Queues configuration update to SQS
4. **ec2ActionWorker Lambda**: Processes configuration, updates EC2 tags, creates/updates CloudWatch alarm
5. **EC2 Instance**: Runs cron job every minute to count connections
6. **port_count.sh Script**: Counts TCP connections on port 25565, publishes to CloudWatch
7. **CloudWatch Alarm**: Monitors UserCount metric, triggers EC2 stop when threshold breached
8. **EC2 Auto-Stop**: AWS automation stops instance when alarm fires

## Components and Interfaces

### Frontend Component: ServerSettings.vue

**Purpose**: Provides UI for configuring user-based auto-shutdown

**Key Elements**:
- Shutdown method selector (CPUUtilization, Connections, Schedule)
- Threshold input field (number of users)
- Evaluation period input field (minutes)
- Validation warnings
- Configuration summary card

**State Management**:
```javascript
const serverConfigInput = reactive({
    id: null,
    alarmThreshold: 0,              // Number of users
    alarmEvaluationPeriod: 0,       // Minutes
    shutdownMethod: 'Connections'   // Selected method
});
```

**Validation Rules**:
- Threshold: Non-negative integers only
- Evaluation Period: Positive integers only
- Warning when period < 5 minutes with threshold > 0

**API Integration**:
```javascript
// Calls serverStore.putServerConfig(configData)
// which triggers GraphQL mutation
```

### Backend Component: ec2ActionWorker Lambda

**Purpose**: Processes configuration updates and manages CloudWatch alarms

**Key Function**: `handle_update_server_config(instance_id, arguments)`

**Logic Flow**:
```python
1. Validate arguments
2. Update EC2 instance tags via ec2_utils.set_instance_attributes_to_tags()
3. Determine shutdown method from response
4. If method == 'Connections':
   a. Remove any schedule events
   b. Create/update CloudWatch alarm with UserCount metric
5. Return success/failure
```

**Error Handling**:
- Missing arguments → return False
- Invalid threshold/period → return False
- CloudWatch API errors → logged and return False

### EC2 Helper: ec2Helper.py

**Purpose**: Abstracts EC2 and CloudWatch operations

**Key Methods**:

#### `update_alarm(instance_id, alarm_metric, alarm_threshold, alarm_evaluation_period)`
```python
# Creates or updates CloudWatch alarm
# For Connections:
#   - Metric: UserCount
#   - Namespace: MinecraftDashboard
#   - Statistic: Maximum
#   - Dimensions: InstanceId
#   - Period: 60 seconds
#   - Comparison: LessThanOrEqualToThreshold
#   - Action: EC2 stop automation
```

#### `remove_alarm(instance_id)`
```python
# Deletes CloudWatch alarm if it exists
# Used when switching from Connections to Schedule method
```

#### `set_instance_attributes_to_tags(input)`
```python
# Stores configuration in EC2 instance tags
# Tags: ShutdownMethod, AlarmThreshold, AlarmEvaluationPeriod
```

### Metric Collection: port_count.sh

**Purpose**: Counts active Minecraft connections and publishes to CloudWatch

**Installation**: Created during EC2 bootstrap via BootstrapSSMDoc

**Script Location**: `/usr/local/port_count.sh`

**Execution**: Cron job runs every minute

**Implementation**:
```bash
#!/bin/bash
INSTANCE_ID="<instance-id>"
REGION="<region>"
PORT_COUNT=$(netstat -an | grep ESTABLISHED | grep ':25565' | wc -l)
aws cloudwatch put-metric-data \
  --metric-name UserCount \
  --dimensions InstanceId=$INSTANCE_ID \
  --namespace 'MinecraftDashboard' \
  --value $PORT_COUNT \
  --region $REGION
```

**Metric Details**:
- **Metric Name**: UserCount
- **Namespace**: MinecraftDashboard
- **Dimension**: InstanceId
- **Unit**: Count
- **Frequency**: Every 60 seconds

### CloudWatch Alarm Configuration

**Alarm Name**: `{instance_id}-minecraft-server`

**Metric Configuration**:
- **Namespace**: MinecraftDashboard
- **Metric Name**: UserCount
- **Statistic**: Maximum (captures peak connections in period)
- **Dimensions**: InstanceId={instance_id}
- **Period**: 60 seconds
- **Evaluation Periods**: User-configured (minutes)
- **Datapoints to Alarm**: Same as evaluation periods
- **Threshold**: User-configured (player count)
- **Comparison Operator**: LessThanOrEqualToThreshold
- **Treat Missing Data**: missing (don't trigger on missing data)

**Alarm Actions**:
- **ALARM State**: `arn:aws:automate:{region}:ec2:stop`

**Example**: 
- Threshold: 0 users
- Evaluation Period: 10 minutes
- Result: Server stops if 0 users for 10 consecutive minutes

## Data Models

### ServerConfig (GraphQL Schema)

```graphql
type ServerConfig {
    id: ID!                          # EC2 Instance ID
    shutdownMethod: String           # "CPUUtilization" | "Connections" | "Schedule"
    alarmThreshold: Float            # Number of users (0-N)
    alarmEvaluationPeriod: Int       # Minutes (1-N)
    runCommand: String               # Minecraft start command
    workDir: String                  # Working directory
    stopScheduleExpression: String   # Cron expression (for Schedule method)
    startScheduleExpression: String  # Cron expression (for Schedule method)
}

input ServerConfigInput {
    id: ID!
    shutdownMethod: String
    alarmThreshold: Float
    alarmEvaluationPeriod: Int
    runCommand: String
    workDir: String
    stopScheduleExpression: String
    startScheduleExpression: String
}
```

### EC2 Instance Tags

Configuration is persisted as EC2 instance tags:

| Tag Key | Tag Value | Type | Example |
|---------|-----------|------|---------|
| ShutdownMethod | CPUUtilization \| Connections \| Schedule | String | "Connections" |
| AlarmThreshold | Numeric value | String | "0" |
| AlarmEvaluationPeriod | Minutes | String | "10" |
| RunCommand | Shell command | String | "java -jar server.jar" |
| WorkDir | Directory path | String | "/home/minecraft" |
| StopScheduleExpression | Cron expression | String | "0 23 * * *" |
| StartScheduleExpression | Cron expression | String | "0 17 * * *" |

**Note**: Tags are stored as strings; type conversion happens in `get_instance_attributes_from_tags()`

### CloudWatch Metric Data Point

```json
{
    "MetricName": "UserCount",
    "Namespace": "MinecraftDashboard",
    "Dimensions": [
        {
            "Name": "InstanceId",
            "Value": "i-1234567890abcdef0"
        }
    ],
    "Value": 3,
    "Timestamp": "2025-11-19T10:30:00Z",
    "Unit": "Count"
}
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Configuration Persistence
*For any* valid configuration with Connections shutdown method, saving the configuration should result in EC2 instance tags containing the exact threshold and evaluation period values.
**Validates: Requirements 1.4**

### Property 2: Metric Collection Accuracy
*For any* point in time when the script executes, the UserCount metric value should equal the number of established TCP connections on port 25565.
**Validates: Requirements 2.1, 2.2**

### Property 3: Alarm Threshold Enforcement
*For any* CloudWatch alarm configured with threshold T and evaluation period E, the alarm should transition to ALARM state if and only if UserCount ≤ T for E consecutive minutes.
**Validates: Requirements 3.2**

### Property 4: Shutdown Method Exclusivity
*For any* instance, when shutdown method is set to Connections, no EventBridge schedule rules should exist for that instance, and a CloudWatch alarm should exist.
**Validates: Requirements 7.1, 7.2**

### Property 5: Zero User Detection
*For any* instance with threshold set to 0, when no TCP connections exist on port 25565, the metric collection script should publish UserCount = 0.
**Validates: Requirements 8.1**

### Property 6: Configuration Validation
*For any* configuration where threshold > 0 and evaluation period < 5, the UI should display a warning message before allowing submission.
**Validates: Requirements 4.1**

### Property 7: Alarm Action Correctness
*For any* CloudWatch alarm in ALARM state for Connections method, the alarm action should be the EC2 stop automation ARN for the correct region.
**Validates: Requirements 3.3**

### Property 8: Metric Dimension Consistency
*For any* published UserCount metric, the InstanceId dimension should match the EC2 instance ID where the script is executing.
**Validates: Requirements 2.3**

## Error Handling

### Frontend Validation Errors

**Invalid Threshold**:
- **Trigger**: Non-numeric or negative value
- **Handling**: Display inline validation error, disable save button
- **Message**: "It must be numbers only."

**Invalid Evaluation Period**:
- **Trigger**: Non-numeric, zero, or negative value
- **Handling**: Display inline validation error, disable save button
- **Message**: "Field is required." or "It must be numbers only."

**Short Evaluation Period Warning**:
- **Trigger**: Threshold > 0 AND period < 5 minutes
- **Handling**: Display warning alert (allows save)
- **Message**: "Short evaluation period may shutdown server when players briefly disconnect."

### Backend Processing Errors

**Missing Configuration Arguments**:
- **Trigger**: `arguments` parameter is None or empty
- **Handling**: Log error, return False, send FAILED status to AppSync
- **Recovery**: User must retry with valid configuration

**CloudWatch API Errors**:
- **Trigger**: `put_metric_alarm()` fails (permissions, throttling, etc.)
- **Handling**: Log error with details, return False
- **Recovery**: Automatic retry via SQS (up to 3 attempts), then DLQ

**Invalid Threshold/Period Values**:
- **Trigger**: Missing or invalid alarm parameters
- **Handling**: Log error, return False
- **Recovery**: User must provide valid values

**Tag Update Failures**:
- **Trigger**: `create_tags()` or `delete_tags()` fails
- **Handling**: Log error, return False
- **Recovery**: Configuration not persisted; user must retry

### Metric Collection Errors

**Network Connectivity Loss**:
- **Trigger**: Cannot reach CloudWatch API
- **Handling**: AWS CLI retries with exponential backoff (built-in)
- **Recovery**: Metric published when connectivity restored

**Missing Instance Metadata**:
- **Trigger**: Cannot retrieve instance ID or region
- **Handling**: Script fails, logged to cron output
- **Recovery**: Manual investigation required (rare scenario)

**CloudWatch Agent Not Running**:
- **Trigger**: Agent stopped or crashed
- **Handling**: Script continues independently (uses AWS CLI)
- **Recovery**: No impact; script doesn't depend on agent

### Alarm Monitoring Errors

**Insufficient Data**:
- **Trigger**: Metric not published for extended period
- **Handling**: Alarm treats as "missing" (doesn't trigger)
- **Recovery**: Alarm evaluates when data resumes

**Alarm Deletion During Active Monitoring**:
- **Trigger**: User switches to Schedule method
- **Handling**: Alarm removed cleanly via `remove_alarm()`
- **Recovery**: N/A (intentional)

## Testing Strategy

### Unit Tests

**Frontend Validation Tests**:
- Test threshold validation with valid/invalid inputs
- Test evaluation period validation
- Test warning display logic for short periods
- Test form submission prevention with invalid data

**Backend Configuration Tests**:
- Test `handle_update_server_config()` with valid Connections config
- Test error handling for missing arguments
- Test alarm creation with various threshold/period combinations
- Test method switching from Schedule to Connections

**EC2 Helper Tests**:
- Test `update_alarm()` creates alarm with correct parameters
- Test `remove_alarm()` handles non-existent alarms gracefully
- Test tag conversion (string to float/int) in `get_instance_attributes_from_tags()`

### Integration Tests

**End-to-End Configuration Flow**:
1. Submit configuration via UI
2. Verify GraphQL mutation succeeds
3. Verify SQS message queued
4. Verify Lambda processes message
5. Verify EC2 tags updated
6. Verify CloudWatch alarm created

**Metric Collection Flow**:
1. Simulate player connections on port 25565
2. Trigger cron job execution
3. Verify metric published to CloudWatch
4. Verify metric has correct dimensions and value

**Alarm Trigger Flow**:
1. Configure alarm with threshold 0, period 5 minutes
2. Ensure no connections for 5 minutes
3. Verify alarm enters ALARM state
4. Verify EC2 stop action triggered

### Property-Based Tests

**Property Test 1: Configuration Round-Trip**:
- Generate random valid threshold (0-100) and period (1-60)
- Save configuration
- Retrieve configuration from tags
- Assert retrieved values match original

**Property Test 2: Metric Value Accuracy**:
- Generate random number of simulated connections (0-20)
- Execute metric collection script
- Assert published metric value equals connection count

**Property Test 3: Alarm State Transitions**:
- Generate random threshold and period
- Simulate metric values above and below threshold
- Assert alarm state matches expected based on evaluation logic

### Edge Case Tests

**Zero Threshold**:
- Configure threshold = 0, period = 10
- Verify alarm triggers when UserCount = 0
- Verify alarm doesn't trigger when UserCount > 0

**Large Evaluation Period**:
- Configure period = 60 minutes
- Verify alarm doesn't trigger prematurely
- Verify alarm triggers after full 60 minutes below threshold

**Rapid Connection Changes**:
- Simulate connections fluctuating around threshold
- Verify alarm only triggers after sustained period below threshold

**Instance Restart**:
- Stop and start instance
- Verify cron job resumes automatically
- Verify metric collection continues

## Implementation Notes

### Existing Implementation Status

The user-based auto-shutdown feature is **fully implemented** in the current codebase:

✅ **Frontend**: ServerSettings.vue supports Connections method with validation
✅ **Backend**: ec2ActionWorker handles configuration updates
✅ **EC2 Helper**: update_alarm() creates CloudWatch alarms for Connections
✅ **Metric Collection**: port_count.sh script installed via bootstrap
✅ **CloudWatch Integration**: Alarms configured with correct parameters

### Potential Enhancements

1. **Enhanced Metric Collection**:
   - Track unique player UUIDs instead of just connection count
   - Distinguish between authenticated and unauthenticated connections
   - Add metric for player join/leave events

2. **Advanced Alarm Configuration**:
   - Support for composite alarms (CPU AND Connections)
   - Configurable alarm actions (SNS notifications before shutdown)
   - Grace period before shutdown (warning to players)

3. **UI Improvements**:
   - Real-time display of current UserCount metric
   - Historical graph of player connections
   - Estimated cost savings calculator

4. **Monitoring & Observability**:
   - Dashboard showing alarm state history
   - Alerts for metric collection failures
   - Audit log of shutdown events with reason

### Dependencies

- **AWS Services**: EC2, CloudWatch, EventBridge, SQS, AppSync
- **Frontend**: Vue 3, Vuetify, AWS Amplify SDK
- **Backend**: Python 3.9+, boto3, requests
- **EC2 Instance**: bash, netstat, aws-cli, cron

### Security Considerations

- **IAM Permissions**: EC2 instance role must have `cloudwatch:PutMetricData`
- **Alarm Actions**: Uses AWS service-linked role for EC2 automation
- **Tag Access**: Lambda requires `ec2:CreateTags`, `ec2:DeleteTags`, `ec2:DescribeTags`
- **Metric Data**: UserCount metric is not sensitive; no PII concerns

### Performance Considerations

- **Metric Frequency**: 1-minute intervals provide good balance of accuracy and cost
- **Alarm Evaluation**: CloudWatch evaluates alarms every minute
- **Script Execution**: `netstat` command is lightweight, minimal CPU impact
- **API Calls**: CloudWatch PutMetricData has generous free tier (1M requests/month)

### Cost Implications

- **CloudWatch Metrics**: $0.30 per custom metric per month
- **CloudWatch Alarms**: $0.10 per alarm per month
- **API Calls**: Included in free tier for typical usage
- **Total Estimated Cost**: ~$0.40/month per instance with Connections monitoring

**Cost Savings**: Automatic shutdown when idle can save $20-50/month in EC2 costs, providing 50-125x ROI.
