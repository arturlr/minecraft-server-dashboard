# Design Document

## Overview

This design document describes the refactoring of the server action processing system to fully embrace asynchronous, queue-based processing. The refactoring separates concerns between request validation/authorization (ServerAction Lambda) and action execution (ServerActionProcessor Lambda), improving reliability, scalability, and user experience through real-time status updates.

The architecture follows a producer-consumer pattern where ServerAction acts as the producer (validating and queueing requests) and ServerActionProcessor acts as the consumer (executing the actual operations).

## Architecture

### Current Architecture Issues

The current implementation has mixed responsibilities:
- ServerAction Lambda contains both synchronous EC2 operations AND queue-sending logic
- Some operations bypass the queue entirely, leading to timeout risks
- Inconsistent status update patterns
- Duplicate code between ServerAction and ServerActionProcessor

### Target Architecture

```
┌─────────────┐
│   AppSync   │
│  (GraphQL)  │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────┐
│      ServerAction Lambda                │
│  ┌───────────────────────────────────┐  │
│  │ 1. Validate JWT Token             │  │
│  │ 2. Check Authorization            │  │
│  │ 3. Validate Request               │  │
│  │ 4. Route:                         │  │
│  │    - Read ops → Process sync      │  │
│  │    - Write ops → Queue to SQS     │  │
│  │ 5. Send PROCESSING status         │  │
│  └───────────────────────────────────┘  │
└──────┬──────────────────────────────────┘
       │
       ▼
┌─────────────────────┐
│ ServerActionQueue   │
│      (SQS)          │
│  - Visibility: 300s │
│  - Retry: 3 times   │
│  - DLQ enabled      │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│   ServerActionProcessor Lambda          │
│  ┌───────────────────────────────────┐  │
│  │ 1. Parse SQS Message              │  │
│  │ 2. Route to Handler:              │  │
│  │    - start/stop/restart           │  │
│  │    - fixServerRole                │  │
│  │    - putServerConfig              │  │
│  │    - updateServerConfig           │  │
│  │ 3. Execute AWS Operations         │  │
│  │ 4. Send Status Updates            │  │
│  └───────────────────────────────────┘  │
└──────┬──────────────────────────────────┘
       │
       ▼
┌─────────────────────┐
│   AppSync           │
│ putServerAction     │
│    Status           │
│ (Real-time updates) │
└─────────────────────┘
```

## Components and Interfaces

### ServerAction Lambda

**Responsibilities:**
- JWT token validation
- User authorization checking
- Request validation
- Queueing write operations to SQS
- Synchronous processing of read operations
- Initial status update (PROCESSING) for queued operations

**Key Functions:**

```python
def handler(event, context) -> dict:
    """
    Main entry point for AppSync GraphQL requests
    Returns: Response dict with status code and body
    """

def check_authorization(event, instance_id, user_attributes) -> bool:
    """
    Verify user has permission to perform action on instance
    Returns: True if authorized, False otherwise
    """

def send_to_queue(action, instance_id, arguments=None, user_email=None) -> dict:
    """
    Queue action to SQS for async processing
    Returns: 202 response with queued message
    """

def action_process_sync(action, instance_id, arguments=None) -> dict:
    """
    Process read-only operations synchronously
    Returns: Operation result
    """

def handle_get_server_config(instance_id) -> dict:
    """
    Retrieve server configuration from EC2 tags
    Returns: Configuration dict
    """

def handle_get_server_users(instance_id) -> list:
    """
    Retrieve list of users with access to server
    Returns: List of user dicts
    """
```

**Removed Functions:**
- All EC2 operation functions (start/stop/restart)
- IamProfile class and related functions
- EventBridge rule management
- CloudWatch alarm management
- Config update handling

### ServerActionProcessor Lambda

**Responsibilities:**
- Processing messages from ServerActionQueue
- Executing EC2 operations (start/stop/restart)
- Managing IAM profiles
- Managing EventBridge schedules
- Managing CloudWatch alarms
- Updating server configuration tags
- Sending status updates to AppSync

**Key Functions:**

