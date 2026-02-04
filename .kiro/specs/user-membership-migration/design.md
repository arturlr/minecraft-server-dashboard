# Design Document

## Overview

This feature migrates the user membership system from AWS Cognito user groups to DynamoDB storage with role-based access control. Currently, each EC2 instance has an associated Cognito user group that controls which users can perform actions against that server. This system will be completely replaced with a DynamoDB-based membership model that stores user email, Cognito sub, server instance ID, and role information directly in a dedicated table.

The migration introduces three distinct roles (admin, moderator, viewer) with different permission levels, providing more granular access control than the current binary group membership model. All existing Lambda functions will be updated to use DynamoDB queries instead of Cognito group checks for authorization decisions.

## Architecture

### Current System (To Be Replaced)
```
User Authentication → Cognito Groups → Authorization Check
                     (per-server groups)
```

### New System (Target Architecture)
```
User Authentication → DynamoDB Membership Table → Role-Based Authorization
                     (centralized membership with roles)
```

### Data Flow Changes

**Before (Cognito Groups)**:
1. User authenticates via Cognito
2. Lambda extracts user groups from JWT token
3. Authorization checks if user belongs to instance-specific group
4. Binary access: member or not member

**After (DynamoDB Membership)**:
1. User authenticates via Cognito (unchanged)
2. Lambda queries DynamoDB membership table by user sub + instance ID
3. Authorization checks user's role for the specific server
4. Role-based access: admin, moderator, or viewer permissions

## Components and Interfaces

### 1. DynamoDB Membership Table

**Table Name**: `{ProjectName}-{EnvironmentName}-UserMembership`

**Primary Key Design**:
- **Partition Key**: `userId` (String) - Cognito sub
- **Sort Key**: `serverId` (String) - EC2 instance ID

**Attributes**:
```javascript
{
  userId: String,        // Cognito sub (partition key)
  serverId: String,      // EC2 instance ID (sort key)
  email: String,         // User's email address
  role: String,          // admin | moderator | viewer
  createdAt: String,     // ISO timestamp
  updatedAt: String,     // ISO timestamp
  createdBy: String      // Email of user who added this membership
}
```

**Global Secondary Index (GSI)**:
- **GSI Name**: `ServerMembership-Index`
- **Partition Key**: `serverId` (String)
- **Sort Key**: `role` (String)
- **Purpose**: Efficiently query all members of a server, optionally filtered by role

### 2. Updated GraphQL Schema

**New Types**:
```graphql
type UserMembership @aws_iam @aws_cognito_user_pools {
  userId: String!
  serverId: String!
  email: AWSEmail!
  role: MembershipRole!
  createdAt: AWSDateTime!
  updatedAt: AWSDateTime!
  createdBy: AWSEmail!
}

enum MembershipRole {
  admin
  moderator
  viewer
}

input UserMembershipInput {
  userId: String!
  serverId: String!
  email: AWSEmail!
  role: MembershipRole!
  createdBy: AWSEmail!
}

input UpdateUserRoleInput {
  userId: String!
  serverId: String!
  role: MembershipRole!
}
```

**Updated ServerUsers Type**:
```graphql
type ServerUsers @aws_iam @aws_cognito_user_pools {
  id: String!
  email: AWSEmail!
  fullName: String!
  role: MembershipRole!  # New field
}
```

**New Mutations**:
```graphql
updateUserRole(input: UpdateUserRoleInput!): UserMembership
  @aws_cognito_user_pools
removeUserFromServer(userId: String!, serverId: String!): AWSJSON
  @aws_cognito_user_pools
```

### 3. Updated Lambda Functions

#### 3.1 Auth Helper Layer Updates

**New Methods**:
```python
class Auth:
    def get_user_membership(self, user_sub, server_id):
        """Get user's membership for a specific server"""
        
    def list_server_members(self, server_id, role_filter=None):
        """List all members of a server, optionally filtered by role"""
        
    def create_membership(self, user_sub, server_id, email, role, created_by):
        """Create a new membership record"""
        
    def update_user_role(self, user_sub, server_id, new_role):
        """Update a user's role for a server"""
        
    def remove_membership(self, user_sub, server_id):
        """Remove a user's membership from a server"""
        
    def check_user_permission(self, user_sub, server_id, required_permission):
        """Check if user has required permission level for server"""
```

