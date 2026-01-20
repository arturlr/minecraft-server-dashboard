# Migration: EC2 Tags to DynamoDB for Server Configuration

## Overview
Migrated server configuration storage from EC2 tags to DynamoDB ServersTable for better scalability, performance, and data management.

## Changes Made

### 1. ddbHelper Layer (`layers/ddbHelper/ddbHelper.py`)
**Updated Methods:**
- `get_server_config(instance_id)` - Retrieves server config from DynamoDB
- `put_server_config(config)` - Saves complete server configuration
- `update_server_config(config)` - Updates specific fields
- Legacy methods maintained for backward compatibility

**Schema Support:**
All ServerConfig GraphQL fields now stored in DynamoDB:
- `id` (String)
- `shutdownMethod` (String)
- `stopScheduleExpression` (String)
- `startScheduleExpression` (String)
- `alarmThreshold` (Float)
- `alarmEvaluationPeriod` (Int)
- `runCommand` (String)
- `workDir` (String)
- `timezone` (String)

### 2. Ec2Helper Layer (`layers/ec2Helper/ec2Helper.py`)
**Updated Methods:**
- `get_instance_attributes_from_tags()` - Now reads from DynamoDB instead of EC2 tags
- `set_instance_attributes_to_tags()` - Now writes to DynamoDB instead of EC2 tags
- Added ddbHelper import and initialization

### 3. CloudFormation (`cfn/templates/lambdas.yaml`)
**Infrastructure Changes:**
- Added `SERVERS_TABLE_NAME` to Globals environment variables
- Added `DynLayer` to Lambda functions:
  - `ec2Discovery`
  - `ec2ActionWorker`
- Added `DynamoDBCrudPolicy` for ServersTable access
- Removed EC2 tag permissions (DeleteTags, CreateTags) from ec2ActionWorker

### 4. EC2 Instance Creation (`layers/ec2Helper/ec2Helper.py`)
**Enhanced:**
- Added dual EBS volume support:
  - Root volume: 8 GB (OS)
  - Data volume: 50 GB (game/logs) on `/dev/sdf`
- Both volumes use gp3 (latest generation)
- Automatic volume tagging

### 5. EC2 Template (`cfn/templates/ec2.yaml`)
**Cleanup:**
- Removed `BootstrapEventRule` and `BootstrapEventRole`
- Removed `MinecraftStartupEventRule` and `MinecraftStartupRole`
- Consolidated package installation lists into `REQUIRED_PACKAGES` array
- Consolidated Java installation into single `install_java()` function

## Benefits

### Performance
- Faster reads/writes compared to EC2 tag API
- No EC2 API rate limiting concerns
- Batch operations support

### Scalability
- No EC2 tag limits (50 tags per resource)
- Unlimited configuration fields
- Better for large deployments

### Data Management
- Point-in-time recovery enabled
- TTL support for automatic cleanup
- Better query capabilities
- Audit trail with `updatedAt` timestamps

### Cost
- DynamoDB on-demand pricing more predictable
- Reduced EC2 API calls

## Migration Path

### For Existing Deployments
1. Deploy updated CloudFormation templates
2. Existing EC2 tags will remain but won't be used
3. First configuration update will migrate data to DynamoDB
4. EC2 tags can be manually cleaned up after verification

### For New Deployments
- Configuration automatically stored in DynamoDB
- No EC2 tags created for configuration

## Backward Compatibility
- Legacy method names preserved in ddbHelper
- EC2Helper method signatures unchanged
- GraphQL schema unchanged
- Frontend requires no changes

## Testing Checklist
- [ ] Create new server configuration
- [ ] Update existing server configuration
- [ ] Read server configuration
- [ ] Verify CloudWatch alarms still work
- [ ] Verify EventBridge schedules still work
- [ ] Test server start/stop/restart
- [ ] Verify configuration persists across instance restarts
- [ ] Test with multiple servers

## Rollback Plan
If issues arise, revert to EC2 tags by:
1. Restore previous Lambda layer versions
2. Restore previous CloudFormation templates
3. Data in DynamoDB can remain for future migration
