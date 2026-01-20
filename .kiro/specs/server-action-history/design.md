# Design Document

## Overview

The Server Action History feature provides users with a comprehensive, chronological view of all operations performed on their Minecraft servers. This feature enhances transparency, enables debugging, and creates an audit trail for server management activities. The design leverages existing infrastructure (DynamoDB, AppSync, GraphQL subscriptions) while introducing a new dedicated table for event storage and new UI components for visualization.

## Architecture

### High-Level Architecture

```
┌─────────────┐
│   Frontend  │
│  (Vue.js)   │
└──────┬──────┘
       │ GraphQL Query/Subscription
       ▼
┌─────────────────────┐
│     AppSync API     │
│  (GraphQL Layer)    │
└──────┬──────────────┘
       │
       ├─────────────────────────┐
       │                         │
       ▼                         ▼
┌──────────────┐         ┌──────────────────┐
│ Lambda       │         │  DynamoDB        │
│ Resolvers    │◄────────┤  ec2ActionValidator    │
└──────────────┘         │  History Table   │
       ▲                 └──────────────────┘
       │
       │ Write Events
       │
┌──────────────────────────────────┐
│  ec2ActionValidator Lambda             │
│  (Creates QUEUED events)         │
└──────────────────────────────────┘
       ▲
       │
┌──────────────────────────────────┐
│  ec2ActionWorker Lambda    │
│  (Updates event status)          │
└──────────────────────────────────┘
```

### Data Flow

1. **Event Creation**: When ec2ActionValidator Lambda queues an action to SQS, it creates a new event record in ec2ActionValidatorHistory table with status "QUEUED"
2. **Event Updates**: ec2ActionWorker Lambda updates the event record as it processes the action (PROCESSING → COMPLETED/FAILED)
3. **Real-time Sync**: Status updates are sent to AppSync via putec2ActionValidatorStatus mutation, triggering subscriptions
4. **Frontend Display**: Vue component queries event history on mount and subscribes to real-time updates
5. **Automatic Cleanup**: DynamoDB TTL automatically deletes events older than 365 days

## Components and Interfaces

### Backend Components

#### 1. DynamoDB Table: ec2ActionValidatorHistory

**Purpose**: Store all server action events with automatic expiration

**Schema**:
```
Primary Key:
  - eventId (String, HASH): Unique identifier for the event (UUID)

Attributes:
  - instanceId (String): EC2 instance ID (GSI partition key)
  - action (String): Action type (start, stop, restart, config, fixRole, addUser)
  - status (String): Current status (QUEUED, PROCESSING, COMPLETED, FAILED)
  - userEmail (String): Email of user who initiated the action
  - queuedAt (Number): Unix timestamp when action was queued
  - processingAt (Number, optional): Unix timestamp when processing started
  - completedAt (Number, optional): Unix timestamp when action completed
  - failedAt (Number, optional): Unix timestamp when action failed
  - errorMessage (String, optional): Error details if action failed
  - parameters (Map, optional): Action parameters (e.g., config changes)
  - intermediateStates (List, optional): Array of EC2 state transitions with timestamps
    - Each item: {state: String, timestamp: Number}
    - Example: [{state: "pending", timestamp: 1234567890}, {state: "running", timestamp: 1234567895}]
  - ttl (Number): Unix timestamp for automatic deletion (queuedAt + 365 days)

Global Secondary Index:
  - instanceId-queuedAt-index
    - Partition Key: instanceId
    - Sort Key: queuedAt (descending)
    - Projection: ALL
```

**Access Patterns**:
- Query all events for a server: Query by instanceId, sort by queuedAt descending
- Get specific event: GetItem by eventId
- Update event status: UpdateItem by eventId

#### 2. Lambda Function: Enhanced ec2ActionValidator

**Purpose**: Create event records when queueing actions