**Permission Levels**:
```python
PERMISSION_LEVELS = {
    'viewer': 1,
    'moderator': 2, 
    'admin': 3
}

OPERATION_PERMISSIONS = {
    'read_server': 1,      # viewer and above
    'control_server': 2,   # moderator and above  
    'manage_users': 3,     # admin only
    'manage_config': 3     # admin only
}
```

#### 3.2 Util Helper Layer Updates

**Updated Authorization Method**:
```python
def check_user_authorization(self, user_sub, server_id, required_permission='read_server'):
    """
    New authorization check using DynamoDB membership
    
    Args:
        user_sub: Cognito user sub
        server_id: EC2 instance ID
        required_permission: Permission level required
        
    Returns:
        tuple: (is_authorized, user_role, auth_reason)
    """
```

#### 3.3 Migration Lambda Function

**New Function**: `migrateCognitoGroupsToDynamoDB`

**Purpose**: One-time migration of existing Cognito group memberships to DynamoDB

**Process**:
1. List all EC2 instances with the app tag
2. For each instance, check if Cognito group exists
3. List all members of each group
4. Extract user details (email, sub) from Cognito
5. Create DynamoDB membership records with admin role
6. Generate migration report
7. Verify migration completeness

### 4. Updated Lambda Function Authorization

#### 4.1 ec2Discovery Lambda
- Replace `cognito_groups` check with DynamoDB membership query
- Filter servers based on user's membership records
- Include role information in server list response

#### 4.2 ec2ActionValidator Lambda  
- Replace group-based authorization with role-based permission checks
- Validate required permission level for each operation
- Update error messages to include role requirements

#### 4.3 Other Lambda Functions
- Update all functions that currently use `utilHelper.check_user_authorization`
- Ensure consistent role-based permission checking across all operations

## Data Models

### User Membership Record
```javascript
{
  userId: "cognito-sub-uuid-here",
  serverId: "i-1234567890abcdef0", 
  email: "user@example.com",
  role: "admin",
  createdAt: "2024-01-08T10:30:00Z",
  updatedAt: "2024-01-08T10:30:00Z",
  createdBy: "admin@example.com"
}
```