```python
def handler(event, context) -> None:
    """
    SQS event handler - processes batches of messages
    """

def process_server_action(message_body) -> bool:
    """
    Parse and route action to appropriate handler
    Returns: True if successful, False otherwise
    """

def handle_server_action(action, instance_id) -> bool:
    """
    Handle start/stop/restart operations
    Returns: True if successful, False otherwise
    """

def handle_fix_role(instance_id) -> bool:
    """
    Attach/fix IAM instance profile
    Returns: True if successful, False otherwise
    """

def handle_update_server_config(instance_id, arguments) -> bool:
    """
    Update server configuration tags and related resources
    Returns: True if successful, False otherwise
    """

def send_to_appsync(action, instance_id, status, message=None, user_email=None) -> bool:
    """
    Send action status update to AppSync for real-time subscriptions
    Returns: True if successful, False otherwise
    """
```

### SQS Message Format

```json
{
  "action": "start|stop|restart|fixServerRole|putServerConfig|updateServerConfig",
  "instanceId": "i-1234567890abcdef0",
  "arguments": {
    "shutdownMethod": "cpu|connections|schedule",
    "stopScheduleExpression": "cron(0 2 * * ? *)",
    "startScheduleExpression": "cron(0 14 * * ? *)",
    "alarmType": "cpu|connections",
    "alarmThreshold": 5.0,
    "alarmEvaluationPeriod": 30,
    "runCommand": "/opt/minecraft/start.sh",
    "workDir": "/opt/minecraft"
  },
  "userEmail": "user@example.com",
  "timestamp": 1700000000
}
```

### AppSync Status Update Format

```json
{
  "id": "i-1234567890abcdef0",
  "action": "start",
  "status": "PROCESSING|COMPLETED|FAILED",
  "timestamp": 1700000000,
  "message": "Server starting...",
  "userEmail": "user@example.com"
}
```

## Data Models

### ServerActionStatus (GraphQL Type)

```graphql
type ServerActionStatus {
  id: String!              # EC2 instance ID
  action: String!          # Action being performed
  status: String!          # PROCESSING, COMPLETED, FAILED
  timestamp: AWSTimestamp! # When status was updated
  message: String          # Optional status message
  userEmail: AWSEmail      # User who initiated action
}
```

### SQS Queue Configuration

- **Queue Name**: `{ProjectName}-{EnvironmentName}-server-actions`
- **Visibility Timeout**: 300 seconds (5 minutes)
- **Message Retention**: 14 days
- **Max Receive Count**: 3 (before moving to DLQ)
- **Dead Letter Queue**: `{ProjectName}-{EnvironmentName}-server-actions-dlq`

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Authorization before queueing

*For any* write operation request, the ServerAction Lambda should verify user authorization before queueing the message to SQS, ensuring unauthorized requests never enter the processing pipeline.

**Validates: Requirements 1.1, 3.3, 7.2**

### Property 2: Queue message completeness

*For any* queued action message, the message should contain all required fields (action, instanceId, timestamp) and any provided optional fields (arguments, userEmail), ensuring ServerActionProcessor has all necessary information.

**Validates: Requirements 1.2**

### Property 3: Read operations bypass queue

*For any* read operation (getServerConfig, getServerUsers), the ServerAction Lambda should process it synchronously and return results immediately without queueing to SQS.

**Validates: Requirements 1.4**

### Property 4: Write operations always queued

*For any* write operation (start, stop, restart, fixServerRole, putServerConfig, updateServerConfig), when authorization succeeds, the ServerAction Lambda should queue the request to SQS and return a 202 status.

**Validates: Requirements 1.1, 6.1**

### Property 5: Status update progression

*For any* queued action, the system should send status updates in the correct sequence: PROCESSING (when queued) → PROCESSING (when processing starts) → COMPLETED or FAILED (when done).

**Validates: Requirements 2.1, 2.2, 2.3, 2.4**

### Property 6: Failed message retry

*For any* action that fails in ServerActionProcessor, the SQS queue should automatically retry the message up to the configured maximum (3 times) before moving it to the dead letter queue.

**Validates: Requirements 5.1, 5.2**

### Property 7: Validation before queueing

*For any* request with missing required fields or invalid authorization, the ServerAction Lambda should return an error response immediately (400 or 401) without queueing the message.

**Validates: Requirements 7.1, 7.2, 7.3**

### Property 8: Action routing correctness

*For any* message received by ServerActionProcessor, the system should route it to the correct handler function based on the action type (start/stop/restart → handle_server_action, fixServerRole → handle_fix_role, config updates → handle_update_server_config).

**Validates: Requirements 4.2, 4.3, 4.4**