**New Functionality**:
```python
def create_event_record(instance_id, action, user_email, parameters=None):
    """
    Create a new event record in ec2ActionValidatorHistory table
    
    Args:
        instance_id: EC2 instance ID
        action: Action type (start, stop, restart, etc.)
        user_email: Email of user initiating action
        parameters: Optional dict of action parameters
    
    Returns:
        event_id: UUID of created event
    """
    event_id = str(uuid.uuid4())
    queued_at = int(time.time())
    ttl = queued_at + (365* 24 * 60 * 60)  # 365 days
    
    item = {
        'eventId': event_id,
        'instanceId': instance_id,
        'action': action,
        'status': 'QUEUED',
        'userEmail': user_email,
        'queuedAt': queued_at,
        'ttl': ttl
    }
    
    if parameters:
        item['parameters'] = parameters
    
    dynamodb.put_item(TableName='ec2ActionValidatorHistory', Item=item)
    return event_id
```

**Integration Point**: Call `create_event_record()` after successfully queueing message to SQS

#### 3. Lambda Function: Enhanced ec2ActionWorker

**Purpose**: Update event records as actions progress

**New Functionality**:
```python
def update_event_status(event_id, status, error_message=None):
    """
    Update event status in ec2ActionValidatorHistory table
    
    Args:
        event_id: UUID of event to update
        status: New status (PROCESSING, COMPLETED, FAILED)
        error_message: Optional error message for FAILED status
    """
    timestamp = int(time.time())
    
    update_expr = "SET #status = :status"
    expr_attr_names = {'#status': 'status'}
    expr_attr_values = {':status': status}
    
    if status == 'PROCESSING':
        update_expr += ", processingAt = :timestamp"
        expr_attr_values[':timestamp'] = timestamp
    elif status == 'COMPLETED':
        update_expr += ", completedAt = :timestamp"
        expr_attr_values[':timestamp'] = timestamp
    elif status == 'FAILED':
        update_expr += ", failedAt = :timestamp"
        expr_attr_values[':timestamp'] = timestamp
        if error_message:
            update_expr += ", errorMessage = :error"
            expr_attr_values[':error'] = error_message
    
    dynamodb.update_item(
        TableName='ec2ActionValidatorHistory',
        Key={'eventId': event_id},
        UpdateExpression=update_expr,
        ExpressionAttributeNames=expr_attr_names,
        ExpressionAttributeValues=expr_attr_values
    )
```

**Integration Point**: 
- Call with status="PROCESSING" when starting to process message
- Call with intermediate status updates as EC2 state changes (e.g., "pending", "running", "stopping", "stopped")
- Call with status="COMPLETED" when action succeeds and reaches desired state
- Call with status="FAILED" when action fails

**Status Mapping**:
- For start action: QUEUED → PROCESSING → "pending" → "running" → COMPLETED
- For stop action: QUEUED → PROCESSING → "stopping" → "stopped" → COMPLETED
- For restart action: QUEUED → PROCESSING → "stopping" → "stopped" → "pending" → "running" → COMPLETED
- For config action: QUEUED → PROCESSING → COMPLETED (no intermediate states)
- For any failure: → FAILED (with error message)

#### 4. GraphQL Schema Extensions

**New Type**:
```graphql
type ec2ActionValidatorEvent @aws_iam @aws_cognito_user_pools {
    eventId: ID!
    instanceId: String!
    action: String!
    status: String!
    userEmail: AWSEmail!
    queuedAt: AWSTimestamp!
    processingAt: AWSTimestamp
    completedAt: AWSTimestamp
    failedAt: AWSTimestamp
    errorMessage: String
    parameters: AWSJSON
    intermediateStates: AWSJSON  # Array of {state: String, timestamp: Number}
    duration: Int  # Computed field: completedAt - queuedAt (in seconds)
}

# Example intermediateStates for a start action:
# [
#   {"state": "pending", "timestamp": 1700000001},
#   {"state": "running", "timestamp": 1700000045}
# ]

input ec2ActionValidatorEventFilter {
    actionTypes: [String]
    statuses: [String]
    startDate: AWSTimestamp
    endDate: AWSTimestamp
}
```

**New Query**:
```graphql
type Query {
    getec2ActionValidatorHistory(
        instanceId: String!
        filter: ec2ActionValidatorEventFilter
        limit: Int
        nextToken: String
    ): ec2ActionValidatorHistoryConnection @aws_cognito_user_pools
}

type ec2ActionValidatorHistoryConnection {
    items: [ec2ActionValidatorEvent]
    nextToken: String
}
```