### Role Permission Matrix
```javascript
{
  viewer: {
    permissions: ['read_server', 'read_metrics', 'read_config'],
    description: 'Can view server status and metrics only'
  },
  moderator: {
    permissions: ['read_server', 'read_metrics', 'read_config', 'control_server'],
    description: 'Can view and control server (start/stop/restart) but cannot manage users'
  },
  admin: {
    permissions: ['read_server', 'read_metrics', 'read_config', 'control_server', 'manage_users', 'manage_config'],
    description: 'Full access to server management, user management, and configuration'
  }
}
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Membership data integrity
*For any* membership creation operation, all required fields (userId, serverId, email, role) should be properly stored and retrievable from DynamoDB.
**Validates: Requirements 1.2**

### Property 2: DynamoDB query usage
*For any* membership query operation, the system should use DynamoDB queries instead of Cognito group membership checks and return data in the expected format.
**Validates: Requirements 1.3**

### Property 3: Membership removal consistency
*For any* user removal operation, the corresponding DynamoDB membership record should no longer exist after the operation completes.
**Validates: Requirements 1.4**

### Property 4: Referential integrity
*For any* membership record, the userId should reference a valid Cognito user and serverId should reference a valid EC2 instance.
**Validates: Requirements 1.5**

### Property 5: Role validation
*For any* role assignment operation, the system should accept only the three valid roles (admin, moderator, viewer) and reject invalid role values.
**Validates: Requirements 2.1**

### Property 6: Admin permission completeness
*For any* user with admin role, they should have access to all server management, user management, and server operation functions for their assigned servers.
**Validates: Requirements 2.2**

### Property 7: Moderator permission restrictions
*For any* user with moderator role, they should have access to server operations but be denied access to user management functions.
**Validates: Requirements 2.3**

### Property 8: Viewer permission limitations
*For any* user with viewer role, they should have read-only access to server status and metrics but be denied access to all write operations.
**Validates: Requirements 2.4**

### Property 9: Server-specific permission validation
*For any* permission check, the system should validate the user's role for the specific server being accessed, not their roles on other servers.
**Validates: Requirements 2.5**

### Property 10: Role-based operation enforcement
*For any* operation attempt, users should be prevented from performing actions that require a higher role level than they possess.
**Validates: Requirements 2.6**

### Property 11: Migration data completeness
*For any* migration execution, all existing Cognito group memberships should be identified and read correctly.
**Validates: Requirements 3.1**

### Property 12: Migration data extraction
*For any* group member during migration, the correct email and Cognito sub should be extracted from Cognito user details.
**Validates: Requirements 3.2**

### Property 13: Migration default role assignment
*For any* user migrated from Cognito groups, they should receive the admin role in the DynamoDB membership record.
**Validates: Requirements 3.3**

### Property 14: Migration completeness verification
*For any* migration execution, the count of migrated users should match the count of original group members across all servers.
**Validates: Requirements 3.4**

### Property 15: Migration reporting accuracy
*For any* completed migration, the migration report should contain accurate counts and details of migrated users per server.
**Validates: Requirements 3.5**

### Property 16: Migration idempotency
*For any* migration execution run multiple times, the final state should be identical regardless of how many times it's executed.
**Validates: Requirements 3.6**

### Property 17: DynamoDB authorization implementation
*For any* Lambda function permission check, the system should query the DynamoDB membership table rather than checking Cognito groups.
**Validates: Requirements 4.1**

### Property 18: Membership-based access validation
*For any* server access attempt, the system should verify that the user has a membership record for that specific server.
**Validates: Requirements 4.2**

### Property 19: Role-permission comparison
*For any* operation requiring specific permissions, the system should compare the required permission level with the user's actual role level.
**Validates: Requirements 4.3**

### Property 20: Authorization failure messaging
*For any* failed authorization attempt, the system should return error messages that indicate insufficient permissions with role requirements.
**Validates: Requirements 4.4**

### Property 21: DynamoDB-based user queries
*For any* getServerUsers query execution, the system should return user data from the DynamoDB membership table rather than Cognito groups.
**Validates: Requirements 5.1**

### Property 22: Membership record creation
*For any* addUserToServer mutation execution, the system should create a new DynamoDB membership record with the correct data.
**Validates: Requirements 5.2**

### Property 23: Default role assignment
*For any* new user addition (when role is not specified), the system should assign the viewer role by default.
**Validates: Requirements 5.3**

### Property 24: Role information in responses
*For any* user management operation response, the returned data should include role information for each user.
**Validates: Requirements 5.4**

### Property 25: Role update functionality
*For any* updateUserRole mutation by an admin user, the system should properly update the user's role in the DynamoDB record.
**Validates: Requirements 6.1**

### Property 26: Role update authorization
*For any* role update attempt, the system should validate that the requesting user has admin permissions for that server.
**Validates: Requirements 6.2**

### Property 27: Role update response completeness
*For any* successful role update, the system should return the complete updated membership information.
**Validates: Requirements 6.3**

### Property 28: Non-existent membership error handling
*For any* attempt to update a non-existent membership, the system should return an appropriate error message.
**Validates: Requirements 6.4**

### Property 29: Self-admin-role protection
*For any* attempt by a user to modify their own admin role, the system should prevent the operation to avoid lockout scenarios.
**Validates: Requirements 6.5**

### Property 30: DynamoDB error messaging
*For any* DynamoDB operation failure, the system should return descriptive error messages that help identify the issue.
**Validates: Requirements 7.1**

### Property 31: Permission error message format
*For any* insufficient permission scenario, the system should return "Insufficient permissions" with role requirements in a consistent format.
**Validates: Requirements 7.2**

### Property 32: Server not found error handling
*For any* attempt to access a non-existent server, the system should return a "Server not found" error message.
**Validates: Requirements 7.3**

### Property 33: Membership not found error handling
*For any* attempt to modify a non-existent membership, the system should return a "User membership not found" error message.
**Validates: Requirements 7.4**

### Property 34: Error message consistency
*For any* similar error condition across different Lambda functions, the error messages should be consistent in format and content.
**Validates: Requirements 7.5**

### Property 35: Membership operation logging
*For any* membership record creation or modification, the system should log the operation with user and server details.
**Validates: Requirements 8.1**

### Property 36: Authorization attempt logging
*For any* authorization check, the system should log the access attempt with the outcome (success/failure).
**Validates: Requirements 8.2**

### Property 37: Error operation logging
*For any* error in membership operations, the system should log detailed error information for troubleshooting.
**Validates: Requirements 8.3**

### Property 38: Migration progress logging
*For any* migration execution, the system should log progress updates and completion status.
**Validates: Requirements 8.4**

### Property 39: Audit-quality logging
*For any* logged event, the log entry should contain sufficient detail for security auditing and troubleshooting purposes.
**Validates: Requirements 8.5**

## Error Handling

### DynamoDB Operation Errors
- **ConditionalCheckFailedException**: "Membership record already exists" or "Membership record not found"
- **ValidationException**: "Invalid role value. Must be admin, moderator, or viewer"
- **ResourceNotFoundException**: "Membership table not found"
- **ProvisionedThroughputExceededException**: "Database temporarily unavailable. Please try again"
- **ItemCollectionSizeLimitExceededException**: "Too many memberships for this user"

### Authorization Errors
- **Insufficient Permissions**: "Insufficient permissions. Required role: {required_role}, your role: {user_role}"
- **No Membership**: "You do not have access to this server"
- **Invalid Server**: "Server not found or you do not have access"
- **Self-Role-Modification**: "Cannot modify your own admin role"

### Migration Errors
- **Cognito Access Error**: "Unable to access Cognito groups during migration"
- **Partial Migration**: "Migration completed with errors. See migration report for details"
- **Migration Verification Failed**: "Migration verification failed. Manual review required"

### Input Validation Errors
- **Invalid Role**: "Invalid role. Must be one of: admin, moderator, viewer"
- **Missing Required Fields**: "Required fields missing: {field_names}"
- **Invalid User ID**: "Invalid user ID format"
- **Invalid Server ID**: "Invalid server ID format"

## Testing Strategy

### Unit Testing

**Framework**: pytest (Python) for Lambda functions

**Test Coverage**:

1. **DynamoDB Operations Tests**
   - Test membership record creation with all required fields
   - Test membership record updates and deletions
   - Test query operations with various filters
   - Test error handling for DynamoDB exceptions
   - Test GSI queries for server membership lists

2. **Authorization Logic Tests**
   - Test role-based permission checking for all operations
   - Test permission level comparisons
   - Test server-specific authorization validation
   - Test admin, moderator, and viewer access patterns
   - Test authorization failure scenarios

3. **Migration Function Tests**
   - Test Cognito group enumeration and user extraction
   - Test DynamoDB record creation during migration
   - Test migration idempotency
   - Test migration reporting and verification
   - Test error handling during migration

4. **GraphQL Resolver Tests**
   - Test updated getServerUsers query with role information
   - Test addUserToServer mutation with DynamoDB integration
   - Test updateUserRole mutation with authorization checks
   - Test removeUserFromServer mutation
   - Test error responses for invalid operations

5. **Lambda Function Integration Tests**
   - Test ec2Discovery with DynamoDB membership filtering
   - Test ec2ActionValidator with role-based authorization
   - Test all Lambda functions that use authorization
   - Test consistent error message formats across functions

### Property-Based Testing

**Framework**: Hypothesis (Python property-based testing library)

**Configuration**: Each property test should run a minimum of 100 iterations to ensure comprehensive coverage across the input space.

**Test Tagging**: Each property-based test must include a comment explicitly referencing the correctness property from this design document using the format: `// Feature: user-membership-migration, Property {number}: {property_text}`

