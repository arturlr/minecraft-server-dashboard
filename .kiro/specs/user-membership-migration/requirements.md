# Requirements Document

## Introduction

This feature migrates user membership management from AWS Cognito user groups to DynamoDB storage, enabling role-based access control for Minecraft servers. Currently, each EC2 instance has an associated Cognito user group that controls which users can perform actions against that server. This system will be replaced with DynamoDB-based membership storage where user membership data (email, sub, and role) is stored directly in DynamoDB and used for all access control decisions. This change eliminates the need for Cognito group management and provides more flexibility for role-based permissions.

## Glossary

- **User_Membership**: A DynamoDB record that associates a user with a server and defines their role
- **Membership_Role**: The access level a user has for a specific server (admin, moderator, viewer)
- **Cognito_Sub**: The unique identifier for a user from AWS Cognito (sub claim from JWT token)
- **Server_Admin**: A user with admin role who can manage server settings and user memberships
- **Server_Moderator**: A user with moderator role who can control server operations but cannot manage users
- **Server_Viewer**: A user with viewer role who can only view server status and metrics
- **Auth_Helper**: The Lambda layer that handles authentication and authorization logic
- **DDB_Helper**: The Lambda layer that handles DynamoDB operations

## Requirements

### Requirement 1

**User Story:** As a system architect, I want to store user membership data in DynamoDB instead of Cognito groups, so that I have more control over user roles and reduce dependency on Cognito group management.

#### Acceptance Criteria

1. THE System SHALL create a new DynamoDB table to store user membership records
2. WHEN a user membership is created THEN the system SHALL store the user's email, Cognito sub, server instance ID, and role
3. WHEN querying user memberships THEN the system SHALL use DynamoDB queries instead of Cognito group membership checks
4. WHEN a user is removed from a server THEN the system SHALL delete the corresponding DynamoDB record
5. THE System SHALL maintain referential integrity between users and servers through proper key design

### Requirement 2

**User Story:** As a developer, I want to implement role-based access control with three distinct roles, so that users have appropriate permissions based on their responsibilities.

#### Acceptance Criteria

1. THE System SHALL support exactly three membership roles: admin, moderator, and viewer
2. WHEN a user has admin role THEN they SHALL have full access to server management, user management, and server operations
3. WHEN a user has moderator role THEN they SHALL have access to server operations but NOT user management
4. WHEN a user has viewer role THEN they SHALL have read-only access to server status and metrics
5. WHEN checking permissions THEN the system SHALL validate the user's role for the specific server
6. THE System SHALL prevent users from performing actions above their role level

### Requirement 3

**User Story:** As a backend developer, I want to migrate existing Cognito group memberships to DynamoDB, so that current users maintain their access without disruption and Cognito groups can be eliminated.

#### Acceptance Criteria

1. WHEN the migration runs THEN the system SHALL read all existing Cognito group memberships for each server
2. WHEN processing each group membership THEN the system SHALL extract the user's email and sub from Cognito user details
3. WHEN creating DynamoDB records THEN the system SHALL map existing group members to admin role by default
4. WHEN the migration completes THEN the system SHALL verify that all users have been migrated successfully
5. WHEN the migration is verified THEN the system SHALL provide a report of migrated users per server
6. THE Migration SHALL be idempotent and safe to run multiple times
7. AFTER migration completion THEN Cognito groups can be safely deleted as they will no longer be used

### Requirement 4

**User Story:** As a Lambda function developer, I want to update authorization logic to use DynamoDB instead of Cognito groups, so that access control works with the new data model.

#### Acceptance Criteria

1. WHEN a Lambda function needs to check user permissions THEN it SHALL query the DynamoDB membership table
2. WHEN validating server access THEN the system SHALL verify the user has a membership record for that server
3. WHEN checking role permissions THEN the system SHALL compare the required permission level with the user's role
4. WHEN authorization fails THEN the system SHALL return appropriate error messages indicating insufficient permissions
5. THE Authorization logic SHALL be centralized in the Auth Helper layer for consistency

### Requirement 5

**User Story:** As a GraphQL API user, I want the existing user management operations to work with the new DynamoDB backend, so that the frontend interface continues to function.

#### Acceptance Criteria

1. WHEN calling getServerUsers query THEN the system SHALL return users from DynamoDB membership table
2. WHEN calling addUserToServer mutation THEN the system SHALL create a new DynamoDB membership record
3. WHEN adding a user THEN the system SHALL default to viewer role unless otherwise specified
4. WHEN the user management operations execute THEN they SHALL include role information in responses
5. THE GraphQL schema SHALL be updated to include role fields in user-related types

### Requirement 6

**User Story:** As a system administrator, I want to manage user roles through GraphQL mutations, so that I can promote or demote users as needed.

#### Acceptance Criteria

1. WHEN an admin calls updateUserRole mutation THEN the system SHALL update the user's role in DynamoDB
2. WHEN updating a user role THEN the system SHALL validate that the requesting user has admin permissions
3. WHEN a role update succeeds THEN the system SHALL return the updated membership information
4. WHEN attempting to update a non-existent membership THEN the system SHALL return an appropriate error
5. THE System SHALL prevent users from modifying their own admin role to prevent lockout

### Requirement 7

**User Story:** As a developer, I want comprehensive error handling for the new membership system, so that users receive clear feedback when operations fail.

#### Acceptance Criteria

1. WHEN a DynamoDB operation fails THEN the system SHALL return descriptive error messages
2. WHEN a user lacks sufficient permissions THEN the system SHALL return "Insufficient permissions" with role requirements
3. WHEN attempting to access a non-existent server THEN the system SHALL return "Server not found" error
4. WHEN attempting to modify a non-existent membership THEN the system SHALL return "User membership not found" error
5. THE Error messages SHALL be consistent across all Lambda functions and GraphQL operations

### Requirement 8

**User Story:** As a system maintainer, I want logging and monitoring for membership operations, so that I can track access control changes and troubleshoot issues.

#### Acceptance Criteria

1. WHEN membership records are created or modified THEN the system SHALL log the operation with user and server details
2. WHEN authorization checks occur THEN the system SHALL log access attempts with outcomes
3. WHEN errors occur in membership operations THEN the system SHALL log detailed error information
4. WHEN the migration runs THEN the system SHALL log progress and completion status
5. THE Logging SHALL include sufficient detail for security auditing and troubleshooting