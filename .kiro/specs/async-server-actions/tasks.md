# Implementation Plan

- [x] 1. Refactor ServerAction Lambda to remove direct EC2 operations
  - Remove IamProfile class and all IAM profile management code
  - Remove direct EC2 client calls (start_instances, stop_instances, reboot_instances)
  - Remove EventBridge rule management code
  - Remove CloudWatch alarm management code
  - Keep authorization, queue sending, and read-only operation handlers
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

- [x] 1.1 Write property test for ServerAction code cleanliness
  - **Property 9: ServerAction code cleanliness**
  - **Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5**

- [x] 2. Update ServerAction Lambda to queue all write operations
  - Ensure send_to_queue is called for all write operations (start, stop, restart, fixServerRole, putServerConfig, updateServerConfig)
  - Update send_to_queue to send initial PROCESSING status to AppSync after queueing
  - Ensure read operations (getServerConfig, getServerUsers) continue to process synchronously
  - Update error handling to return appropriate status codes (400, 401, 500)
  - _Requirements: 1.1, 1.4, 3.3, 3.4, 7.1, 7.2, 7.3, 7.4_

- [x] 2.1 Write property test for write operations always queued
  - **Property 4: Write operations always queued**
  - **Validates: Requirements 1.1**

- [x] 2.2 Write property test for read operations bypass queue
  - **Property 3: Read operations bypass queue**
  - **Validates: Requirements 1.4**

- [ ]* 2.3 Write property test for authorization before queueing
  - **Property 1: Authorization before queueing**
  - **Validates: Requirements 1.1, 3.3, 7.2**

- [ ]* 2.4 Write property test for validation before queueing
  - **Property 7: Validation before queueing**
  - **Validates: Requirements 7.1, 7.2, 7.3**

- [x] 3. Enhance SQS message format and validation
  - Update send_to_queue to include all required fields (action, instanceId, timestamp)
  - Include optional fields (arguments, userEmail) when provided
  - Add message validation before sending to queue
  - _Requirements: 1.2, 7.5_

- [x] 3.1 Write property test for queue message completeness
  - **Property 2: Queue message completeness**
  - **Validates: Requirements 1.2**

- [x] 4. Update ServerActionProcessor to handle all action types
  - Ensure process_server_action correctly parses message body
  - Verify routing logic for start/stop/restart → handle_server_action
  - Verify routing logic for fixServerRole → handle_fix_role
  - Verify routing logic for putServerConfig/updateServerConfig → handle_update_server_config
  - Add comprehensive error handling for each action type
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [x] 4.1 Write property test for action routing correctness
  - **Property 8: Action routing correctness**
  - **Validates: Requirements 4.2, 4.3, 4.4**

- [x] 5. Implement comprehensive status update system
  - Update send_to_queue in ServerAction to send initial PROCESSING status
  - Update process_server_action in ServerActionProcessor to send PROCESSING status when processing starts
  - Update all handler functions to send COMPLETED status on success
  - Update all handler functions to send FAILED status with error details on failure
  - Ensure all status updates include required fields (id, action, status, timestamp, message, userEmail)
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [x] 5.1 Write property test for status update progression
  - **Property 5: Status update progression**
  - **Validates: Requirements 2.1, 2.2, 2.3, 2.4**

- [ ]* 5.2 Write property test for status update completeness
  - **Property 10: Status update completeness**
  - **Validates: Requirements 2.5**

- [x] 6. Update IAM permissions for ServerAction Lambda
  - Remove EC2 start/stop/reboot permissions from ServerAction Lambda in lambdas.yaml
  - Remove IAM PassRole permission from ServerAction Lambda
  - Remove EventBridge rule management permissions from ServerAction Lambda
  - Remove CloudWatch alarm management permissions from ServerAction Lambda
  - Verify SQS SendMessage permission exists for ServerAction Lambda
  - Keep EC2 read-only permissions for authorization checks
  - Keep Cognito permissions for user management
  - _Requirements: 6.1, 6.2, 6.3, 6.4_

- [x] 7. Add enhanced error handling and logging
  - Add detailed logging for authorization checks in ServerAction
  - Add detailed logging for queue operations in ServerAction
  - Add detailed logging for action processing in ServerActionProcessor
  - Add error logging with full exception details
  - Add logging for status update successes and failures
  - _Requirements: 1.5, 4.5_

- [x] 7.1 Write unit tests for error handling scenarios
  - Test missing JWT token handling
  - Test invalid JWT token handling
  - Test missing instance ID handling
  - Test authorization failure handling
  - Test SQS queue unavailable handling
  - Test EC2 operation failure handling
  - Test IAM profile attachment failure handling
  - _Requirements: 1.5, 4.5_

- [ ] 8. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ]* 9. Add integration tests for end-to-end flow
  - Test complete flow: AppSync → ServerAction → SQS → ServerActionProcessor → AppSync
  - Test status update delivery via GraphQL subscriptions
  - Test retry behavior with intentionally failing operations
  - Test concurrent action processing
  - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.2, 2.3, 2.4_

- [ ] 10. Update documentation and deployment notes
  - Document the refactored architecture in code comments
  - Add inline documentation for key functions
  - Update environment variable documentation
  - Document monitoring and troubleshooting procedures
  - _Requirements: All_
