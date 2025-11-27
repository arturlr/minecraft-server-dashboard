# New Server Configuration Fields

## Overview
Added three new fields to ServerConfig for tracking instance bootstrap status, Minecraft version, and patch updates.

## New Fields

### 1. isBootstrapped (Boolean)
- **Purpose**: Track whether the EC2 instance has completed initial bootstrap
- **Default**: `false`
- **Use Case**: Determine if instance is ready for Minecraft server operations
- **Updated By**: Bootstrap SSM document or Lambda after successful setup

### 2. minecraftVersion (String)
- **Purpose**: Track the installed Minecraft server version
- **Default**: Empty string
- **Use Case**: Display version in UI, track version across instances
- **Format**: e.g., "1.20.4", "1.19.2"
- **Updated By**: Bootstrap process or manual configuration

### 3. latestPatchUpdate (String)
- **Purpose**: Track when the instance last received system patches/updates
- **Default**: Empty string
- **Use Case**: Monitor instance maintenance, security compliance
- **Format**: ISO 8601 timestamp (e.g., "2024-01-15T10:30:00Z")
- **Updated By**: Automated patch process or manual updates

## Changes Made

### 1. GraphQL Schema (`appsync/schema.graphql`)
```graphql
type ServerConfig {
  # ... existing fields ...
  isBootstrapped: Boolean
  minecraftVersion: String
  latestPatchUpdate: String
}

input ServerConfigInput {
  # ... existing fields ...
  isBootstrapped: Boolean
  minecraftVersion: String
  latestPatchUpdate: String
}
```

### 2. ddbHelper Layer (`layers/ddbHelper/ddbHelper.py`)
**Updated Methods:**
- `get_server_config()` - Returns new fields with proper defaults
- `put_server_config()` - Saves new fields to DynamoDB
- `update_server_config()` - Supports updating new fields individually

**Default Values:**
- `isBootstrapped`: `False`
- `minecraftVersion`: `''` (empty string)
- `latestPatchUpdate`: `''` (empty string)

### 3. Frontend GraphQL Queries (`dashboard/src/graphql/queries.js`)
Updated `getServerConfig` query to include:
```graphql
isBootstrapped
minecraftVersion
latestPatchUpdate
```

### 4. Frontend GraphQL Mutations (`dashboard/src/graphql/mutations.js`)
Updated `putServerConfig` mutation to include:
```graphql
isBootstrapped
minecraftVersion
latestPatchUpdate
```

## Usage Examples

### Setting Bootstrap Status
```python
# In Bootstrap SSM document or Lambda
ec2_utils.dyn.update_server_config({
    'id': instance_id,
    'isBootstrapped': True,
    'minecraftVersion': '1.20.4',
    'latestPatchUpdate': datetime.now(timezone.utc).isoformat()
})
```

### Checking Bootstrap Status
```python
# In any Lambda
config = ec2_utils.get_instance_attributes_from_tags(instance_id)
if config['isBootstrapped']:
    # Instance is ready
    start_minecraft_server(instance_id)
else:
    # Instance still bootstrapping
    logger.info(f"Instance {instance_id} not yet bootstrapped")
```

### Frontend Display
```javascript
// In Vue component
const config = await getServerConfig(instanceId);
if (config.isBootstrapped) {
  console.log(`Minecraft ${config.minecraftVersion} ready`);
  console.log(`Last patched: ${config.latestPatchUpdate}`);
}
```

## Integration Points

### Bootstrap Process
The Bootstrap SSM document should update these fields:
1. Set `isBootstrapped: false` at start
2. Install Minecraft and detect version
3. Set `minecraftVersion` after installation
4. Set `latestPatchUpdate` after system updates
5. Set `isBootstrapped: true` when complete

### UI Display
Recommended UI enhancements:
- Show bootstrap progress indicator
- Display Minecraft version badge
- Show "Last Updated" timestamp
- Warning if `latestPatchUpdate` is old (>30 days)

### Monitoring
Use these fields for:
- Alerting on failed bootstraps (isBootstrapped still false after timeout)
- Tracking version distribution across instances
- Identifying instances needing patches

## Backward Compatibility
- All new fields are optional in GraphQL schema
- Default values provided for missing data
- Existing instances will have default values until updated
- No breaking changes to existing functionality

## Testing Checklist
- [ ] Create new server config with new fields
- [ ] Update existing config with new fields
- [ ] Read config and verify new fields present
- [ ] Verify default values for existing instances
- [ ] Test bootstrap status tracking
- [ ] Test version display in UI
- [ ] Test patch update tracking
- [ ] Verify GraphQL queries return new fields
- [ ] Verify mutations accept new fields

## Future Enhancements
- Automated version detection from running Minecraft server
- Automated patch scheduling based on `latestPatchUpdate`
- Version upgrade workflows
- Bootstrap failure notifications
- Patch compliance reporting
