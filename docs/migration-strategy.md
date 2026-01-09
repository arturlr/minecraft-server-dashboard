# Data Migration Strategy: ServersTable + UserMembershipTable → CoreTable

## Overview
This document outlines the strategy for migrating data from the current two-table structure (ServersTable and UserMembershipTable) to the new single CoreTable with PK/SK pattern.

## Migration Approach

### Phase 1: Preparation
1. **Deploy CoreTable alongside existing tables** (parallel deployment)
2. **Update Lambda functions** to use CoreTableDyn class
3. **Test new functionality** with empty CoreTable
4. **Create migration Lambda function**

### Phase 2: Data Migration
1. **Scan ServersTable** and transform to CoreTable format
2. **Scan UserMembershipTable** and transform to CoreTable format  
3. **Validate data integrity** after migration
4. **Switch traffic** to use CoreTable
5. **Monitor for issues**

### Phase 3: Cleanup
1. **Verify system stability** for 24-48 hours
2. **Remove old table references** from CloudFormation
3. **Delete old tables** (ServersTable, UserMembershipTable)

## Data Transformation

### ServersTable → CoreTable
```
OLD: {id: "i-1234567890abcdef0", name: "MyServer", ...}
NEW: {
  PK: "SERVER#i-1234567890abcdef0",
  SK: "METADATA", 
  Type: "Server",
  name: "MyServer",
  hostname: "...",
  region: "...",
  ...
}
```

### UserMembershipTable → CoreTable
```
OLD: {userId: "abc123", serverId: "i-1234567890abcdef0", role: "admin", email: "user@example.com"}
NEW: {
  PK: "USER#abc123",
  SK: "SERVER#i-1234567890abcdef0",
  Type: "UserServer", 
  role: "admin",
  permissions: ["read", "write", "delete", "manage_users"]
}
```

### User Metadata Creation
```
NEW: {
  PK: "USER#abc123",
  SK: "METADATA",
  Type: "User",
  email: "user@example.com",
  name: "User Name" // from Cognito lookup
}
```

## Migration Lambda Function

```python
import boto3
import logging
from decimal import Decimal

def lambda_handler(event, context):
    """
    Migrate data from ServersTable and UserMembershipTable to CoreTable
    """
    dynamodb = boto3.resource('dynamodb')
    
    # Table references
    servers_table = dynamodb.Table('ServersTable')
    membership_table = dynamodb.Table('UserMembershipTable') 
    core_table = dynamodb.Table('CoreTable')
    
    try:
        # Step 1: Migrate servers
        migrate_servers(servers_table, core_table)
        
        # Step 2: Migrate user memberships
        migrate_memberships(membership_table, core_table)
        
        # Step 3: Create user metadata records
        create_user_metadata(membership_table, core_table)
        
        return {'statusCode': 200, 'body': 'Migration completed successfully'}
        
    except Exception as e:
        logging.error(f"Migration failed: {str(e)}")
        return {'statusCode': 500, 'body': f'Migration failed: {str(e)}'}

def migrate_servers(servers_table, core_table):
    """Migrate server records to CoreTable"""
    response = servers_table.scan()
    
    with core_table.batch_writer() as batch:
        for item in response['Items']:
            server_id = item['id']
            
            # Transform to CoreTable format
            core_item = {
                'PK': f'SERVER#{server_id}',
                'SK': 'METADATA',
                'Type': 'Server',
                **{k: v for k, v in item.items() if k != 'id'}
            }
            
            batch.put_item(Item=core_item)
    
    logging.info(f"Migrated {len(response['Items'])} servers")

def migrate_memberships(membership_table, core_table):
    """Migrate user memberships to CoreTable"""
    response = membership_table.scan()
    
    # Permission mapping
    permissions_map = {
        'admin': ['read', 'write', 'delete', 'manage_users'],
        'moderator': ['read', 'write', 'restart'], 
        'viewer': ['read']
    }
    
    with core_table.batch_writer() as batch:
        for item in response['Items']:
            user_id = item['userId']
            server_id = item['serverId']
            role = item['role']
            
            # Transform to CoreTable format
            core_item = {
                'PK': f'USER#{user_id}',
                'SK': f'SERVER#{server_id}',
                'Type': 'UserServer',
                'role': role,
                'permissions': permissions_map.get(role, ['read'])
            }
            
            batch.put_item(Item=core_item)
    
    logging.info(f"Migrated {len(response['Items'])} memberships")

def create_user_metadata(membership_table, core_table):
    """Create user metadata records from membership data"""
    response = membership_table.scan()
    
    # Get unique users
    users = {}
    for item in response['Items']:
        user_id = item['userId']
        if user_id not in users:
            users[user_id] = {
                'email': item.get('email', ''),
                'name': item.get('email', '').split('@')[0]  # Simple name extraction
            }
    
    with core_table.batch_writer() as batch:
        for user_id, user_data in users.items():
            core_item = {
                'PK': f'USER#{user_id}',
                'SK': 'METADATA', 
                'Type': 'User',
                'email': user_data['email'],
                'name': user_data['name']
            }
            
            batch.put_item(Item=core_item)
    
    logging.info(f"Created metadata for {len(users)} users")
```

## Rollback Strategy

If issues are discovered after migration:

1. **Immediate rollback**: Update Lambda environment variables to use old table names
2. **Data rollback**: Re-deploy old CloudFormation template to restore old tables
3. **Investigation**: Analyze issues and fix CoreTable implementation
4. **Re-attempt**: Fix issues and retry migration

## Validation Steps

After migration, validate:

1. **Record counts match**: CoreTable has correct number of records
2. **Data integrity**: Spot-check transformed data accuracy
3. **Functionality tests**: Test key user workflows
4. **Performance**: Monitor query performance on CoreTable

## Deployment Order

1. Deploy CoreTable (alongside existing tables)
2. Deploy updated Lambda functions
3. Run migration Lambda
4. Switch environment variables to use CoreTable
5. Monitor and validate
6. Remove old tables after stability confirmed

## Risk Mitigation

- **Parallel deployment**: Keep old tables during migration
- **Gradual rollout**: Test with subset of users first
- **Monitoring**: Set up CloudWatch alarms for errors
- **Quick rollback**: Environment variable switch for immediate rollback
- **Data backup**: Export old table data before deletion
