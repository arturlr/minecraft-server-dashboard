# Requirements Document: Multi-Tenancy

## Introduction

This document specifies the requirements for implementing multi-tenancy in the Minecraft Server Dashboard application. Multi-tenancy enables organizations to group users and servers together under a tenant entity, providing tenant-level access control, data isolation, and administrative capabilities while maintaining backward compatibility with the existing single-tenant architecture.

## Glossary

- **System**: The Minecraft Server Dashboard application
- **Tenant**: An organization or group that contains users and servers
- **Tenant_Admin**: A user with administrative privileges within a specific tenant
- **Global_Admin**: A user with administrative privileges across all tenants
- **User**: An authenticated individual who can access the system
- **Server**: A Minecraft server instance hosted on AWS EC2
- **Membership**: The relationship between a user and a tenant, including role information
- **Role**: The permission level assigned to a user within a tenant (admin, member, viewer)
- **Server_Assignment**: The relationship between a server and a tenant
- **CoreTable**: The DynamoDB table using PK/SK pattern for data storage
- **Tenant_Context**: The currently active tenant scope for a user's session
- **Invitation**: A request for a user to join a tenant
- **Data_Isolation**: The separation of tenant data to prevent cross-tenant access

## Requirements

### Requirement 1: Tenant Management

**User Story:** As a global admin, I want to create and manage tenants, so that I can organize servers and users into separate organizations.

#### Acceptance Criteria

1. THE System SHALL create a new tenant with a unique identifier, name, and creation timestamp
2. WHEN a tenant is created, THE System SHALL assign the creating user as a Tenant_Admin
3. THE System SHALL store tenant metadata in CoreTable using PK pattern TENANT#<tenantId>
4. WHEN a tenant is updated, THE System SHALL validate that the requesting user is a Tenant_Admin or Global_Admin
5. THE System SHALL allow Tenant_Admins to update tenant name and settings
6. WHEN a tenant is deleted, THE System SHALL verify that no servers are assigned to the tenant
7. IF a tenant has assigned servers, THEN THE System SHALL prevent deletion and return an error
8. THE System SHALL support querying all tenants for Global_Admins
9. THE System SHALL support querying a user's tenants based on their memberships

### Requirement 2: Tenant Membership Management

**User Story:** As a tenant admin, I want to manage user memberships in my tenant, so that I can control who has access to our servers.

#### Acceptance Criteria

1. WHEN a Tenant_Admin adds a user to a tenant, THE System SHALL create a membership record with the specified role
2. THE System SHALL store membership records in CoreTable using PK pattern USER#<userId> / SK pattern TENANT#<tenantId>
3. THE System SHALL support three tenant roles: admin, member, and viewer
4. WHEN a membership is created, THE System SHALL validate that the requesting user is a Tenant_Admin or Global_Admin
5. THE System SHALL allow Tenant_Admins to update user roles within their tenant
6. THE System SHALL allow Tenant_Admins to remove users from their tenant
7. WHEN a user is removed from a tenant, THE System SHALL revoke access to all servers within that tenant
8. THE System SHALL prevent removal of the last Tenant_Admin from a tenant
9. THE System SHALL support querying all members of a tenant
10. THE System SHALL support querying all tenants a user belongs to

### Requirement 3: Server-Tenant Assignment

**User Story:** As a tenant admin, I want to assign servers to my tenant, so that tenant members can access and manage those servers.

#### Acceptance Criteria

1. WHEN a server is assigned to a tenant, THE System SHALL create a server assignment record
2. THE System SHALL store server assignments in CoreTable by updating SERVER#<instanceId> / METADATA with tenantId field
3. THE System SHALL validate that the requesting user is a Tenant_Admin or Global_Admin for the target tenant
4. THE System SHALL allow a server to belong to only one tenant at a time
5. WHEN a server is reassigned to a different tenant, THE System SHALL update the tenantId field
6. THE System SHALL support querying all servers assigned to a tenant
7. WHEN a server assignment is created, THE System SHALL validate that the server exists
8. THE System SHALL allow Tenant_Admins to remove server assignments from their tenant
9. WHEN a server is unassigned from a tenant, THE System SHALL set the tenantId field to null

