# Requirements Document

## Introduction

This specification defines the refactoring of the server action processing system to fully utilize asynchronous queue-based processing. Currently, the `ec2ActionValidator` Lambda function handles some operations synchronously (directly calling EC2 APIs) while having partial support for queueing actions to SQS. This creates inconsistent behavior, timeout risks, and makes it difficult to provide real-time status updates to users.

The goal is to ensure ALL write operations (start, stop, restart, iamProfileManager, config updates) are queued to the `ec2ActionValidatorQueue` and processed asynchronously by the `ec2ActionWorker` Lambda, while read-only operations (getServerConfig, getServerUsers) continue to be processed synchronously for immediate response.

## Glossary

- **ec2ActionValidator Lambda**: The Lambda function that receives GraphQL mutation requests from AppSync and validates authorization
- **ec2ActionWorker Lambda**: The Lambda function that processes server actions from the SQS queue and performs actual EC2/AWS operations
- **ec2ActionValidatorQueue**: The SQS queue that buffers server action requests for asynchronous processing
- **Write Operation**: Any action that modifies server state (start, stop, restart, iamProfileManager, config updates)
- **Read Operation**: Any action that only retrieves information without modifying state (getServerConfig, getServerUsers)
- **AppSync**: The GraphQL API that receives client requests and invokes Lambda functions
- **Real-time Status Update**: Status information sent to AppSync via the putec2ActionValidatorStatus mutation for subscription delivery to clients

## Requirements

### Requirement 1

**User Story:** As a system architect, I want all write operations to be processed asynchronously through SQS, so that the system is reliable, scalable, and can handle long-running operations without timeouts.

#### Acceptance Criteria

1. WHEN a user initiates a write operation (start, stop, restart, iamProfileManager, putServerConfig, updateServerConfig) THEN the ec2ActionValidator Lambda SHALL queue the request to ec2ActionValidatorQueue and return immediately with a 202 status
2. WHEN a message is queued to ec2ActionValidatorQueue THEN the message SHALL contain all necessary information including action type, instanceId, arguments, userEmail, and timestamp
3. WHEN ec2ActionWorker receives a message from the queue THEN the system SHALL process the action and perform the actual EC2/AWS operations
4. WHEN a read operation is requested (getServerConfig, getServerUsers) THEN the ec2ActionValidator Lambda SHALL process it synchronously and return results immediately
5. WHEN the ec2ActionValidatorQueue is unavailable THEN the system SHALL log an error and return a 500 status to the client

### Requirement 2

**User Story:** As a user, I want to receive real-time updates on the status of my server actions, so that I know when operations are processing, completed, or failed.

#### Acceptance Criteria

1. WHEN an action is queued THEN the ec2ActionValidator Lambda SHALL send a "PROCESSING" status update to AppSync
2. WHEN ec2ActionWorker begins processing an action THEN the system SHALL send a "PROCESSING" status update to AppSync with the action details
3. WHEN an action completes successfully THEN the ec2ActionWorker SHALL send a "COMPLETED" status update to AppSync
4. WHEN an action fails THEN the ec2ActionWorker SHALL send a "FAILED" status update to AppSync with error details
5. WHEN a status update is sent to AppSync THEN the system SHALL include instanceId, action, status, timestamp, message, and userEmail

### Requirement 3

**User Story:** As a developer, I want the ec2ActionValidator Lambda to only handle authorization and queueing, so that the code is simple, maintainable, and follows single responsibility principle.

#### Acceptance Criteria

1. WHEN ec2ActionValidator Lambda receives a request THEN the system SHALL validate the JWT token and extract user attributes
2. WHEN user attributes are extracted THEN the system SHALL check authorization using the existing check_authorization function
3. WHEN authorization succeeds for a write operation THEN the system SHALL call send_to_queue with the action details
4. WHEN authorization succeeds for a read operation THEN the system SHALL call the appropriate handler function synchronously
5. WHEN authorization fails THEN the system SHALL return a 401 status with an error message

### Requirement 4

**User Story:** As a developer, I want the ec2ActionWorker to handle all write operations, so that all business logic for server actions is centralized in one place.

#### Acceptance Criteria

1. WHEN ec2ActionWorker receives a message THEN the system SHALL parse the message body to extract action, instanceId, arguments, and userEmail
2. WHEN the action is "start", "stop", or "restart" THEN the system SHALL call handle_server_action with the appropriate parameters
3. WHEN the action is "iamProfileManager" THEN the system SHALL call handle_fix_role with the instanceId
4. WHEN the action is "putServerConfig" or "updateServerConfig" THEN the system SHALL call handle_update_server_config with instanceId and arguments
5. WHEN any action processing fails THEN the system SHALL log the error and send a FAILED status update to AppSync

### Requirement 5

**User Story:** As a system administrator, I want failed actions to be retried automatically and eventually moved to a dead letter queue, so that transient failures are handled gracefully and persistent failures can be investigated.

#### Acceptance Criteria

1. WHEN an action fails in ec2ActionWorker THEN the SQS queue SHALL automatically retry the message based on the configured retry policy
2. WHEN a message fails after the maximum number of retries (3) THEN the system SHALL move the message to the ec2ActionValidatorDLQ
3. WHEN a message is in the dead letter queue THEN the system SHALL retain it for 14 days for investigation
4. WHEN processing a message THEN the ec2ActionWorker SHALL have a visibility timeout of 300 seconds to complete the operation
5. WHEN a message is successfully processed THEN the system SHALL delete it from the queue automatically

### Requirement 6

**User Story:** As a developer, I want to remove all direct EC2 operation code from ec2ActionValidator Lambda, so that there is a clear separation between request handling and action execution.

#### Acceptance Criteria

1. WHEN reviewing ec2ActionValidator Lambda code THEN the code SHALL NOT contain any calls to ec2_client.start_instances, ec2_client.stop_instances, or ec2_client.reboot_instances
2. WHEN reviewing ec2ActionValidator Lambda code THEN the code SHALL NOT contain any IAM profile management logic (IamProfile class usage)
3. WHEN reviewing ec2ActionValidator Lambda code THEN the code SHALL NOT contain any EventBridge rule management logic
4. WHEN reviewing ec2ActionValidator Lambda code THEN the code SHALL NOT contain any CloudWatch alarm management logic
5. WHEN reviewing ec2ActionValidator Lambda code THEN the code SHALL only contain authorization logic, queue sending logic, and read-only operation handlers

### Requirement 7

**User Story:** As a user, I want the system to validate my requests before queueing them, so that I receive immediate feedback on invalid requests without waiting for async processing.

#### Acceptance Criteria

1. WHEN a request is missing required fields (instanceId) THEN the ec2ActionValidator Lambda SHALL return a 400 status with an error message immediately
2. WHEN a user is not authorized for an action THEN the ec2ActionValidator Lambda SHALL return a 401 status immediately without queueing
3. WHEN a request contains an invalid JWT token THEN the ec2ActionValidator Lambda SHALL return a 401 status immediately
4. WHEN a request is valid and authorized THEN the ec2ActionValidator Lambda SHALL queue it and return a 202 status
5. WHEN validation passes THEN the system SHALL include all validated data in the queued message