### Property 9: ServerAction code cleanliness

*For any* code review of ServerAction Lambda, the code should not contain direct EC2 client calls (start_instances, stop_instances, reboot_instances), IAM profile management, EventBridge rule management, or CloudWatch alarm management.

**Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5**

### Property 10: Status update completeness

*For any* status update sent to AppSync, the update should include all required fields (id, action, status, timestamp) and preserve any provided optional fields (message, userEmail).

**Validates: Requirements 2.5**

## Error Handling

### ServerAction Lambda Error Scenarios

1. **Missing JWT Token**
   - Return: 401 Unauthorized
   - Message: "No Authorization header found"
   - Action: Do not queue

2. **Invalid JWT Token**
   - Return: 401 Unauthorized
   - Message: "Invalid Token"
   - Action: Do not queue

3. **Missing Instance ID**
   - Return: 400 Bad Request
   - Message: "Instance id is not present in the event"
   - Action: Do not queue

4. **Authorization Failure**
   - Return: 401 Unauthorized
   - Message: "User not authorized"
   - Action: Do not queue, log user email and instance ID

5. **SQS Queue Unavailable**
   - Return: 500 Internal Server Error
   - Message: "Failed to queue action"
   - Action: Log error with full exception details

### ServerActionProcessor Lambda Error Scenarios

1. **Invalid Message Format**
   - Action: Log error, send FAILED status to AppSync
   - Message will be retried or moved to DLQ

2. **EC2 Operation Failure**
   - Action: Log error, send FAILED status with error details
   - Message will be retried (may succeed on retry)

3. **IAM Profile Attachment Failure**
   - Action: Log error, send FAILED status
   - Special handling for UnauthorizedOperation errors

4. **EventBridge Rule Creation Failure**
   - Action: Log error, send FAILED status
   - Validate cron expressions before attempting creation

5. **CloudWatch Alarm Creation Failure**
   - Action: Log error, send FAILED status
   - Validate alarm parameters before attempting creation

6. **AppSync Status Update Failure**
   - Action: Log warning, continue processing
   - Do not fail the entire operation if status update fails

### Retry Strategy

- **Automatic Retries**: SQS automatically retries failed messages up to 3 times
- **Visibility Timeout**: 300 seconds allows sufficient time for long-running operations
- **Dead Letter Queue**: Messages that fail after 3 retries are moved to DLQ for investigation
- **Idempotency**: Operations should be designed to be safely retried (e.g., starting an already-running instance should not fail)

## Testing Strategy

### Unit Testing

**ServerAction Lambda Tests:**
- Test JWT token validation with valid and invalid tokens
- Test authorization checking for admin users, group members, and unauthorized users
- Test request validation with missing/invalid fields
- Test queue message formatting
- Test read operation synchronous processing
- Test error response formatting

**ServerActionProcessor Lambda Tests:**
- Test message parsing with valid and malformed messages
- Test action routing to correct handlers
- Test EC2 operation execution (mocked)
- Test IAM profile management (mocked)
- Test EventBridge rule management (mocked)
- Test CloudWatch alarm management (mocked)
- Test AppSync status update sending (mocked)
- Test error handling for each operation type

### Property-Based Testing

We will use the Hypothesis library for Python to implement property-based tests. Each test should run a minimum of 100 iterations.

**Property Tests to Implement:**

1. **Authorization Before Queueing** (Property 1)
   - Generate random user credentials and instance IDs
   - Verify unauthorized requests never reach the queue

2. **Queue Message Completeness** (Property 2)
   - Generate random action requests with various field combinations
   - Verify all required fields are present in queued messages

3. **Read Operations Bypass Queue** (Property 3)
   - Generate random read operation requests
   - Verify they are processed synchronously without queueing

4. **Write Operations Always Queued** (Property 4)
   - Generate random write operation requests
   - Verify they are queued and return 202 status

5. **Status Update Progression** (Property 5)
   - Generate random actions and track status updates
   - Verify status transitions follow correct sequence

6. **Validation Before Queueing** (Property 7)
   - Generate random invalid requests (missing fields, bad auth)
   - Verify they return errors without queueing

7. **Action Routing Correctness** (Property 8)
   - Generate random action types
   - Verify each routes to the correct handler

8. **Status Update Completeness** (Property 10)
   - Generate random status updates with various field combinations
   - Verify all required fields are included

