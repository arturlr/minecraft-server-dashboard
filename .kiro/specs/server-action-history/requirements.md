# Requirements Document

## Introduction

This specification defines a server action event history feature that allows users to view a chronological log of all actions performed on their Minecraft servers. Users need visibility into when actions were initiated, who initiated them, and when they completed or failed. This provides transparency, debugging capability, and audit trail functionality.

## Glossary

- **Server Action Event**: A record of a server action including when it was invoked, by whom, the action type, and its completion status
- **Event History**: A chronological list of all server action events for a specific server
- **Action Types**: Operations performed on servers including start, stop, restart, config updates, IAM role fixes, and user management
- **Event Status**: The state of an action event (QUEUED, PROCESSING, COMPLETED, FAILED)
- **Event Timeline**: A visual representation showing the progression of events over time
- **DynamoDB Table**: The ec2ActionValidatorHistory table that stores all action event records
- **TTL (Time To Live)**: Automatic expiration of old event records after a configured retention period

## Requirements

### Requirement 1

**User Story:** As a user, I want to see a history of all actions performed on my server, so that I can understand what operations have been executed and when.

#### Acceptance Criteria

1. WHEN a user views a server's details THEN the system SHALL display an event history section showing all actions for that server
2. WHEN displaying event history THEN the system SHALL show events in reverse chronological order (newest first)
3. WHEN displaying an event THEN the system SHALL show the action type, user who initiated it, timestamp when queued, and current status
4. WHEN an event is completed THEN the system SHALL show the completion timestamp and duration
5. WHEN an event has failed THEN the system SHALL show the error message and failure timestamp

### Requirement 2

**User Story:** As a system, I want to record every server action event to DynamoDB, so that a complete audit trail is maintained for all operations.

#### Acceptance Criteria

1. WHEN a write operation is queued to SQS THEN the ec2ActionValidator Lambda SHALL create an event record in the ec2ActionValidatorHistory table with status "QUEUED"
2. WHEN ec2ActionWorker begins processing an action THEN the system SHALL update the event record status to "PROCESSING" with a processing timestamp
3. WHEN an action completes successfully THEN the system SHALL update the event record status to "COMPLETED" with a completion timestamp
4. WHEN an action fails THEN the system SHALL update the event record status to "FAILED" with a failure timestamp and error message
5. WHEN creating an event record THEN the system SHALL include instanceId, action, userEmail, queuedAt timestamp, and a unique eventId

### Requirement 3

**User Story:** As a user, I want to see the duration of completed actions, so that I can understand how long operations typically take.

#### Acceptance Criteria

1. WHEN an action completes THEN the system SHALL calculate the duration between queuedAt and completedAt timestamps
2. WHEN displaying a completed event THEN the system SHALL show the duration in a human-readable format (e.g., "2m 34s", "45s")
3. WHEN an action is still processing THEN the system SHALL show the elapsed time since it was queued
4. WHEN calculating duration THEN the system SHALL handle timezone conversions correctly
5. WHEN displaying duration THEN the system SHALL use appropriate units (seconds for < 60s, minutes and seconds for < 60m, hours and minutes for >= 60m)

### Requirement 4

**User Story:** As a user, I want to filter and search the event history, so that I can quickly find specific actions or time periods.

#### Acceptance Criteria

1. WHEN viewing event history THEN the system SHALL provide a filter to show only specific action types (start, stop, restart, config, etc.)
2. WHEN viewing event history THEN the system SHALL provide a filter to show only specific statuses (queued, processing, completed, failed)
3. WHEN viewing event history THEN the system SHALL provide a date range filter to show events within a specific time period
4. WHEN applying filters THEN the system SHALL update the displayed events in real-time without page reload
5. WHEN no events match the filters THEN the system SHALL display a message indicating no events were found

### Requirement 5

**User Story:** As a system administrator, I want old event records to be automatically deleted, so that storage costs are controlled and the database doesn't grow indefinitely.

#### Acceptance Criteria

1. WHEN creating an event record THEN the system SHALL set a TTL (Time To Live) attribute for automatic expiration
2. WHEN the TTL is configured THEN the system SHALL retain event records for 90 days by default
3. WHEN a record's TTL expires THEN DynamoDB SHALL automatically delete the record without manual intervention
4. WHEN calculating TTL THEN the system SHALL use the queuedAt timestamp plus the retention period
5. WHEN storing TTL THEN the system SHALL use Unix epoch timestamp format as required by DynamoDB

