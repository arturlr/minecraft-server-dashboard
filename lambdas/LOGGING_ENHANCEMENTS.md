# Enhanced Error Handling and Logging

## Overview

This document describes the enhanced error handling and logging implemented in both the `serverAction` and `serverActionProcessor` Lambda functions as part of the async server actions refactoring.

## Implementation Date

November 20, 2025

## Objectives

The enhanced logging provides:
1. Detailed logging for authorization checks
2. Detailed logging for queue operations
3. Detailed logging for action processing
4. Error logging with full exception details (using `exc_info=True`)
5. Logging for status update successes and failures

## ServerAction Lambda Enhancements

### Authorization Logging

**Location:** `check_authorization()` function

Enhanced logging includes:
- Initial authorization check with user, instance, and groups
- Success messages with authorization reason (admin/group member/owner)
- Denial warnings when authorization fails
- Exception logging with full stack traces

**Example Log Output:**
```
INFO: Authorization check: user=user@example.com, instance=i-1234567890abcdef0, groups=['admin']
INFO: Authorization SUCCESS: Admin user user@example.com authorized for instance i-1234567890abcdef0
```

### Queue Operation Logging

**Location:** `send_to_queue()` function

Enhanced logging includes:
- Queue operation initiation with action, instance, and user
- Message validation results
- SQS message sending with queue URL and message ID
- Initial status update to AppSync
- Success/failure for both queue and status operations
- Exception logging with full details

**Example Log Output:**
```
INFO: Queue operation initiated: action=start, instance=i-1234567890abcdef0, user=user@example.com
INFO: Queue operation: Sending message to SQS - action=start, instance=i-1234567890abcdef0, queue=https://sqs.us-east-1.amazonaws.com/...
INFO: Queue operation SUCCESS: Message sent to SQS - action=start, instance=i-1234567890abcdef0, messageId=abc-123
INFO: Sending initial PROCESSING status to AppSync: action=start, instance=i-1234567890abcdef0
INFO: Initial status update SUCCESS: action=start, instance=i-1234567890abcdef0
```

### AppSync Status Update Logging

**Location:** `send_status_to_appsync()` function

Enhanced logging includes:
- Status update initiation with all parameters
- HTTP response codes and error messages
- Success/failure indicators
- Exception logging with full stack traces

**Example Log Output:**
```
INFO: AppSync status update: action=start, instance=i-1234567890abcdef0, status=PROCESSING, user=user@example.com
INFO: AppSync status update SUCCESS: action=start, instance=i-1234567890abcdef0, status=PROCESSING
```

### Error Handling

All exception handlers now use `exc_info=True` to capture full stack traces:
- Token processing errors
- Authorization check errors
- Queue operation errors
- AppSync communication errors

## ServerActionProcessor Lambda Enhancements

### Action Processing Logging

**Location:** `process_server_action()` function

Enhanced logging includes:
- Message parsing with body length
- Field extraction and validation
- Action routing decisions
- Handler execution tracking
- Final status determination
- Exception logging with full context

**Example Log Output:**
```
INFO: Action processing started: message_body_length=256
INFO: Message parsed successfully: action=start, instance=i-1234567890abcdef0
INFO: Action processing: action=start, instance=i-1234567890abcdef0, user=user@example.com, has_arguments=False
INFO: Routing action to handler: action=start, instance=i-1234567890abcdef0
INFO: Routing to handle_server_action(start): instance=i-1234567890abcdef0
INFO: Action completed successfully: action=start, instance=i-1234567890abcdef0
```

### Handler Logging

**Location:** `handle_server_action()`, `handle_fix_role()`, `handle_update_server_config()` functions

Enhanced logging includes:
- Handler initiation with parameters
- Instance state retrieval
- EC2 API call execution
- Success/failure/skip indicators
- Detailed configuration processing steps
- Exception logging with full stack traces

**Example Log Output:**
```
INFO: Server action handler started: action=start, instance=i-1234567890abcdef0
INFO: Retrieving instance information: instance=i-1234567890abcdef0
INFO: Instance state retrieved: instance=i-1234567890abcdef0, state=stopped
INFO: Executing EC2 start_instances: instance=i-1234567890abcdef0
INFO: Server action SUCCESS: Start initiated for instance i-1234567890abcdef0
```

### AppSync Status Update Logging

**Location:** `send_to_appsync()` function

Enhanced logging includes:
- Status update initiation with all parameters
- Endpoint configuration checks
- HTTP response tracking
- Success/failure indicators
- Exception logging with full details

**Example Log Output:**
```
INFO: AppSync status update: action=start, instance=i-1234567890abcdef0, status=COMPLETED, user=user@example.com, message=Successfully completed start
INFO: Sending status to AppSync endpoint: action=start, instance=i-1234567890abcdef0, status=COMPLETED
INFO: AppSync status update SUCCESS: action=start, instance=i-1234567890abcdef0, status=COMPLETED
```

### SQS Handler Logging

**Location:** `handler()` function

Enhanced logging includes:
- Record count on invocation
- Per-message processing tracking with message IDs
- Success/failure for each message

**Example Log Output:**
```
INFO: SQS handler invoked: record_count=1
INFO: Processing SQS message 1/1: messageId=abc-123
INFO: Message processing SUCCESS: messageId=abc-123
```

## Logging Format Standards

All enhanced log messages follow these patterns:

### Success Messages
```
INFO: <Operation> SUCCESS: <details>
```

### Failure Messages
```
ERROR: <Operation> FAILED: <details>
```

### Warning Messages
```
WARNING: <Operation> SKIPPED/DENIED: <details>
```

### Exception Messages
```
ERROR: <Operation> FAILED with exception: <details>, exc_info=True
```

## Benefits

1. **Troubleshooting**: Detailed logs make it easy to trace request flow and identify issues
2. **Monitoring**: Structured log format enables easy parsing and alerting
3. **Audit Trail**: Complete record of authorization decisions and actions
4. **Performance**: Logs include timing information for optimization
5. **Debugging**: Full stack traces with `exc_info=True` for all exceptions

## CloudWatch Insights Queries

### Find Authorization Failures
```
fields @timestamp, @message
| filter @message like /Authorization DENIED/
| sort @timestamp desc
```

### Find Queue Operation Failures
```
fields @timestamp, @message
| filter @message like /Queue operation FAILED/
| sort @timestamp desc
```

### Find Action Processing Failures
```
fields @timestamp, @message
| filter @message like /Action processing FAILED/
| sort @timestamp desc
```

### Track Action Flow
```
fields @timestamp, @message
| filter @message like /action=start/ and @message like /instance=i-1234567890abcdef0/
| sort @timestamp asc
```

## Requirements Satisfied

This implementation satisfies the following requirements from the spec:

- **Requirement 1.5**: Enhanced error handling for queue operations
- **Requirement 4.5**: Detailed logging for action processing in ServerActionProcessor

## Testing

A verification script (`test_logging_verification.py`) has been created to validate that all logging enhancements are present in the code. Run it with:

```bash
python3 lambdas/serverAction/test_logging_verification.py
```

The script verifies:
- Authorization logging statements (4 types)
- Queue operation logging statements (4 types)
- AppSync status logging statements (3 types)
- Exception logging with `exc_info=True` (multiple instances)
- Action processing logging statements (4 types)
- Handler logging statements (3 types)

## Future Enhancements

Potential future improvements:
1. Structured logging with JSON format for easier parsing
2. Correlation IDs to track requests across Lambda invocations
3. Performance metrics logging (execution time, memory usage)
4. Custom CloudWatch metrics for key operations
5. Log sampling for high-volume operations
