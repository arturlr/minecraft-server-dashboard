# Implementation Plan

- [ ] 1. Create DynamoDB table and infrastructure
  - Create ServerActionHistory DynamoDB table with eventId as primary key
  - Add Global Secondary Index (instanceId-queuedAt-index) for efficient queries by server
  - Configure TTL on the ttl attribute for automatic 365-day expiration
  - Add IAM permissions for Lambda functions to read/write to the table
  - _Requirements: 2.1, 2.5, 5.1, 5.2_

- [ ] 2. Enhance ServerAction Lambda to create event records
- [ ] 2.1 Add event record creation function
  - Implement `create_event_record()` function that generates UUID, calculates TTL, and writes to DynamoDB
  - Include instanceId, action, userEmail, queuedAt, status (QUEUED), and ttl fields
  - Handle optional parameters field for config updates
  - _Requirements: 2.1, 2.5, 5.1, 5.2_

- [ ]* 2.2 Write property test for event record creation
  - **Property 5: Event record creation**
  - **Validates: Requirements 2.1, 2.5**

- [ ] 2.3 Integrate event creation into action queueing flow
  - Call `create_event_record()` after successfully queueing message to SQS
  - Pass eventId in SQS message body for correlation
  - Handle DynamoDB write failures gracefully (log error, continue with action)
  - _Requirements: 2.1_

- [ ]* 2.4 Write unit tests for ServerAction Lambda integration
  - Test event record created when action queued
  - Test eventId included in SQS message
  - Test graceful handling of DynamoDB failures
  - _Requirements: 2.1_

- [ ] 3. Enhance ServerActionProcessor Lambda to update event status
- [ ] 3.1 Add event status update function
  - Implement `update_event_status()` function that updates status and timestamps
  - Support PROCESSING, COMPLETED, FAILED statuses with appropriate timestamp fields
  - Add error message parameter for FAILED status
  - _Requirements: 2.2, 2.3, 2.4_

- [ ] 3.2 Add intermediate state tracking function
  - Implement `add_intermediate_state()` function that appends EC2 state transitions to intermediateStates array
  - Include state name and timestamp for each transition
  - _Requirements: 11.1_

- [ ]* 3.3 Write property test for duration calculation
  - **Property 9: Duration calculation accuracy**
  - **Validates: Requirements 3.1**

- [ ] 3.4 Integrate status updates into action processing flow
  - Call `update_event_status("PROCESSING")` when starting to process message
  - Call `add_intermediate_state()` for each EC2 state change (pending, running, stopping, stopped)
  - Call `update_event_status("COMPLETED")` when action succeeds
  - Call `update_event_status("FAILED", error_message)` when action fails
  - Extract eventId from SQS message body for correlation
  - _Requirements: 2.2, 2.3, 2.4, 11.1_

- [ ]* 3.5 Write unit tests for ServerActionProcessor integration
  - Test status updated to PROCESSING when processing starts
  - Test intermediate states recorded for EC2 transitions
  - Test status updated to COMPLETED on success
  - Test status updated to FAILED with error message on failure
  - _Requirements: 2.2, 2.3, 2.4, 11.1_

- [ ] 4. Create GraphQL schema extensions
- [ ] 4.1 Add ServerActionEvent type to schema
  - Define ServerActionEvent type with all fields (eventId, instanceId, action, status, timestamps, intermediateStates, etc.)
  - Add ServerActionEventFilter input type for filtering
  - Add ServerActionHistoryConnection type for pagination
  - _Requirements: 8.1_

- [ ] 4.2 Add getServerActionHistory query to schema
  - Define query with instanceId, filter, limit, and nextToken parameters
  - Add @aws_cognito_user_pools authorization directive
  - _Requirements: 8.1_

- [ ] 5. Implement getServerActionHistory Lambda resolver
- [ ] 5.1 Create Lambda function for query resolution
  - Validate user authorization for the instanceId using existing check_authorization
  - Query ServerActionHistory table using instanceId-queuedAt-index
  - Apply optional filters (action types, statuses, date range)
  - Calculate duration field for completed events (completedAt - queuedAt)
  - Return paginated results (default 100, max 500)
  - _Requirements: 8.2, 8.4, 8.5_

- [ ]* 5.2 Write property test for action type filtering
  - **Property 11: Action type filtering**
  - **Validates: Requirements 4.1**

- [ ]* 5.3 Write property test for status filtering
  - **Property 12: Status filtering**
  - **Validates: Requirements 4.2**

- [ ]* 5.4 Write property test for date range filtering
  - **Property 13: Date range filtering**
  - **Validates: Requirements 4.3**

- [ ]* 5.5 Write property test for TTL field presence
  - **Property 14: TTL field presence**
  - **Validates: Requirements 5.1, 5.2**

- [ ]* 5.6 Write unit tests for query resolver
  - Test authorization check prevents unauthorized access
  - Test query returns all events when no filters provided
  - Test pagination with limit and nextToken
  - Test duration calculation for completed events
  - _Requirements: 8.2, 8.4, 8.5_

- [ ] 6. Create frontend GraphQL operations
- [ ] 6.1 Add query and subscription to graphql/queries.js
  - Add getServerActionHistory query with filter parameters
  - Export query for use in components
  - _Requirements: 1.1_

- [ ] 6.2 Update graphql/subscriptions.js if needed
  - Verify onPutServerActionStatus subscription exists
  - Verify onChangeState subscription exists
  - _Requirements: 6.1, 11.2_

- [ ] 7. Create ServerActionHistory Vue component
- [ ] 7.1 Create component structure and props
  - Create ServerActionHistory.vue in components directory
  - Define props: serverId (required), maxHeight (optional)
  - Set up component data: events array, loading state, filters, expandedEvents set
  - _Requirements: 1.1_