### Integration Testing

- Test end-to-end flow: AppSync → ServerAction → SQS → ServerActionProcessor → AppSync
- Test real-time subscription delivery of status updates
- Test retry behavior with intentionally failing operations
- Test DLQ message handling
- Test concurrent action processing

### Manual Testing Scenarios

- Start a stopped server and verify status updates
- Stop a running server and verify status updates
- Restart a running server and verify status updates
- Fix IAM role on a server without proper profile
- Update server configuration with various settings
- Attempt unauthorized actions and verify rejection
- Test with network failures to verify retry behavior

## Implementation Notes

### Code Removal from ServerAction

The following code sections should be removed from `lambdas/serverAction/index.py`:

1. **IamProfile class** (lines 52-147) - Move entirely to ServerActionProcessor
2. **handle_server_action function** - Already exists in ServerActionProcessor
3. **handle_fix_role function** - Already exists in ServerActionProcessor
4. **handle_update_server_config function** - Already exists in ServerActionProcessor
5. **All direct ec2_client calls** - Should only exist in ServerActionProcessor

### Code to Keep in ServerAction

1. **handler function** - Main entry point
2. **check_authorization function** - Authorization logic
3. **send_to_queue function** - Queue message sending
4. **action_process_sync function** - Read operation routing
5. **handle_get_server_config function** - Synchronous config retrieval
6. **handle_get_server_users function** - Synchronous user list retrieval
7. **check_and_create_group function** - Cognito group management (used by addUserToServer)

### Environment Variables

**ServerAction Lambda:**
- `SERVER_ACTION_QUEUE_URL` - SQS queue URL for queueing actions
- `COGNITO_USER_POOL_ID` - For user authentication
- `TAG_APP_VALUE` - For EC2 instance filtering
- `EC2_INSTANCE_PROFILE_NAME` - For validation only
- `EC2_INSTANCE_PROFILE_ARN` - For validation only

**ServerActionProcessor Lambda:**
- `APPSYNC_URL` - For sending status updates
- `EC2_INSTANCE_PROFILE_NAME` - For IAM profile operations
- `EC2_INSTANCE_PROFILE_ARN` - For IAM profile operations
- `TAG_APP_VALUE` - For EC2 instance filtering
- `AWS_REGION_NAME` - For AWS service clients

### IAM Permissions

**ServerAction Lambda:**
- Remove: EC2 start/stop/reboot permissions
- Remove: IAM PassRole permission
- Remove: EventBridge rule management permissions
- Remove: CloudWatch alarm management permissions
- Keep: SQS SendMessage permission
- Keep: EC2 read-only permissions (for authorization checks)
- Keep: Cognito permissions (for user management)

**ServerActionProcessor Lambda:**
- Keep: All existing permissions (EC2, IAM, EventBridge, CloudWatch, AppSync)

## Deployment Considerations

### Rollout Strategy

1. **Phase 1**: Deploy updated ServerActionProcessor with enhanced logging
2. **Phase 2**: Deploy updated ServerAction that queues all write operations
3. **Phase 3**: Monitor SQS queue metrics and CloudWatch logs
4. **Phase 4**: Remove unused IAM permissions from ServerAction

### Monitoring

- **SQS Metrics**: Monitor queue depth, message age, and DLQ messages
- **Lambda Metrics**: Monitor invocation count, duration, errors, and throttles
- **AppSync Metrics**: Monitor subscription delivery success rate
- **Custom Metrics**: Track action success/failure rates by action type

### Rollback Plan

If issues arise:
1. Revert ServerAction Lambda to previous version
2. SQS queue will continue to buffer messages
3. ServerActionProcessor will continue processing queued messages
4. No data loss due to SQS message retention

## Performance Considerations

- **Latency**: Users receive immediate 202 response, actual operation happens asynchronously
- **Throughput**: SQS can handle high message volumes, Lambda scales automatically
- **Concurrency**: Multiple ServerActionProcessor instances can process messages in parallel
- **Cost**: Minimal additional cost from SQS usage (~$0.40 per million requests)

## Security Considerations

- Authorization checks happen before queueing (defense in depth)
- SQS messages are encrypted at rest and in transit
- IAM roles enforce least privilege access
- AppSync subscriptions are authenticated via Cognito
- Sensitive data (user emails) included in messages for audit trail