**Lambda Resolver**: New Lambda function `getec2ActionValidatorHistory` that:
1. Validates user authorization for the instance
2. Queries ec2ActionValidatorHistory table using instanceId-queuedAt-index
3. Applies optional filters (action types, statuses, date range)
4. Calculates duration for completed events
5. Returns paginated results (default 100, max 500)

### Frontend Components

#### 1. Vue Component: ec2ActionValidatorHistory.vue

**Purpose**: Display event history for a specific server

**Props**:
- `serverId` (String, required): EC2 instance ID
- `maxHeight` (Number, optional): Maximum height for scrollable area

**Data**:
```javascript
{
  events: [],              // Array of event objects
  loading: false,          // Loading state
  filters: {
    actionTypes: [],       // Selected action type filters
    statuses: [],          // Selected status filters
    dateRange: null        // Selected date range
  },
  expandedEvents: new Set(), // Set of expanded event IDs
  subscription: null       // GraphQL subscription reference
}
```

**Methods**:
```javascript
async loadHistory() {
  // Query getec2ActionValidatorHistory with current filters
}

subscribeToUpdates() {
  // Subscribe to both onPutec2ActionValidatorStatus and onChangeState for this server
  // onPutec2ActionValidatorStatus: Updates event status (QUEUED/PROCESSING/COMPLETED/FAILED)
  // onChangeState: Updates event with EC2 state transitions (pending/running/stopping/stopped)
  // Update matching event in events array when any update received
  // Store intermediate states in event.intermediateStates array for timeline visualization
}

formatDuration(queuedAt, completedAt) {
  // Calculate and format duration (e.g., "2m 34s")
}

formatTimestamp(timestamp) {
  // Format Unix timestamp to readable date/time
}

toggleExpand(eventId) {
  // Toggle event expansion to show/hide details
}

applyFilters() {
  // Reload history with new filters
}
```

**Template Structure**:
```vue
<template>
  <v-card>
    <v-card-title>Action History</v-card-title>
    
    <!-- Filter Controls -->
    <v-card-text>
      <v-row>
        <v-col>
          <v-select
            v-model="filters.actionTypes"
            :items="actionTypeOptions"
            label="Action Types"
            multiple
            chips
          />
        </v-col>
        <v-col>
          <v-select
            v-model="filters.statuses"
            :items="statusOptions"
            label="Status"
            multiple
            chips
          />
        </v-col>
      </v-row>
    </v-card-text>
    
    <!-- Event Timeline -->
    <v-card-text>
      <v-timeline side="end" density="compact">
        <v-timeline-item
          v-for="event in events"
          :key="event.eventId"
          :dot-color="getStatusColor(event.status)"
          :icon="getStatusIcon(event.status)"
        >
          <!-- Event Summary -->
          <v-card>
            <v-card-title>
              <v-icon :icon="getActionIcon(event.action)" />
              {{ formatActionName(event.action) }}
            </v-card-title>
            
            <v-card-text>
              <div>{{ formatInitiator(event.userEmail) }}</div>
              <div>{{ formatTimestamp(event.queuedAt) }}</div>
              
              <!-- Show intermediate states as chips -->
              <div v-if="event.intermediateStates && event.intermediateStates.length > 0" class="mt-2">
                <v-chip
                  v-for="(state, idx) in event.intermediateStates"
                  :key="idx"
                  size="x-small"
                  class="mr-1"
                  :color="getStateColor(state.state)"
                >
                  {{ state.state }}
                </v-chip>
              </div>
              
              <div v-if="event.completedAt">
                Duration: {{ formatDuration(event.queuedAt, event.completedAt) }}
              </div>
            </v-card-text>
            
            <!-- Expand Button -->
            <v-card-actions>
              <v-btn
                @click="toggleExpand(event.eventId)"
                text
              >
                {{ expandedEvents.has(event.eventId) ? 'Less' : 'More' }}
              </v-btn>
            </v-card-actions>
            
            <!-- Expanded Details -->
            <v-expand-transition>
              <v-card-text v-if="expandedEvents.has(event.eventId)">
                <div v-if="event.errorMessage">
                  <strong>Error:</strong> {{ event.errorMessage }}
                </div>
                <div v-if="event.parameters">
                  <strong>Parameters:</strong>
                  <pre>{{ JSON.stringify(event.parameters, null, 2) }}</pre>
                </div>
              </v-card-text>
            </v-expand-transition>
          </v-card>
        </v-timeline-item>
      </v-timeline>
    </v-card-text>
  </v-card>
</template>
```