**Property Tests**:

1. **Property 1: Membership data integrity**
   - Generate random membership data with valid userId, serverId, email, and role
   - Create membership records and verify all fields are stored and retrievable
   - **Tag**: `# Feature: user-membership-migration, Property 1: Membership data integrity`

2. **Property 5: Role validation**
   - Generate random role values including valid and invalid options
   - Test that only admin, moderator, and viewer are accepted
   - **Tag**: `# Feature: user-membership-migration, Property 5: Role validation`

3. **Property 16: Migration idempotency**
   - Generate random sets of Cognito group memberships
   - Run migration multiple times and verify identical final states
   - **Tag**: `# Feature: user-membership-migration, Property 16: Migration idempotency`

4. **Property 19: Role-permission comparison**
   - Generate random combinations of user roles and required permissions
   - Verify that permission checks correctly compare role levels
   - **Tag**: `# Feature: user-membership-migration, Property 19: Role-permission comparison`

5. **Property 34: Error message consistency**
   - Generate various error scenarios across different Lambda functions
   - Verify that similar errors produce consistent message formats
   - **Tag**: `# Feature: user-membership-migration, Property 34: Error message consistency`

### Integration Testing

**Test Scenarios**:
- End-to-end user addition flow from GraphQL to DynamoDB
- Complete migration process with verification
- Authorization flow from JWT token to DynamoDB membership check
- Role update flow with proper authorization validation