### Requirement 6

**User Story:** As a user, I want to see real-time updates to the event history, so that I can watch actions progress without refreshing the page.

#### Acceptance Criteria

1. WHEN viewing event history THEN the system SHALL subscribe to the onPutec2ActionValidatorStatus GraphQL subscription
2. WHEN a status update is received via subscription THEN the system SHALL update the corresponding event in the displayed history
3. WHEN a new action is initiated THEN the system SHALL add the new event to the top of the history list
4. WHEN an event status changes THEN the system SHALL update the event's visual appearance (color, icon, status text)
5. WHEN the user navigates away from the server details THEN the system SHALL unsubscribe from the subscription to prevent memory leaks

### Requirement 7

**User Story:** As a user, I want to see visual indicators for different event statuses, so that I can quickly identify the state of actions at a glance.

#### Acceptance Criteria

1. WHEN an event is in "QUEUED" status THEN the system SHALL display it with a blue color and a clock icon
2. WHEN an event is in "PROCESSING" status THEN the system SHALL display it with an orange color and a spinner icon
3. WHEN an event is in "COMPLETED" status THEN the system SHALL display it with a green color and a checkmark icon
4. WHEN an event is in "FAILED" status THEN the system SHALL display it with a red color and an error icon
5. WHEN displaying action types THEN the system SHALL use distinct icons for each action (play for start, stop for stop, refresh for restart, settings for config)

### Requirement 8

**User Story:** As a developer, I want a GraphQL query to retrieve event history, so that the frontend can fetch and display historical events.

#### Acceptance Criteria

1. WHEN the GraphQL schema is defined THEN the system SHALL include a getec2ActionValidatorHistory query that accepts instanceId and optional filters
2. WHEN getec2ActionValidatorHistory is called THEN the system SHALL return a list of ec2ActionValidatorEvent objects for the specified instance
3. WHEN optional filters are provided THEN the system SHALL filter results by action type, status, and date range
4. WHEN no filters are provided THEN the system SHALL return all events for the instance ordered by queuedAt descending
5. WHEN the query is executed THEN the system SHALL limit results to 100 events by default with pagination support

### Requirement 9

**User Story:** As a user, I want to see who initiated each action, so that I can track accountability for server operations.

#### Acceptance Criteria

1. WHEN displaying an event THEN the system SHALL show the email address of the user who initiated the action
2. WHEN the current user initiated the action THEN the system SHALL display "You" instead of the email address
3. WHEN an action was initiated by the system (auto-shutdown) THEN the system SHALL display "System" as the initiator
4. WHEN displaying the initiator THEN the system SHALL truncate long email addresses with ellipsis for better layout
5. WHEN hovering over a truncated email THEN the system SHALL show the full email address in a tooltip

### Requirement 10

**User Story:** As a user, I want to expand event details to see additional information, so that I can investigate issues or understand what parameters were used.

#### Acceptance Criteria

1. WHEN viewing an event THEN the system SHALL provide an expand/collapse control to show additional details
2. WHEN an event is expanded THEN the system SHALL show the full error message for failed events
3. WHEN an event is expanded THEN the system SHALL show any parameters or arguments passed to the action
4. WHEN an event is expanded for a config update THEN the system SHALL show which configuration fields were changed
5. WHEN an event is collapsed THEN the system SHALL show only the summary information (action, user, time, status)

### Requirement 11

**User Story:** As a user, I want to see all intermediate EC2 state transitions for server actions, so that I can understand the complete lifecycle of start/stop/restart operations.

#### Acceptance Criteria

1. WHEN a server action involves EC2 state changes THEN the system SHALL record each intermediate state transition with its timestamp
2. WHEN displaying a server action event THEN the system SHALL show all intermediate states (pending, running, stopping, stopped) as visual indicators
3. WHEN a start action is executed THEN the system SHALL show the progression: QUEUED → PROCESSING → pending → running → COMPLETED
4. WHEN a stop action is executed THEN the system SHALL show the progression: QUEUED → PROCESSING → stopping → stopped → COMPLETED
5. WHEN a restart action is executed THEN the system SHALL show the progression: QUEUED → PROCESSING → stopping → stopped → pending → running → COMPLETED
