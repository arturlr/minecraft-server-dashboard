# Refactor: Fix Server Role Lambda Separation

## Overview
Separated IAM profile management functionality from `ec2ActionWorker` into a dedicated `iamProfileManager` Lambda function.

## Problem
The IAM profile management logic was embedded in `ec2ActionWorker`, which created unnecessary coupling:
- `iamProfileManager` mutation → `ec2ActionValidator` → SQS Queue → `ec2ActionWorker`
- IAM operations mixed with server control operations (start/stop/restart)
- Unnecessary async processing for a quick synchronous operation

## Solution
Created a dedicated `iamProfileManager` Lambda function that:
- Handles IAM profile management directly (synchronous)
- Bypasses the SQS queue (not needed for quick operations)
- Has focused permissions (only IAM-related)
- Simplifies the architecture

## Architecture Changes

### Before
```
iamProfileManager mutation
  ↓
ec2ActionValidator Lambda (validates, queues)
  ↓
SQS Queue
  ↓
ec2ActionWorker Lambda (processes IAM + server actions)
```

### After
```
iamProfileManager mutation
  ↓
iamProfileManager Lambda (handles IAM directly)

Other mutations (start/stop/restart/config)
  ↓
ec2ActionValidator Lambda (validates, queues)
  ↓
SQS Queue
  ↓
ec2ActionWorker Lambda (processes server actions only)
```

## Files Changed

### New Files
- `lambdas/iamProfileManager/index.py` - New dedicated Lambda for IAM profile management
- `lambdas/iamProfileManager/requirements.txt` - Dependencies

### Modified Files
- `cfn/templates/lambdas.yaml`:
  - Added `iamProfileManager` Lambda function definition
  - Added `iamProfileManagerDataSource` and `iamProfileManagerFunction` to AppSync
  - Updated `iamProfileManager` resolver to use `iamProfileManagerFunction` instead of `ec2ActionValidatorFunction`
  - Removed IAM permissions from `ec2ActionWorker`
  - Removed EC2_INSTANCE_PROFILE environment variables from `ec2ActionWorker`
  - Added output for `iamProfileManager` Lambda

- `lambdas/ec2ActionWorker/index.py`:
  - Removed `IamProfile` class (moved to iamProfileManager Lambda)
  - Removed `handle_fix_role` function
  - Removed routing for 'iamProfileManager' and 'fixrole' actions

- `lambdas/ec2ActionValidator/index.py`:
  - Removed 'iamProfileManager' and 'iamProfileManager' from allowed actions list

## Benefits
1. **Separation of Concerns**: IAM management is now isolated from server control operations
2. **Simpler Architecture**: No unnecessary queueing for synchronous operations
3. **Better Performance**: Direct execution instead of queue → processor flow
4. **Clearer Permissions**: Each Lambda has only the permissions it needs
5. **Easier Maintenance**: Changes to IAM logic don't affect server control logic

## Frontend Impact
No changes required in the frontend. The GraphQL mutation `iamProfileManager` continues to work the same way, just with a different backend implementation.

## Deployment Notes
When deploying this change:
1. Deploy the CloudFormation stack update (creates new Lambda)
2. The new `iamProfileManager` Lambda will be automatically wired to the GraphQL resolver
3. Old IAM code in `ec2ActionWorker` is removed but won't affect existing queued messages
4. No data migration needed