### Performance Testing

**Load Testing**:
- Test DynamoDB query performance with large membership datasets
- Test concurrent membership operations
- Test migration performance with large numbers of users and servers

**Optimization Targets**:
- Membership queries should complete within 100ms
- Migration should process 1000+ users within 5 minutes
- Authorization checks should add less than 50ms to operation latency

## Implementation Notes

### DynamoDB Table Design Considerations

**Partition Key Choice**: Using `userId` as partition key distributes load evenly across users and supports efficient user-centric queries.

**Sort Key Choice**: Using `serverId` as sort key enables range queries for a user's server memberships and supports the composite primary key requirement.

**GSI Design**: The `ServerMembership-Index` GSI enables efficient server-centric queries (list all members of a server) which is the primary access pattern for the existing `getServerUsers` query.

### Migration Strategy

**Phased Approach**:
1. **Phase 1**: Deploy new DynamoDB table and migration function
2. **Phase 2**: Run migration to populate membership data
3. **Phase 3**: Deploy updated Lambda functions with dual-mode support (check both Cognito and DynamoDB)
4. **Phase 4**: Verify all operations work with DynamoDB
5. **Phase 5**: Remove Cognito group dependencies and clean up

**Rollback Plan**: Maintain Cognito groups during transition period to enable rollback if issues are discovered.

### Security Considerations

**Data Protection**:
- Email addresses are stored in DynamoDB but are already available in Cognito
- No additional PII is introduced beyond what's already in the system
- DynamoDB table uses encryption at rest

**Authorization Security**:
- Role-based permissions provide more granular control than binary group membership
- Admin role protection prevents accidental lockouts
- Centralized authorization logic reduces security vulnerabilities

**Audit Trail**:
- All membership changes are logged with timestamps and initiating user
- Migration process creates comprehensive audit log
- Authorization attempts are logged for security monitoring

### Performance Optimizations

**Query Patterns**:
- Primary key queries for user-server membership checks (most common)
- GSI queries for server member lists (less frequent)
- Batch operations for migration efficiency

**Caching Strategy**:
- Consider caching user memberships in Lambda memory for frequently accessed servers
- Cache TTL should be short (5-10 minutes) to ensure role changes take effect quickly

**Connection Pooling**:
- Reuse DynamoDB connections across Lambda invocations
- Use connection pooling for migration function to handle large datasets efficiently

## Deployment Considerations

### CloudFormation Updates

**New Resources**:
- DynamoDB UserMembership table with GSI
- IAM permissions for Lambda functions to access new table
- Migration Lambda function with appropriate timeouts and memory

**Updated Resources**:
- All existing Lambda functions need DynamoDB permissions
- AppSync schema updates for new types and mutations
- Environment variables for new table name

### Migration Execution

**Prerequisites**:
- Backup existing Cognito group memberships
- Verify all EC2 instances have proper tags
- Ensure sufficient DynamoDB capacity for migration load

**Execution Steps**:
1. Deploy infrastructure changes
2. Run migration function with dry-run mode first
3. Execute actual migration with monitoring
4. Verify migration results against backup data
5. Update Lambda functions to use DynamoDB
6. Test all functionality thoroughly
7. Clean up Cognito groups (optional, after verification period)

### Monitoring and Alerting

**Key Metrics**:
- DynamoDB read/write capacity utilization
- Lambda function error rates and duration
- Authorization check success/failure rates
- Migration progress and completion status

**Alerts**:
- DynamoDB throttling events
- Authorization failures above baseline
- Migration function failures or timeouts
- Inconsistent membership data detection