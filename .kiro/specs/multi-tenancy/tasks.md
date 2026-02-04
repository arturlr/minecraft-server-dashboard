# Implementation Plan: Multi-Tenancy

## Overview

This implementation plan breaks down the multi-tenancy feature into discrete, incremental tasks. The approach follows a phased rollout: backend infrastructure first, then GraphQL API extensions, followed by frontend implementation. Each task builds on previous work and includes validation through tests. The implementation maintains backward compatibility with existing single-tenant servers and authorization patterns.

## Tasks

- [ ] 1. Extend DynamoDB data model and access patterns
  - Create helper functions for tenant data operations in ddbHelper layer
  - Implement functions for storing/retrieving tenant metadata (PK: TENANT#<id>, SK: METADATA)
  - Implement functions for storing/retrieving tenant settings (PK: TENANT#<id>, SK: SETTINGS)
  - Implement functions for storing/retrieving user-tenant memberships (PK: USER#<id>, SK: TENANT#<id>)
  - Implement functions for storing/retrieving tenant-user memberships via GSI (SK: TENANT#<id>, PK: USER#<id>)
  - Implement functions for storing/retrieving invitations (PK: INVITATION#<id>, SK: METADATA)
  - Implement functions for storing/retrieving audit logs (PK: TENANT#<id>, SK: LOG#<timestamp>#<id>)
  - Add tenantId field handling to existing server metadata operations
  - _Requirements: 1.3, 2.2, 3.2, 6.2, 8.1, 11.5_

- [ ]* 1.1 Write property test for DynamoDB data storage format
  - **Property 2: Tenant Data Storage Format**
  - **Validates: Requirements 1.3, 2.2, 6.2, 8.1, 11.5**

- [ ] 2. Implement tenant management Lambda function
  - [ ] 2.1 Create tenantManager Lambda directory and handler structure
    - Set up Lambda function with proper IAM permissions for DynamoDB
    - Create handler entry point with routing for different operations
    - _Requirements: 1.1, 1.4, 1.5, 1.6_
  
  - [ ] 2.2 Implement tenant CRUD operations
    - Implement create_tenant: generate UUID, validate name, create metadata record, create initial admin membership
    - Implement update_tenant: validate admin permissions, update tenant name and metadata
    - Implement delete_tenant: validate no servers assigned, validate admin permissions, delete tenant
    - Implement get_tenant: retrieve tenant metadata with member/server counts
    - Implement list_user_tenants: query all tenants where user has membership
    - _Requirements: 1.1, 1.2, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9_
  
  - [ ]* 2.3 Write property tests for tenant operations
    - **Property 1: Tenant Creation Uniqueness**
    - **Validates: Requirements 1.1, 1.2**
    - **Property 3: Tenant Deletion Validation**
    - **Validates: Requirements 1.6, 1.7**
    - **Property 5: Tenant Query Filtering**
    - **Validates: Requirements 1.8, 1.9**
  
  - [ ] 2.4 Implement tenant membership operations
    - Implement add_member: validate admin permissions, validate role, create membership record
    - Implement remove_member: validate admin permissions, check last admin protection, delete membership
    - Implement update_member_role: validate admin permissions, validate role, update membership
    - Implement list_members: query all members of tenant via GSI
    - _Requirements: 2.1, 2.3, 2.4, 2.5, 2.6, 2.8, 2.9, 2.10_
  
  - [ ]* 2.5 Write property tests for membership operations
    - **Property 6: Membership Role Validation**
    - **Validates: Requirements 2.3**
    - **Property 7: Membership Cascading Effects**
    - **Validates: Requirements 2.7**
    - **Property 8: Last Admin Protection**
    - **Validates: Requirements 2.8**
    - **Property 9: Membership Query Completeness**
    - **Validates: Requirements 2.9, 2.10**
  
  - [ ] 2.6 Implement server-tenant assignment operations
    - Implement assign_server: validate admin permissions, validate server exists, update server tenantId, apply tenant defaults
    - Implement unassign_server: validate admin permissions, set server tenantId to null
    - Implement list_tenant_servers: query servers with matching tenantId
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9_
  
  - [ ]* 2.7 Write property tests for server assignment
    - **Property 10: Server Single-Tenant Constraint**
    - **Validates: Requirements 3.4, 3.5**
    - **Property 11: Server Assignment Validation**
    - **Validates: Requirements 3.7**
    - **Property 12: Server Assignment Storage**
    - **Validates: Requirements 3.2, 3.9**
    - **Property 13: Tenant Server Query Completeness**
    - **Validates: Requirements 3.6**
  
  - [ ] 2.8 Implement audit logging for tenant operations
    - Create audit log entries for all tenant operations (create, update, delete, add member, remove member, assign server)
    - Include all required fields: tenantId, timestamp, actionId, actorUserId, actorEmail, action, targetType, targetId, details
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6_
  
  - [ ]* 2.9 Write property test for audit logging
    - **Property 32: Audit Log Completeness**
    - **Validates: Requirements 11.1, 11.2, 11.3, 11.4, 11.6**

- [ ] 3. Checkpoint - Ensure tenant management Lambda tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 4. Implement tenant invitation Lambda function
  - [ ] 4.1 Create tenantInvitationManager Lambda directory and handler structure
    - Set up Lambda function with proper IAM permissions
    - Create handler entry point with routing for invitation operations
    - _Requirements: 6.1, 6.8_
  
  - [ ] 4.2 Implement invitation operations
    - Implement create_invitation: validate admin permissions (or member if allowed), generate UUID, set expiration to 7 days, create invitation record
    - Implement accept_invitation: validate invitation exists, check not expired, check not already accepted, create membership, mark invitation accepted
    - Implement revoke_invitation: validate admin permissions, update invitation status to revoked
    - Implement list_user_invitations: query pending invitations for user's email
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8, 6.9, 6.10_
  
  - [ ]* 4.3 Write property tests for invitation operations
    - **Property 21: Invitation Uniqueness and Completeness**
    - **Validates: Requirements 6.1, 6.3**
    - **Property 22: Invitation Expiration Calculation**
    - **Validates: Requirements 6.4**
    - **Property 23: Invitation Acceptance Effects**
    - **Validates: Requirements 6.5, 6.6**
    - **Property 24: Invitation Expiration Validation**
    - **Validates: Requirements 6.7**
    - **Property 25: Invitation Revocation**
    - **Validates: Requirements 6.8**
    - **Property 26: Deferred Invitation Activation**
    - **Validates: Requirements 6.10**

- [ ] 5. Implement tenant settings Lambda function
  - [ ] 5.1 Create tenantSettingsManager Lambda directory and handler structure
    - Set up Lambda function with proper IAM permissions
    - Create handler entry point for settings operations
    - _Requirements: 8.1, 8.7_
  
  - [ ] 5.2 Implement settings operations
    - Implement get_settings: retrieve tenant settings from CoreTable
    - Implement update_settings: validate admin permissions, update settings record
    - Implement apply_defaults_to_server: apply tenant default configurations to newly assigned server
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7_
  
  - [ ]* 5.3 Write property test for settings operations
    - **Property 30: Tenant Default Configuration Application**
    - **Validates: Requirements 8.5**

- [ ] 6. Extend authHelper layer with tenant-aware authorization
  - [ ] 6.1 Implement tenant membership checking functions
    - Implement check_tenant_membership: query USER#<userId>/TENANT#<tenantId>, return (is_member, role)
    - Implement check_tenant_admin: verify user has admin role in tenant
    - Implement get_user_tenants: query all USER#<userId>/TENANT#* memberships
    - Implement get_tenant_servers: query servers with matching tenantId
    - Implement is_global_admin: check USER#<userId>/ADMIN record
    - _Requirements: 4.1, 4.7_
  
  - [ ] 6.2 Implement tenant-scoped server authorization
    - Implement check_server_access: verify user has membership in server's tenant with required role
    - Handle legacy servers (null tenantId) with fallback to USER#<userId>/SERVER#<serverId> check
    - Support role-based permissions (viewer: read-only, member: control, admin: all)
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.8, 4.9, 7.1, 7.2, 7.7_
  
  - [ ]* 6.3 Write property tests for authorization
    - **Property 14: Comprehensive Tenant-Scoped Authorization**
    - **Validates: Requirements 4.1, 4.2, 4.8, 4.9, 9.4, 9.5**
    - **Property 15: Role-Based Permission Enforcement**
    - **Validates: Requirements 4.3, 4.4**
    - **Property 16: Server Query Tenant Filtering**
    - **Validates: Requirements 4.5**
    - **Property 17: Tenant Isolation Enforcement**
    - **Validates: Requirements 4.6, 9.1, 9.2, 9.3, 9.6, 9.8**
    - **Property 18: Global Admin Bypass**
    - **Validates: Requirements 4.7**
    - **Property 27: Legacy Server Compatibility**
    - **Validates: Requirements 7.1, 7.2, 7.7**

- [ ] 7. Update ec2Discovery Lambda for tenant filtering
  - [ ] 7.1 Modify server discovery to include tenant information
    - Query user's tenant memberships before filtering servers
    - Add tenantId and tenantName fields to server response
    - Filter servers to only those in user's tenants (or legacy servers with direct membership)
    - Handle Global_Admin case (return all servers)
    - _Requirements: 4.5, 7.5, 7.6_
  
  - [ ]* 7.2 Write property test for combined legacy and tenant queries
    - **Property 29: Combined Legacy and Tenant Query**
    - **Validates: Requirements 7.5, 7.6**

- [ ] 8. Update server control Lambdas for tenant authorization
  - [ ] 8.1 Update ec2ActionValidator Lambda
    - Replace Cognito group authorization with tenant membership checks
    - Validate user has appropriate role in server's tenant
    - Include tenant context in audit logs
    - _Requirements: 4.2, 4.3_
  
  - [ ] 8.2 Update ec2ActionWorker Lambda
    - Use tenant-aware authorization for server operations
    - Log tenant context in operation logs
    - _Requirements: 4.2, 4.3_
  
  - [ ]* 8.3 Write property test for admin-only operations
    - **Property 4: Admin-Only Tenant Operations**
    - **Validates: Requirements 1.4, 2.4, 3.3, 8.7**

- [ ] 9. Checkpoint - Ensure backend Lambda tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 10. Extend GraphQL schema with tenant types and operations
  - [ ] 10.1 Add tenant types to schema
    - Add Tenant, TenantMembership, TenantInvitation, TenantSettings, TenantAuditLog types
    - Add TenantRole enum (admin, member, viewer)
    - Add input types for all tenant operations
    - Extend ServerInfo type with tenantId and tenantName fields
    - _Requirements: 12.1-12.14_
  
  - [ ] 10.2 Add tenant queries to schema
    - Add listMyTenants, getTenant, listTenantMembers, getTenantSettings, listMyInvitations, getTenantAuditLogs, listTenantServers queries
    - _Requirements: 12.4, 12.8, 12.13_
  
  - [ ] 10.3 Add tenant mutations to schema
    - Add createTenant, updateTenant, deleteTenant mutations
    - Add addTenantMember, updateTenantMemberRole, removeTenantMember mutations
    - Add assignServerToTenant, unassignServerFromTenant mutations
    - Add createTenantInvitation, acceptTenantInvitation, revokeTenantInvitation mutations
    - Add updateTenantSettings mutation
    - _Requirements: 12.1, 12.2, 12.3, 12.5, 12.6, 12.7, 12.9, 12.10, 12.11, 12.12, 12.14_

- [ ] 11. Create AppSync resolvers for tenant operations
  - [ ] 11.1 Create resolvers for tenant queries
    - Create listMyTenants resolver (calls tenantManager.list_user_tenants)
    - Create getTenant resolver (calls tenantManager.get_tenant)
    - Create listTenantMembers resolver (calls tenantManager.list_members)
    - Create getTenantSettings resolver (calls tenantSettingsManager.get_settings)
    - Create listMyInvitations resolver (calls tenantInvitationManager.list_user_invitations)
    - Create getTenantAuditLogs resolver (calls tenantManager.get_audit_logs)
    - Create listTenantServers resolver (calls tenantManager.list_tenant_servers)
    - _Requirements: 12.4, 12.8, 12.13_
  
  - [ ] 11.2 Create resolvers for tenant mutations
    - Create createTenant resolver (calls tenantManager.create_tenant)
    - Create updateTenant resolver (calls tenantManager.update_tenant)
    - Create deleteTenant resolver (calls tenantManager.delete_tenant)
    - Create addTenantMember resolver (calls tenantManager.add_member)
    - Create updateTenantMemberRole resolver (calls tenantManager.update_member_role)
    - Create removeTenantMember resolver (calls tenantManager.remove_member)
    - Create assignServerToTenant resolver (calls tenantManager.assign_server)
    - Create unassignServerFromTenant resolver (calls tenantManager.unassign_server)
    - Create createTenantInvitation resolver (calls tenantInvitationManager.create_invitation)
    - Create acceptTenantInvitation resolver (calls tenantInvitationManager.accept_invitation)
    - Create revokeTenantInvitation resolver (calls tenantInvitationManager.revoke_invitation)
    - Create updateTenantSettings resolver (calls tenantSettingsManager.update_settings)
    - _Requirements: 12.1, 12.2, 12.3, 12.5, 12.6, 12.7, 12.9, 12.10, 12.11, 12.12, 12.14_
  
  - [ ]* 11.3 Write integration tests for GraphQL API
    - **Property 34: GraphQL API Completeness**
    - **Validates: Requirements 12.1-12.14**

- [ ] 12. Update CloudFormation templates for tenant infrastructure
  - [ ] 12.1 Add tenant Lambda functions to lambdas.yaml
    - Add tenantManager Lambda with DynamoDB permissions
    - Add tenantInvitationManager Lambda with DynamoDB permissions
    - Add tenantSettingsManager Lambda with DynamoDB permissions
    - Configure environment variables (CORE_TABLE_NAME, COGNITO_USER_POOL_ID)
    - _Requirements: 1.1, 6.1, 8.1_
  
  - [ ] 12.2 Update AppSync template with tenant resolvers
    - Add data sources for tenant Lambda functions
    - Add resolvers for all tenant queries and mutations
    - Configure authorization (@aws_cognito_user_pools)
    - _Requirements: 12.1-12.14_

- [ ] 13. Checkpoint - Test backend infrastructure deployment
  - Deploy CloudFormation stack to development environment
  - Test GraphQL operations via AppSync console
  - Verify DynamoDB records are created correctly
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 14. Implement Vuex store extensions for tenant state
  - [ ] 14.1 Add tenant state to Vuex store
    - Add currentTenant, userTenants, tenantMembers, tenantSettings, pendingInvitations to state
    - _Requirements: 5.1, 5.3_
  
  - [ ] 14.2 Implement tenant actions
    - Implement fetchUserTenants: query listMyTenants
    - Implement switchTenant: update currentTenant, trigger server refresh
    - Implement createTenant: call createTenant mutation
    - Implement fetchTenantMembers: query listTenantMembers
    - Implement addTenantMember: call addTenantMember mutation
    - Implement removeTenantMember: call removeTenantMember mutation
    - Implement updateMemberRole: call updateTenantMemberRole mutation
    - Implement assignServerToTenant: call assignServerToTenant mutation
    - Implement fetchPendingInvitations: query listMyInvitations
    - Implement acceptInvitation: call acceptTenantInvitation mutation
    - Implement fetchTenantSettings: query getTenantSettings
    - Implement updateTenantSettings: call updateTenantSettings mutation
    - _Requirements: 5.1, 5.3, 5.4, 5.5_
  
  - [ ] 14.3 Implement tenant getters
    - Implement currentTenant getter
    - Implement userTenants getter
    - Implement isTenantAdmin getter (check if user is admin of specific tenant)
    - Implement tenantServers getter (filter servers by current tenant)
    - _Requirements: 5.3, 5.8_
  
  - [ ]* 14.4 Write unit tests for Vuex store
    - Test state mutations
    - Test action dispatching
    - Test getter computations
    - Test tenant context switching

- [ ] 15. Implement TenantSwitcher component
  - [ ] 15.1 Create TenantSwitcher.vue component
    - Create dropdown component showing user's tenants
    - Display current tenant name
    - Handle tenant selection and dispatch switchTenant action
    - Emit tenant-changed event
    - _Requirements: 5.3, 5.4_
  
  - [ ]* 15.2 Write unit tests for TenantSwitcher
    - Test dropdown rendering
    - Test tenant selection
    - Test event emission
  
  - [ ]* 15.3 Write property test for tenant context switching
    - **Property 20: Tenant Context Switching**
    - **Validates: Requirements 5.3, 5.4, 5.5, 5.8**

- [ ] 16. Implement TenantManagement component
  - [ ] 16.1 Create TenantManagement.vue component
    - Create admin interface for managing tenant
    - Display tenant information and settings
    - Implement member list with roles
    - Implement add/remove member functionality
    - Implement role update functionality
    - Implement server assignment/unassignment
    - Implement invitation creation
    - Display pending invitations
    - Display audit logs
    - _Requirements: 10.1-10.10_
  
  - [ ]* 16.2 Write unit tests for TenantManagement
    - Test member list rendering
    - Test role update flow
    - Test server assignment flow
    - Test invitation creation flow

- [ ] 17. Implement TenantInvitations component
  - [ ] 17.1 Create TenantInvitations.vue component
    - Display list of pending invitations
    - Show invitation details (tenant, role, expiration)
    - Implement accept invitation button
    - Implement decline invitation button
    - _Requirements: 6.5, 6.6_
  
  - [ ]* 17.2 Write unit tests for TenantInvitations
    - Test invitation list rendering
    - Test acceptance flow
    - Test decline flow

- [ ] 18. Update existing components for tenant context
  - [ ] 18.1 Update ServerCard component
    - Add tenant name badge display
    - Add "Legacy" badge for servers without tenant
    - Filter by current tenant context
    - _Requirements: 5.4_
  
  - [ ] 18.2 Update ServerSettings component
    - Validate user has admin/member role for config updates
    - Display tenant context
    - _Requirements: 4.8_
  
  - [ ] 18.3 Update ServerControl component
    - Validate user has admin/member role for control operations
    - Display tenant context
    - _Requirements: 4.2, 4.3_
  
  - [ ]* 18.4 Write integration tests for updated components
    - Test tenant filtering
    - Test role-based permissions
    - Test legacy server handling

- [ ] 19. Add tenant management to application navigation
  - [ ] 19.1 Add TenantSwitcher to application header
    - Integrate TenantSwitcher component into Header.vue
    - Position next to user profile
    - _Requirements: 5.3_
  
  - [ ] 19.2 Add tenant management route
    - Add /tenants route to Vue Router
    - Add navigation link for tenant admins
    - Implement route guard (admin-only)
    - _Requirements: 10.1_

- [ ] 20. Implement GraphQL queries and mutations in frontend
  - [ ] 20.1 Create tenant queries in graphql/queries.js
    - Add listMyTenants query
    - Add getTenant query
    - Add listTenantMembers query
    - Add getTenantSettings query
    - Add listMyInvitations query
    - Add getTenantAuditLogs query
    - Add listTenantServers query
    - _Requirements: 12.4, 12.8, 12.13_
  
  - [ ] 20.2 Create tenant mutations in graphql/mutations.js
    - Add createTenant mutation
    - Add updateTenant mutation
    - Add deleteTenant mutation
    - Add addTenantMember mutation
    - Add updateTenantMemberRole mutation
    - Add removeTenantMember mutation
    - Add assignServerToTenant mutation
    - Add unassignServerFromTenant mutation
    - Add createTenantInvitation mutation
    - Add acceptTenantInvitation mutation
    - Add revokeTenantInvitation mutation
    - Add updateTenantSettings mutation
    - _Requirements: 12.1, 12.2, 12.3, 12.5, 12.6, 12.7, 12.9, 12.10, 12.11, 12.12, 12.14_

- [ ] 21. Checkpoint - Test frontend integration
  - Test tenant creation flow
  - Test membership management flow
  - Test server assignment flow
  - Test invitation flow
  - Test tenant context switching
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 22. Implement error handling and user feedback
  - [ ] 22.1 Add error handling to tenant operations
    - Display user-friendly error messages for authorization errors
    - Display validation error messages
    - Provide retry mechanisms for transient errors
    - _Requirements: Error Handling section_
  
  - [ ] 22.2 Add loading states and progress indicators
    - Show loading spinners during tenant operations
    - Show progress for multi-step operations
    - Disable buttons during operations
  
  - [ ] 22.3 Add success notifications
    - Show success messages for tenant creation
    - Show success messages for membership changes
    - Show success messages for server assignments

- [ ] 23. Implement audit logging and monitoring
  - [ ] 23.1 Add audit log viewer to TenantManagement component
    - Display audit logs with filtering (date range, action type)
    - Show actor, action, target, timestamp
    - Implement pagination for large log sets
    - _Requirements: 11.7, 11.8_
  
  - [ ]* 23.2 Write property test for audit log authorization
    - **Property 33: Audit Log Query Authorization**
    - **Validates: Requirements 11.7, 11.8**
  
  - [ ] 23.3 Add cross-tenant access logging
    - Log all cross-tenant access attempts
    - Include user, tenant, operation in logs
    - _Requirements: 9.7_
  
  - [ ]* 23.4 Write property test for cross-tenant access prevention
    - **Property 31: Cross-Tenant Access Prevention**
    - **Validates: Requirements 9.3, 9.7**

- [ ] 24. Create migration script for legacy servers
  - [ ] 24.1 Create migration Lambda function
    - Query all servers without tenantId
    - For each server, check if owner wants to assign to tenant
    - Optionally create default tenant for each owner
    - Assign servers to appropriate tenants
    - Preserve all server configurations
    - _Requirements: 7.3, 7.4_
  
  - [ ]* 24.2 Write property test for legacy server migration
    - **Property 28: Legacy Server Migration**
    - **Validates: Requirements 7.3, 7.4**

- [ ] 25. Implement tenant context initialization on login
  - [ ] 25.1 Update authentication flow
    - Load user's tenants on login
    - Set first tenant as default context
    - Store tenant context in session
    - _Requirements: 5.1, 5.2_
  
  - [ ]* 25.2 Write property test for tenant context initialization
    - **Property 19: Tenant Context Initialization**
    - **Validates: Requirements 5.1, 5.2**

- [ ] 26. Final checkpoint - End-to-end testing
  - Test complete tenant creation and management flow
  - Test complete invitation flow
  - Test complete server assignment flow
  - Test tenant context switching with server filtering
  - Test legacy server compatibility
  - Test authorization for all roles (admin, member, viewer)
  - Test global admin bypass
  - Verify backward compatibility with existing servers
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 27. Documentation and deployment preparation
  - [ ] 27.1 Update API documentation
    - Document all new GraphQL queries and mutations
    - Document tenant data model
    - Document authorization rules
  
  - [ ] 27.2 Create user guide
    - Document tenant creation process
    - Document member management
    - Document server assignment
    - Document invitation system
    - Document tenant context switching
  
  - [ ] 27.3 Create deployment guide
    - Document migration strategy
    - Document rollback procedures
    - Document monitoring and alerting setup
    - Document performance optimization recommendations

## Notes

- Tasks marked with `*` are optional test tasks that can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation throughout implementation
- Property tests validate universal correctness properties with minimum 100 iterations
- Unit tests validate specific examples and edge cases
- The implementation maintains backward compatibility with existing single-tenant servers
- Global admins bypass all tenant restrictions for administrative purposes
- Tenant isolation is enforced at multiple layers (authorization, queries, UI filtering)