- [ ] 7.2 Implement event loading and subscription
  - Implement loadHistory() method to query getServerActionHistory
  - Implement subscribeToUpdates() to subscribe to onPutServerActionStatus and onChangeState
  - Update events array when subscription receives updates
  - Unsubscribe on component unmount
  - _Requirements: 1.1, 6.1, 6.2, 6.3_

- [ ]* 7.3 Write property test for chronological ordering
  - **Property 2: Chronological ordering**
  - **Validates: Requirements 1.2**

- [ ] 7.4 Implement formatting utility methods
  - Implement formatDuration() to convert seconds to human-readable format (e.g., "2m 34s")
  - Implement formatTimestamp() to convert Unix timestamp to readable date/time
  - Implement formatInitiator() to show "You" for current user, "System" for system actions
  - Implement formatActionName() to convert action codes to display names
  - _Requirements: 3.2, 3.3, 9.2, 9.3_

- [ ]* 7.5 Write property test for duration formatting
  - **Property 10: Duration formatting**
  - **Validates: Requirements 3.5**

- [ ]* 7.6 Write property test for current user display
  - **Property 22: Current user display**
  - **Validates: Requirements 9.2**

- [ ]* 7.7 Write property test for email truncation
  - **Property 24: Email truncation**
  - **Validates: Requirements 9.4**

- [ ] 7.8 Implement visual indicator methods
  - Implement getStatusColor() to map status to color (blue/orange/green/red)
  - Implement getStatusIcon() to map status to icon (clock/spinner/checkmark/error)
  - Implement getActionIcon() to map action type to icon (play/stop/refresh/settings)
  - Implement getStateColor() to map EC2 states to colors
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 11.2_

- [ ]* 7.9 Write property test for action icon uniqueness
  - **Property 19: Action icon uniqueness**
  - **Validates: Requirements 7.5**

- [ ] 7.10 Implement filter functionality
  - Implement applyFilters() method to reload history with selected filters
  - Add filter controls for action types, statuses, and date range
  - Update displayed events when filters change
  - _Requirements: 4.1, 4.2, 4.3_

- [ ] 7.11 Implement expand/collapse functionality
  - Implement toggleExpand() method to manage expandedEvents set
  - Show error message and parameters in expanded section
  - Show only summary in collapsed state
  - _Requirements: 10.1, 10.2, 10.3, 10.5_

- [ ] 7.12 Create component template with timeline
  - Use v-timeline component to display events chronologically
  - Add filter controls (v-select for action types and statuses)
  - Display event cards with summary information
  - Show intermediate states as chips
  - Add expand/collapse controls
  - Show expanded details (error messages, parameters)
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 4.1, 4.2, 10.1, 10.2, 10.3, 11.2_

- [ ]* 7.13 Write unit tests for component methods
  - Test loadHistory() fetches and displays events
  - Test subscribeToUpdates() updates events in real-time
  - Test filter application produces correct subset
  - Test expand/collapse state management
  - Test formatting methods produce correct output
  - _Requirements: 1.1, 4.1, 4.2, 6.2, 10.1_

- [ ] 8. Integrate ServerActionHistory into existing components
- [ ] 8.1 Add history tab to ServerStatsDialog
  - Import ServerActionHistory component
  - Add "History" tab alongside existing tabs
  - Pass serverId prop to component
  - _Requirements: 1.1_

- [ ] 8.2 Add history section to ServerSettings
  - Import ServerActionHistory component
  - Add collapsible section or tab for action history
  - Pass serverId prop to component
  - _Requirements: 1.1_

- [ ]* 8.3 Write integration tests for component integration
  - Test history component renders in ServerStatsDialog
  - Test history component renders in ServerSettings
  - Test serverId prop passed correctly
  - _Requirements: 1.1_

- [ ] 9. Add store methods for event history
- [ ] 9.1 Add getServerActionHistory method to server store
  - Implement method in dashboard/src/stores/server.js
  - Call GraphQL query with instanceId and optional filters
  - Handle errors and return results
  - _Requirements: 1.1_

- [ ]* 9.2 Write unit tests for store methods
  - Test getServerActionHistory calls correct GraphQL query
  - Test error handling
  - Test filter parameters passed correctly
  - _Requirements: 1.1_

- [ ] 10. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 11. End-to-end testing and validation
- [ ]* 11.1 Test complete event lifecycle
  - Trigger server start action
  - Verify QUEUED event appears immediately
  - Verify event updates to PROCESSING
  - Verify intermediate states (pending, running) appear
  - Verify event updates to COMPLETED
  - Verify duration calculated correctly
  - _Requirements: 2.1, 2.2, 2.3, 3.1, 11.1, 11.3_

- [ ]* 11.2 Test real-time subscription updates
  - Open event history in one browser tab
  - Trigger action from different tab
  - Verify new event appears in real-time
  - Verify status updates appear in real-time
  - Verify intermediate states appear in real-time
  - _Requirements: 6.2, 6.3, 11.2_

- [ ]* 11.3 Test filter combinations
  - Create events with various action types and statuses
  - Apply action type filter
  - Verify only matching events displayed
  - Apply status filter
  - Verify only matching events displayed
  - Apply date range filter
  - Verify only events in range displayed
  - _Requirements: 4.1, 4.2, 4.3_

- [ ]* 11.4 Test TTL and data retention
  - Create event with TTL in past (for testing)
  - Verify DynamoDB TTL configuration active
  - Verify old events not returned in queries
  - _Requirements: 5.1, 5.2_

- [ ]* 11.5 Test error scenarios
  - Test unauthorized access to event history
  - Test query with invalid filters
  - Test subscription connection loss and recovery
  - Test empty event history display
  - _Requirements: 4.5_