#### 2. Integration with Existing Components

**ServerSettings.vue Enhancement**:
- Add a tab or section for "Action History"
- Include `<ec2ActionValidatorHistory :server-id="serverId" />` component

**ServerStatsDialog.vue Enhancement**:
- Add "History" tab alongside "Stats" and "Charts"
- Display ec2ActionValidatorHistory component in history tab

## Data Models

### ec2ActionValidatorEvent Model

```typescript
interface ec2ActionValidatorEvent {
  eventId: string;           // UUID
  instanceId: string;        // EC2 instance ID
  action: ActionType;        // Enum: start, stop, restart, config, fixRole, addUser
  status: EventStatus;       // Enum: QUEUED, PROCESSING, COMPLETED, FAILED
  userEmail: string;         // User who initiated action
  queuedAt: number;          // Unix timestamp (seconds)
  processingAt?: number;     // Unix timestamp (seconds)
  completedAt?: number;      // Unix timestamp (seconds)
  failedAt?: number;         // Unix timestamp (seconds)
  errorMessage?: string;     // Error details
  parameters?: Record<string, any>;  // Action-specific parameters
  duration?: number;         // Computed: completedAt - queuedAt (seconds)
}

enum ActionType {
  START = 'start',
  STOP = 'stop',
  RESTART = 'restart',
  CONFIG = 'config',
  FIX_ROLE = 'fixRole',
  ADD_USER = 'addUser'
}

enum EventStatus {
  QUEUED = 'QUEUED',
  PROCESSING = 'PROCESSING',
  COMPLETED = 'COMPLETED',
  FAILED = 'FAILED'
}
```

### Filter Model