### Requirement 4: Tenant-Scoped Authorization

**User Story:** As a system architect, I want tenant-scoped authorization checks, so that users can only access servers and data within their authorized tenants.

#### Acceptance Criteria

1. WHEN a user requests server information, THE System SHALL verify the user has membership in the server's tenant
2. WHEN a user attempts to start, stop, or restart a server, THE System SHALL verify tenant membership with appropriate role
3. THE System SHALL allow tenant members with admin or member roles to control servers
4. THE System SHALL allow tenant members with viewer role to view server information but not control servers
5. WHEN a user queries servers, THE System SHALL return only servers from tenants the user belongs to
6. THE System SHALL enforce tenant isolation by validating tenantId in all server operations
7. WHERE a user is a Global_Admin, THE System SHALL grant access to all tenants and servers
8. WHEN a user updates server configuration, THE System SHALL verify the user is a Tenant_Admin or member of the server's tenant
9. THE System SHALL validate tenant membership before returning server metrics and logs

### Requirement 5: Tenant Context Management

**User Story:** As a user, I want to switch between my tenants, so that I can manage servers across different organizations.

#### Acceptance Criteria

1. WHEN a user logs in, THE System SHALL load all tenants the user belongs to
2. THE System SHALL set the first tenant as the default Tenant_Context
3. THE System SHALL allow users to switch their active Tenant_Context
4. WHEN a user switches Tenant_Context, THE System SHALL update the UI to show only servers from the selected tenant
5. THE System SHALL persist the selected Tenant_Context in the user's session
6. THE System SHALL display the current Tenant_Context in the UI header
7. WHEN a user has no tenant memberships, THE System SHALL display an empty state with instructions
8. THE System SHALL support querying the current Tenant_Context from the frontend

### Requirement 6: Tenant Invitation System

**User Story:** As a tenant admin, I want to invite users to my tenant, so that I can grant access to new team members.

#### Acceptance Criteria

1. WHEN a Tenant_Admin creates an invitation, THE System SHALL generate a unique invitation token
2. THE System SHALL store invitation records in CoreTable using PK pattern INVITATION#<invitationId>
3. THE System SHALL include tenant information, inviter information, role, and expiration timestamp in invitations
4. THE System SHALL set invitation expiration to 7 days from creation
5. WHEN a user accepts an invitation, THE System SHALL create a tenant membership with the specified role
6. WHEN a user accepts an invitation, THE System SHALL mark the invitation as accepted
7. IF an invitation is expired, THEN THE System SHALL prevent acceptance and return an error
8. THE System SHALL allow Tenant_Admins to revoke pending invitations
9. THE System SHALL support inviting users by email address
10. WHEN inviting a user who does not exist, THE System SHALL create a pending invitation that activates upon user registration

### Requirement 7: Backward Compatibility

**User Story:** As a system architect, I want to maintain backward compatibility, so that existing users and servers continue to function without disruption.

#### Acceptance Criteria

1. WHEN the system encounters a server without a tenantId, THE System SHALL treat it as a legacy server
2. THE System SHALL allow users with existing USER#<userId> / SERVER#<serverId> memberships to access legacy servers
3. WHEN a Global_Admin assigns a legacy server to a tenant, THE System SHALL migrate the server to tenant-scoped access
4. THE System SHALL preserve existing server configurations during tenant assignment
5. THE System SHALL support querying both tenant-scoped and legacy servers for backward compatibility
6. WHEN a user has both legacy memberships and tenant memberships, THE System SHALL return servers from both sources
7. THE System SHALL maintain existing authorization patterns for legacy servers

### Requirement 8: Tenant Settings and Configuration

**User Story:** As a tenant admin, I want to configure tenant-level settings, so that I can customize behavior for my organization.

#### Acceptance Criteria

1. THE System SHALL store tenant settings in CoreTable under TENANT#<tenantId> / SETTINGS
2. THE System SHALL support tenant-level default server configurations
3. THE System SHALL allow Tenant_Admins to configure default auto-shutdown policies for new servers
4. THE System SHALL allow Tenant_Admins to configure default Minecraft server settings
5. WHEN a new server is assigned to a tenant, THE System SHALL apply tenant default configurations
6. THE System SHALL allow Tenant_Admins to update tenant settings
7. THE System SHALL validate that only Tenant_Admins or Global_Admins can modify tenant settings

