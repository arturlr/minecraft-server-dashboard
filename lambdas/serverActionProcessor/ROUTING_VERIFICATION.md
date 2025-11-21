# ServerActionProcessor Routing Verification

## Task 4 Implementation Summary

This document verifies that the ServerActionProcessor has been updated to handle all action types correctly according to Requirements 4.1-4.5.

## Changes Made

### 1. Enhanced Message Parsing (Requirement 4.1)

**Location**: `process_server_action()` function

**Improvements**:
- Added explicit JSON parsing with error handling for `JSONDecodeError`
- Added validation for required fields (`action`, `instanceId`)
- Improved error logging with specific messages for each failure type
- Preserved message object for error reporting in exception handlers

**Code**:
```python
# Parse message body
try:
    message = json.loads(message_body)
except json.JSONDecodeError as e:
    logger.error(f"Invalid JSON in message body: {e}")
    return False

# Extract required fields
if 'action' not in message:
    logger.error("Missing 'action' field in message")
    return False
if 'instanceId' not in message:
    logger.error("Missing 'instanceId' field in message")
    return False
```

### 2. Improved Action Routing (Requirements 4.2, 4.3, 4.4)

**Location**: `process_server_action()` function

**Routing Logic**:

| Action Input | Handler Function | Requirement |
|-------------|------------------|-------------|
| `start`, `startserver` | `handle_server_action('start', instance_id)` | 4.2 |
| `stop`, `stopserver` | `handle_server_action('stop', instance_id)` | 4.2 |
| `restart`, `restartserver` | `handle_server_action('restart', instance_id)` | 4.2 |
| `fixserverrole`, `fixrole` | `handle_fix_role(instance_id)` | 4.3 |
| `putserverconfig`, `updateserverconfig` | `handle_update_server_config(instance_id, arguments)` | 4.4 |

**Code**:
```python
if action in ['start', 'startserver']:
    result = handle_server_action('start', instance_id)
elif action in ['stop', 'stopserver']:
    result = handle_server_action('stop', instance_id)
elif action in ['restart', 'restartserver']:
    result = handle_server_action('restart', instance_id)
elif action in ['fixserverrole', 'fixrole']:
    result = handle_fix_role(instance_id)
elif action in ['putserverconfig', 'updateserverconfig']:
    result = handle_update_server_config(instance_id, arguments)
else:
    logger.error(f"Unknown action type: {action}")
    send_to_appsync(action, instance_id, "FAILED", f"Unknown action: {action}", user_email)
    return False
```

### 3. Comprehensive Error Handling (Requirement 4.5)

**Location**: All handler functions

**Error Handling Improvements**:

#### A. `process_server_action()` Error Handling
- JSON parsing errors caught and logged
- Missing field validation with specific error messages
- Handler exceptions caught with `exc_info=True` for full stack traces
- Graceful AppSync error reporting even when message parsing fails
- Unknown action types properly rejected with error status

#### B. `handle_server_action()` Error Handling
- Instance not found errors logged and returned as failure
- State validation before attempting operations
- Individual try-catch blocks for each EC2 API call
- Detailed logging with instance ID and action type
- Full exception info logged with `exc_info=True`

**Code**:
```python
if state == "stopped":
    try:
        ec2_client.start_instances(InstanceIds=[instance_id])
        logger.info(f"Successfully initiated start for instance {instance_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to start instance {instance_id}: {e}", exc_info=True)
        return False
```

#### C. `handle_fix_role()` Error Handling
- Wrapped entire function in try-catch
- Specific handling for UnauthorizedOperation errors
- Detailed logging of IAM profile operations
- Error dictionary responses properly handled

**Code**:
```python
try:
    logger.info(f"Starting IAM role fix for instance {instance_id}")
    iam_profile = IamProfile(instance_id)
    resp = iam_profile.manage_iam_profile()
    
    if isinstance(resp, dict) and resp.get("status") == "error":
        if resp.get("code") == "UnauthorizedOperation":
            logger.error(f"Unauthorized operation for instance {instance_id}: {resp.get('message', '')}")
            return False
    # ... rest of handling
except Exception as e:
    logger.error(f"Error in handle_fix_role for instance {instance_id}: {e}", exc_info=True)
    return False
```