```typescript
interface ec2ActionValidatorEventFilter {
  actionTypes?: ActionType[];
  statuses?: EventStatus[];
  startDate?: number;  // Unix timestamp
  endDate?: number;    // Unix timestamp
}
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*


### Property 1: Event display completeness
*For any* event, when rendered, the output SHALL contain the action type, user email, queuedAt timestamp, and status
**Validates: Requirements 1.3**

### Property 2: Chronological ordering
*For any* list of events, when displayed, they SHALL be sorted by queuedAt timestamp in descending order (newest first)
**Validates: Requirements 1.2**

### Property 3: Completed event information
*For any* event with status COMPLETED, the rendered output SHALL include completedAt timestamp and calculated duration
**Validates: Requirements 1.4**

### Property 4: Failed event information
*For any* event with status FAILED, the rendered output SHALL include errorMessage and failedAt timestamp
**Validates: Requirements 1.5**

### Property 5: Event record creation
*For any* write operation queued to SQS, a corresponding event record SHALL exist in DynamoDB with status QUEUED, containing instanceId, action, userEmail, queuedAt, and unique eventId
**Validates: Requirements 2.1, 2.5**

### Property 6: Status progression to processing
*For any* event that begins processing, the event record SHALL be updated to status PROCESSING with processingAt timestamp set
**Validates: Requirements 2.2**

### Property 7: Status progression to completed
*For any* successfully completed action, the event record SHALL have status COMPLETED and completedAt timestamp
**Validates: Requirements 2.3**

### Property 8: Status progression to failed
*For any* failed action, the event record SHALL have status FAILED, failedAt timestamp, and errorMessage
**Validates: Requirements 2.4**

### Property 9: Duration calculation accuracy
*For any* completed event, the duration SHALL equal completedAt minus queuedAt
**Validates: Requirements 3.1**

### Property 10: Duration formatting
*For any* duration value, the formatting function SHALL use seconds for durations < 60s, minutes and seconds for durations < 60m, and hours and minutes for durations >= 60m
**Validates: Requirements 3.5**

### Property 11: Action type filtering
*For any* set of events and any action type filter, the filtered results SHALL only contain events whose action matches one of the specified action types
**Validates: Requirements 4.1**

### Property 12: Status filtering
*For any* set of events and any status filter, the filtered results SHALL only contain events whose status matches one of the specified statuses
**Validates: Requirements 4.2**

### Property 13: Date range filtering
*For any* set of events and any date range (startDate, endDate), the filtered results SHALL only contain events where queuedAt is between startDate and endDate inclusive
**Validates: Requirements 4.3**

### Property 14: TTL field presence
*For any* created event record, the TTL field SHALL be present and equal to queuedAt plus 31,536,000 seconds (365 days)
**Validates: Requirements 5.1, 5.2**

### Property 15: TTL format correctness
*For any* TTL value stored, it SHALL be a positive integer representing Unix epoch timestamp
**Validates: Requirements 5.5**

### Property 16: Subscription update matching
*For any* status update received via subscription (including intermediate statuses from EC2 state changes), if an event with matching instanceId and action exists in the displayed list, that event SHALL be updated with the new status information
**Validates: Requirements 6.2**

**Note**: This property ensures that all GraphQL status updates (from both `onPutec2ActionValidatorStatus` and `onChangeState` subscriptions) are reflected in the event history, providing complete visibility into the action lifecycle including EC2 state transitions (pending → running, stopping → stopped, etc.).

### Property 17: New event positioning
*For any* newly created event, it SHALL appear at index 0 in the displayed event list (top position)
**Validates: Requirements 6.3**

### Property 18: Status visual mapping
*For any* event status, the visual indicator (color and icon) SHALL be unique and consistent for that status
**Validates: Requirements 6.4**

### Property 19: Action icon uniqueness
*For any* two different action types, the icon mapping function SHALL return different icons
**Validates: Requirements 7.5**

### Property 20: Query result structure
*For any* valid getec2ActionValidatorHistory query, the result SHALL be a list where each item conforms to the ec2ActionValidatorEvent type structure
**Validates: Requirements 8.2**

### Property 21: Unfiltered query completeness
*For any* getec2ActionValidatorHistory query with no filters, all events for the specified instanceId SHALL be returned, ordered by queuedAt descending
**Validates: Requirements 8.4**

### Property 22: Current user display
*For any* event where userEmail matches the current authenticated user's email, the displayed initiator SHALL be "You"
**Validates: Requirements 9.2**

### Property 23: System initiator display
*For any* event where userEmail is "system" or matches a system identifier pattern, the displayed initiator SHALL be "System"
**Validates: Requirements 9.3**

### Property 24: Email truncation
*For any* email address longer than 30 characters, the displayed version SHALL be truncated with ellipsis
**Validates: Requirements 9.4**

### Property 25: Expand control presence
*For any* rendered event, an expand/collapse control SHALL be present in the UI
**Validates: Requirements 10.1**

### Property 26: Expanded failed event details
*For any* failed event that is expanded, the errorMessage SHALL be visible in the expanded section
**Validates: Requirements 10.2**

### Property 27: Expanded parameter visibility
*For any* event with parameters that is expanded, those parameters SHALL be visible in the expanded section
**Validates: Requirements 10.3**

### Property 28: Collapsed event summary
*For any* collapsed event, only action, userEmail, queuedAt, and status SHALL be visible (errorMessage and parameters SHALL NOT be visible)
**Validates: Requirements 10.5**

### Property 29: Intermediate state recording
*For any* server action that involves EC2 state changes, the event record SHALL contain an intermediateStates array with each state transition and its timestamp
**Validates: Requirements 11.1**

### Property 30: Intermediate state display
*For any* event with intermediateStates, all intermediate states SHALL be displayed as visual indicators in the event summary
**Validates: Requirements 11.2**

## Error Handling

### Backend Error Scenarios

1. **DynamoDB Write Failures**
   - **Scenario**: Event record creation fails due to DynamoDB unavailability
   - **Handling**: Log error, continue with SQS queueing (event history is supplementary, not critical path)
   - **User Impact**: Action proceeds but won't appear in history until retry succeeds

2. **DynamoDB Update Failures**
   - **Scenario**: Event status update fails during processing
   - **Handling**: Log error, retry with exponential backoff (3 attempts), continue with action execution
   - **User Impact**: Event may show stale status temporarily

3. **Invalid Event ID**
   - **Scenario**: Attempt to update event with non-existent eventId
   - **Handling**: Log warning, continue (may occur if event was already TTL-expired)
   - **User Impact**: None (event already expired)

4. **Query Authorization Failure**
   - **Scenario**: User attempts to query events for server they don't own
   - **Handling**: Return 401 Unauthorized error
   - **User Impact**: Error message displayed, no data returned

5. **Malformed Filter Parameters**
   - **Scenario**: Invalid date range or filter values provided
   - **Handling**: Return 400 Bad Request with validation error details
   - **User Impact**: Error message displayed with guidance on correct format

### Frontend Error Scenarios

1. **Query Failure**
   - **Scenario**: getec2ActionValidatorHistory query fails
   - **Handling**: Display error message, provide retry button
   - **User Impact**: "Unable to load event history. Please try again."

2. **Subscription Connection Loss**
   - **Scenario**: WebSocket connection drops
   - **Handling**: Automatically reconnect, reload events on reconnection
   - **User Impact**: Brief delay in real-time updates, automatic recovery

3. **Empty Results**
   - **Scenario**: No events match filters or server has no history
   - **Handling**: Display friendly message: "No events found. Try adjusting your filters."
   - **User Impact**: Clear indication of empty state

4. **Timestamp Formatting Errors**
   - **Scenario**: Invalid timestamp value received
   - **Handling**: Display "Invalid date" placeholder, log error
   - **User Impact**: Single event shows invalid date, rest of history unaffected

## Testing Strategy

### Unit Testing

**Backend Unit Tests**:
1. Test `create_event_record()` function creates correct DynamoDB item structure
2. Test `update_event_status()` function updates correct fields for each status
3. Test TTL calculation produces correct Unix timestamp (queuedAt + 365 days)
4. Test query resolver applies filters correctly (action types, statuses, date ranges)
5. Test authorization logic prevents unauthorized access to event history
6. Test duration calculation handles edge cases (same timestamp, very long durations)

**Frontend Unit Tests**:
1. Test event list sorting maintains descending chronological order
2. Test filter application produces correct subset of events
3. Test duration formatting for various time ranges (seconds, minutes, hours)
4. Test initiator display logic (current user → "You", system → "System")
5. Test email truncation at 30 character threshold
6. Test expand/collapse state management
7. Test status color and icon mapping functions

### Property-Based Testing

We will use **Hypothesis** (Python) for backend property tests and **fast-check** (JavaScript) for frontend property tests. Each property test will run a minimum of 100 iterations.

**Backend Property Tests**:

1. **Property 5: Event record creation** (Requirements 2.1, 2.5)
   - Generate random instanceId, action, userEmail, parameters
   - Call create_event_record()
   - Assert record exists in DynamoDB with all required fields and status QUEUED

2. **Property 9: Duration calculation accuracy** (Requirements 3.1)
   - Generate random queuedAt and completedAt timestamps (completedAt > queuedAt)
   - Calculate duration
   - Assert duration equals completedAt - queuedAt

3. **Property 11: Action type filtering** (Requirements 4.1)
   - Generate random list of events with various action types
   - Generate random action type filter
   - Apply filter
   - Assert all results have action in filter list

4. **Property 12: Status filtering** (Requirements 4.2)
   - Generate random list of events with various statuses
   - Generate random status filter
   - Apply filter
   - Assert all results have status in filter list

5. **Property 13: Date range filtering** (Requirements 4.3)
   - Generate random list of events with various timestamps
   - Generate random date range
   - Apply filter
   - Assert all results have queuedAt within range

6. **Property 14: TTL field presence** (Requirements 5.1, 5.2)
   - Generate random queuedAt timestamp
   - Create event record
   - Assert TTL equals queuedAt + 7,776,000

**Frontend Property Tests**:

1. **Property 2: Chronological ordering** (Requirements 1.2)
   - Generate random list of events with various queuedAt timestamps
   - Sort for display
   - Assert list is in descending order by queuedAt

2. **Property 10: Duration formatting** (Requirements 3.5)
   - Generate random duration values
   - Format duration
   - Assert format uses correct units based on duration magnitude

3. **Property 19: Action icon uniqueness** (Requirements 7.5)
   - For all pairs of different action types
   - Get icons for each
   - Assert icons are different

4. **Property 22: Current user display** (Requirements 9.2)
   - Generate random events with various userEmails
   - Set current user email
   - Format initiator
   - Assert events matching current user show "You"

5. **Property 24: Email truncation** (Requirements 9.4)
   - Generate random email addresses of various lengths
   - Format for display
   - Assert emails > 30 chars are truncated with ellipsis

### Integration Testing

1. **End-to-End Event Flow**:
   - Trigger server action (start/stop/restart)
   - Verify QUEUED event created in DynamoDB
   - Verify event updated to PROCESSING
   - Verify event updated to COMPLETED/FAILED
   - Verify frontend displays event with correct status

2. **Real-time Subscription**:
   - Open event history view
   - Trigger action from different browser tab
   - Verify new event appears in real-time
   - Verify status updates appear in real-time

3. **Filter Combinations**:
   - Create events with various combinations of action types and statuses
   - Apply multiple filters simultaneously
   - Verify only matching events displayed

4. **Pagination**:
   - Create > 100 events for a server
   - Query first page
   - Verify 100 events returned
   - Query next page with token
   - Verify remaining events returned

## Implementation Notes

### Performance Considerations

1. **DynamoDB Query Optimization**:
   - Use GSI (instanceId-queuedAt-index) for efficient queries
   - Limit default page size to 100 events to prevent large payloads
   - Consider caching recent events in frontend for 30 seconds

2. **Subscription Efficiency**:
   - Only subscribe when event history component is mounted
   - Unsubscribe immediately on unmount to prevent memory leaks
   - Batch multiple rapid updates to prevent UI thrashing

3. **TTL Cleanup**:
   - DynamoDB TTL runs in background, may take up to 48 hours to delete expired items
   - Don't rely on TTL for immediate deletion
   - Query filters should exclude expired items if needed

### Security Considerations

1. **Authorization**:
   - Verify user owns or has access to server before returning events
   - Use same authorization logic as existing server queries
   - Don't expose events from other users' servers

2. **Data Sanitization**:
   - Sanitize error messages before storing (remove sensitive data)
   - Limit parameter storage to non-sensitive configuration values
   - Don't store passwords, tokens, or credentials in event parameters

3. **Rate Limiting**:
   - Consider rate limiting event history queries to prevent abuse
   - Use AppSync's built-in throttling (default 1000 req/sec per account)

### Migration Strategy

1. **Backward Compatibility**:
   - New feature doesn't affect existing functionality
   - Existing servers will have empty event history initially
   - Events only created for actions after deployment

2. **Deployment Order**:
   - Deploy DynamoDB table first
   - Deploy Lambda updates (ec2ActionValidator, ec2ActionWorker)
   - Deploy GraphQL schema and resolvers
   - Deploy frontend updates
   - No downtime required

3. **Rollback Plan**:
   - If issues occur, disable event creation in Lambda (feature flag)
   - Frontend gracefully handles empty event history
   - Can delete ec2ActionValidatorHistory table if needed (no dependencies)

## Dependencies

### External Libraries

**Backend**:
- `boto3`: AWS SDK for DynamoDB operations (already in use)
- `uuid`: Generate unique event IDs (Python standard library)

**Frontend**:
- `@aws-amplify/api-graphql`: GraphQL queries and subscriptions (already in use)
- `vuetify`: UI components for timeline, cards, chips (already in use)
- `date-fns`: Date formatting utilities (consider adding for better date handling)

### AWS Services

- **DynamoDB**: Event storage with TTL
- **AppSync**: GraphQL API for queries and subscriptions
- **Lambda**: Event creation and updates
- **IAM**: Permissions for Lambda to access DynamoDB

### Internal Dependencies

- `utilHelper.check_authorization()`: Verify user access to server
- `ec2ActionValidatorStatus` subscription: Reuse existing subscription infrastructure
- Server store (`dashboard/src/stores/server.js`): Add event history methods

## Future Enhancements

1. **Event Aggregation**: Show summary statistics (total actions, success rate, average duration)
2. **Export Functionality**: Allow users to export event history as CSV or JSON
3. **Advanced Filtering**: Add search by user, regex matching on error messages
4. **Event Notifications**: Email or push notifications for failed actions
5. **Retention Configuration**: Allow users to configure TTL period (30/60/365 days)
6. **Event Replay**: Ability to retry failed actions from history
7. **Audit Compliance**: Enhanced logging for compliance requirements (HIPAA, SOC2)
8. **Performance Metrics**: Track and display action performance trends over time