### Requirement 9: Data Isolation and Security

**User Story:** As a security architect, I want strong data isolation between tenants, so that tenant data remains private and secure.

#### Acceptance Criteria

1. THE System SHALL validate tenant membership before returning any tenant-scoped data
2. THE System SHALL filter GraphQL query results to include only data from the user's authorized tenants
3. THE System SHALL prevent cross-tenant data access through API manipulation
4. WHEN a user queries server metrics, THE System SHALL verify the server belongs to an authorized tenant
5. WHEN a user queries audit logs, THE System SHALL return only logs for servers in authorized tenants
6. THE System SHALL validate tenantId parameters in all GraphQL mutations
7. THE System SHALL log all cross-tenant access attempts for security monitoring
8. THE System SHALL enforce tenant isolation in DynamoDB queries using filter expressions

### Requirement 10: Tenant Administration UI

**User Story:** As a tenant admin, I want a user interface for managing my tenant, so that I can easily administer users, servers, and settings.

#### Acceptance Criteria

1. THE System SHALL provide a tenant management page accessible to Tenant_Admins
2. WHEN a Tenant_Admin views the tenant management page, THE System SHALL display tenant information and settings
3. THE System SHALL provide a user interface for viewing and managing tenant members
4. THE System SHALL provide a user interface for inviting new users to the tenant
5. THE System SHALL provide a user interface for assigning and unassigning servers to the tenant
6. THE System SHALL display tenant member roles and allow role updates
7. THE System SHALL provide a tenant switcher component in the application header
8. WHEN a user switches tenants, THE System SHALL update the server list without page reload
9. THE System SHALL display the current tenant name in the UI header
10. THE System SHALL provide visual indicators for tenant-scoped vs legacy servers

### Requirement 11: Audit Logging for Tenant Operations

**User Story:** As a tenant admin, I want to see audit logs for tenant operations, so that I can track changes and maintain accountability.

#### Acceptance Criteria

1. WHEN a tenant is created, THE System SHALL log the creation event with timestamp and user information
2. WHEN a user is added to or removed from a tenant, THE System SHALL log the membership change
3. WHEN a server is assigned to or unassigned from a tenant, THE System SHALL log the assignment change
4. WHEN tenant settings are updated, THE System SHALL log the configuration change
5. THE System SHALL store audit logs in CoreTable using PK pattern TENANT#<tenantId> / SK pattern LOG#<timestamp>
6. THE System SHALL include actor, action, target, and timestamp in all audit log entries
7. THE System SHALL allow Tenant_Admins to query audit logs for their tenant
8. THE System SHALL support filtering audit logs by date range and action type

### Requirement 12: GraphQL API Extensions

**User Story:** As a frontend developer, I want GraphQL operations for tenant management, so that I can build the tenant administration UI.

#### Acceptance Criteria

1. THE System SHALL provide a createTenant mutation for creating new tenants
2. THE System SHALL provide an updateTenant mutation for updating tenant information
3. THE System SHALL provide a deleteTenant mutation for removing tenants
4. THE System SHALL provide a listTenants query for retrieving user's tenants
5. THE System SHALL provide an addTenantMember mutation for adding users to tenants
6. THE System SHALL provide a removeTenantMember mutation for removing users from tenants
7. THE System SHALL provide an updateTenantMemberRole mutation for changing user roles
8. THE System SHALL provide a listTenantMembers query for retrieving tenant members
9. THE System SHALL provide an assignServerToTenant mutation for server assignment
10. THE System SHALL provide an unassignServerFromTenant mutation for server removal
11. THE System SHALL provide a createTenantInvitation mutation for inviting users
12. THE System SHALL provide an acceptTenantInvitation mutation for accepting invitations
13. THE System SHALL provide a getTenantSettings query for retrieving tenant configuration
14. THE System SHALL provide an updateTenantSettings mutation for updating tenant configuration
