# Status Update Progression Property Test Summary

## Overview

This document summarizes the property-based test implementation for **Property 5: Status update progression** in the async-server-actions feature.

## Test File

`lambdas/serverActionProcessor/test_status_update_progression_property.py`

## Property Being Tested

**Property 5: Status update progression**

*For any* queued action, the system should send status updates in the correct sequence: PROCESSING (when queued) → PROCESSING (when processing starts) → COMPLETED or FAILED (when done).

**Validates: Requirements 2.1, 2.2, 2.3, 2.4**

## Test Implementation

The test suite contains 4 property-based tests that verify different aspects of status update progression:

### 1. test_successful_action_status_progression

**Purpose**: Verifies that successful actions follow the correct status progression.

**Property**: For any action that completes successfully in ServerActionProcessor, the system should send status updates in the correct sequence:
1. PROCESSING (when processing starts)
2. COMPLETED (when done)

**Validates**: Requirements 2.2, 2.3

**Test Strategy**:
- Generates random actions, instance IDs, and user emails
- Mocks handler functions to return success (True)
- Captures all status updates sent to AppSync
- Verifies:
  - At least 2 status updates are sent
  - First status is PROCESSING
  - Final status is COMPLETED
  - No FAILED status in the sequence
  - PROCESSING comes before COMPLETED

### 2. test_failed_action_status_progression

**Purpose**: Verifies that failed actions follow the correct status progression.

**Property**: For any action that fails in ServerActionProcessor, the system should send status updates in the correct sequence:
1. PROCESSING (when processing starts)
2. FAILED (when handler fails)

**Validates**: Requirements 2.2, 2.4

**Test Strategy**:
- Generates random actions, instance IDs, and user emails
- Mocks handler functions to return failure (False)
- Captures all status updates sent to AppSync
- Verifies:
  - At least 2 status updates are sent
  - First status is PROCESSING
  - Final status is FAILED
  - No COMPLETED status in the sequence
  - PROCESSING comes before FAILED

### 3. test_status_updates_contain_required_fields

**Purpose**: Verifies that all status updates contain the required fields.

**Property**: For any action, all status updates should contain the required fields: action, instanceId, and status.

**Validates**: Requirements 2.5

**Test Strategy**:
- Generates random actions, instance IDs, and user emails
- Captures all status updates sent to AppSync
- Verifies each status update contains:
  - 'action' field (not None)
  - 'instanceId' field (not None, matches expected)
  - 'status' field (not None, one of PROCESSING/COMPLETED/FAILED)

### 4. test_no_status_regression

**Purpose**: Verifies that status updates never regress from a final state back to PROCESSING.

**Property**: For any action, status updates should never regress from a final state (COMPLETED or FAILED) back to PROCESSING.

**Validates**: Requirements 2.2, 2.3, 2.4

**Test Strategy**:
- Generates random actions, instance IDs, and user emails
- Captures all status updates sent to AppSync
- Verifies:
  - Once a COMPLETED or FAILED status is sent, no subsequent PROCESSING status is sent
  - This ensures the status progression is monotonic (always moving forward)

## Test Configuration

- **Test Framework**: Hypothesis (property-based testing)
- **Iterations**: 100 examples per test (configurable via @settings decorator)
- **Action Types Tested**: All write operations (start, stop, restart, fixServerRole, putServerConfig, updateServerConfig)
- **Instance ID Pattern**: Valid EC2 instance ID format (i-[0-9a-f]{17})
- **User Email**: Valid email addresses

## Test Results

All 4 tests pass successfully:
- ✅ test_successful_action_status_progression
- ✅ test_failed_action_status_progression
- ✅ test_status_updates_contain_required_fields
- ✅ test_no_status_regression

## Key Insights

1. **Status Progression is Correct**: The ServerActionProcessor correctly sends PROCESSING status when it starts processing, and then sends either COMPLETED or FAILED based on the handler result.

2. **Required Fields are Present**: All status updates include the required fields (action, instanceId, status), ensuring clients can properly track action progress.

3. **No Status Regression**: The system never regresses from a final state back to PROCESSING, which is critical for maintaining a consistent user experience.

4. **Separation of Concerns**: The test focuses on the ServerActionProcessor component only, which is appropriate since this component is responsible for sending status updates during action processing.

## Note on Test Scope

This test focuses on the ServerActionProcessor component's status update behavior. The complete end-to-end status progression (including the initial PROCESSING status sent by ServerAction when queueing) is verified through the combination of:
- This test (ServerActionProcessor status updates)
- The write operations queued property test (ServerAction queueing and initial status)

Together, these tests provide comprehensive coverage of the full status update progression property.