#### D. `handle_update_server_config()` Error Handling
- Arguments validation at function start
- Try-catch for tag setting operations
- Separate error handling for schedule vs alarm configurations
- ValueError handling for invalid schedule expressions
- Detailed logging at each step of configuration
- Full exception info logged for all errors

**Code**:
```python
try:
    if not arguments:
        logger.error(f"Missing arguments for config update on instance {instance_id}")
        return False
    
    # Set instance attributes to tags
    try:
        response = ec2_utils.set_instance_attributes_to_tags(arguments)
    except Exception as e:
        logger.error(f"Failed to set instance attributes to tags for {instance_id}: {e}", exc_info=True)
        return False
    
    # ... configuration logic with detailed error handling
except Exception as e:
    logger.error(f"Error in handle_update_server_config for instance {instance_id}: {e}", exc_info=True)
    return False
```

## Verification Checklist

- [x] **Requirement 4.1**: Message body parsing correctly extracts action, instanceId, arguments, and userEmail
- [x] **Requirement 4.2**: start/stop/restart actions route to `handle_server_action`
- [x] **Requirement 4.3**: fixServerRole action routes to `handle_fix_role`
- [x] **Requirement 4.4**: putServerConfig/updateServerConfig actions route to `handle_update_server_config`
- [x] **Requirement 4.5**: Comprehensive error handling added for each action type with detailed logging

## Error Handling Coverage

| Error Scenario | Handler | Status |
|---------------|---------|--------|
| Invalid JSON | `process_server_action` | ✓ Handled |
| Missing action field | `process_server_action` | ✓ Handled |
| Missing instanceId field | `process_server_action` | ✓ Handled |
| Unknown action type | `process_server_action` | ✓ Handled |
| Handler exception | `process_server_action` | ✓ Handled |
| Instance not found | `handle_server_action` | ✓ Handled |
| Invalid instance state | `handle_server_action` | ✓ Handled |
| EC2 API failure | `handle_server_action` | ✓ Handled |
| Unauthorized IAM operation | `handle_fix_role` | ✓ Handled |
| IAM profile attachment failure | `handle_fix_role` | ✓ Handled |
| Missing config arguments | `handle_update_server_config` | ✓ Handled |
| Tag setting failure | `handle_update_server_config` | ✓ Handled |
| Invalid schedule expression | `handle_update_server_config` | ✓ Handled |
| Alarm configuration failure | `handle_update_server_config` | ✓ Handled |

## Status Update Flow

For each action, the following status updates are sent to AppSync:

1. **PROCESSING** - Sent when message is first received and parsed
2. **PROCESSING** - (Optional) Sent when handler begins execution
3. **COMPLETED** - Sent when action succeeds
4. **FAILED** - Sent when action fails (with error message)

All status updates include:
- `id` (instance ID)
- `action` (action type)
- `status` (PROCESSING/COMPLETED/FAILED)
- `timestamp` (current time)
- `message` (status description)
- `userEmail` (user who initiated action)

## Testing Recommendations

To fully verify this implementation:

1. **Unit Tests**: Test each handler function with mocked AWS clients
2. **Integration Tests**: Test end-to-end flow with real SQS messages
3. **Error Tests**: Verify error handling with intentionally failing operations
4. **Property Tests**: Verify routing correctness across all action types (Task 4.1)

## Conclusion

Task 4 has been successfully implemented. The ServerActionProcessor now:
- Correctly parses all message fields
- Routes all action types to appropriate handlers
- Handles errors comprehensively at every level
- Provides detailed logging for troubleshooting
- Sends appropriate status updates to AppSync

All requirements (4.1-4.5) have been satisfied.
