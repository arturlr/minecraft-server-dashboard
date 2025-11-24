# Refactor: Fix Server Role Lambda Separation

## Overview
Separated IAM profile management functionality from `serverActionProcessor` into a dedicated `fixServerRole` Lambda function.

## Problem
The IAM profile management logic was embedded in `serverActionProcessor`, which created unnecessary coupling:
- `fixServerRole` mutation → `serverAction` → SQS Queue → `serverActionProcessor`
- IAM operations mixed with server control operations (start/stop/restart)
- Unnecessary async processing for a quick synchronous operation

## Solution
Created a dedicated `fixServerRole` Lambda function that:
- Handles IAM profile management directly (synchronous)
- Bypasses the SQS queue (not needed for quick operations)
- Has focused permissions (only IAM-related)
- Simplifies the architecture

## Architecture Changes

### Before
```
fixServerRole mutation
  ↓
serverAction Lambda (validates, queues)
  ↓
SQS Queue
  ↓
serverActionProcessor Lambda (processes IAM + server actions)
```

### After
```
fixServerRole mutation
  ↓
fixServerRole Lambda (handles IAM directly)

Other mutations (start/stop/restart/config)
  ↓
serverAction Lambda (validates, queues)
  ↓
SQS Queue
  ↓
serverActionProcessor Lambda (processes server actions only)
```

## Files Changed

### New Files
- `lambdas/fixServerRole/index.py` - New dedicated Lambda for IAM profile management
- `lambdas/fixServerRole/requirements.txt` - Dependencies

### Modified Files
- `cfn/templates/lambdas.yaml`:
  - Added `FixServerRole` Lambda function definition
  - Added `FixServerRoleDataSource` and `fixServerRoleFunction` to AppSync
  - Updated `fixServerRole` resolver to use `fixServerRoleFunction` instead of `serverActionFunction`
  - Removed IAM permissions from `serverActionProcessor`
  - Removed EC2_INSTANCE_PROFILE environment variables from `serverActionProcessor`
  - Added output for `FixServerRole` Lambda

- `lambdas/serverActionProcessor/index.py`:
  - Removed `IamProfile` class (moved to fixServerRole Lambda)
  - Removed `handle_fix_role` function
  - Removed routing for 'fixserverrole' and 'fixrole' actions

- `lambdas/serverAction/index.py`:
  - Removed 'fixServerRole' and 'fixserverrole' from allowed actions list

## Benefits
1. **Separation of Concerns**: IAM management is now isolated from server control operations
2. **Simpler Architecture**: No unnecessary queueing for synchronous operations
3. **Better Performance**: Direct execution instead of queue → processor flow
4. **Clearer Permissions**: Each Lambda has only the permissions it needs
5. **Easier Maintenance**: Changes to IAM logic don't affect server control logic

## Frontend Impact
No changes required in the frontend. The GraphQL mutation `fixServerRole` continues to work the same way, just with a different backend implementation.

## Deployment Notes
When deploying this change:
1. Deploy the CloudFormation stack update (creates new Lambda)
2. The new `fixServerRole` Lambda will be automatically wired to the GraphQL resolver
3. Old IAM code in `serverActionProcessor` is removed but won't affect existing queued messages
4. No data migration needed
