# Implementation Plan: User Membership Migration

## Overview

This implementation plan migrates user membership management from AWS Cognito user groups to DynamoDB storage with role-based access control. The plan follows a phased approach to ensure zero downtime and provides rollback capabilities. All Lambda functions are implemented in Python to match the existing codebase.

## Tasks

- [x] 1. Create DynamoDB UserMembership table and infrastructure
  - Add UserMembership table definition to `cfn/templates/dynamodb.yaml`
  - Include Global Secondary Index for server-based queries
  - Add IAM permissions for Lambda functions to access new table
  - Update environment variables for table name
  - _Requirements: 1.1, 1.5_

- [x] 2. Update GraphQL schema with membership types and operations
  - Add UserMembership type and MembershipRole enum to `appsync/schema.graphql`
  - Update ServerUsers type to include role field
  - Add updateUserRole and removeUserFromServer mutations
  - Add UserMembershipInput and UpdateUserRoleInput input types
  - _Requirements: 5.5, 6.1_

- [ ]* 2.1 Write property test for role validation
  - **Property 5: Role validation**
  - **Validates: Requirements 2.1**

- [x] 3. Create DynamoDB helper methods for membership operations
  - Add membership CRUD operations to `layers/ddbHelper/ddbHelper.py`
  - Implement `create_membership`, `get_membership`, `update_membership`, `delete_membership`
  - Implement `list_server_members` with optional role filtering
  - Add proper error handling and logging for all operations
  - _Requirements: 1.2, 1.3, 1.4_

- [x] 3.1 Write property test for membership data integrity
  - **Property 1: Membership data integrity**
  - **Validates: Requirements 1.2**

- [x] 3.2 Write property test for membership removal consistency
  - **Property 3: Membership removal consistency**
  - **Validates: Requirements 1.4**

- [x] 4. Update Auth Helper with role-based authorization methods
  - Add role-based permission checking methods to `layers/authHelper/authHelper.py`
  - Implement `get_user_membership`, `check_user_permission`, `list_server_members`
  - Define permission levels and operation requirements
  - Replace Cognito group methods with DynamoDB membership methods
  - _Requirements: 2.2, 2.3, 2.4, 2.5, 2.6, 4.1, 4.2, 4.3_

- [ ]* 4.1 Write property test for role-permission comparison
  - **Property 19: Role-permission comparison**
  - **Validates: Requirements 4.3**

- [ ]* 4.2 Write property test for admin permission completeness
  - **Property 6: Admin permission completeness**
  - **Validates: Requirements 2.2**

- [ ]* 4.3 Write property test for moderator permission restrictions
  - **Property 7: Moderator permission restrictions**
  - **Validates: Requirements 2.3**

- [ ]* 4.4 Write property test for viewer permission limitations
  - **Property 8: Viewer permission limitations**
  - **Validates: Requirements 2.4**

- [x] 5. Update Util Helper with new authorization logic
  - Update `check_user_authorization` method in `layers/utilHelper/utilHelper.py`
  - Replace Cognito group checks with DynamoDB membership queries
  - Update method signature to support role-based permissions
  - Ensure consistent error messaging across authorization failures
  - _Requirements: 4.4, 7.2, 7.5_

- [ ]* 5.1 Write property test for authorization failure messaging
  - **Property 20: Authorization failure messaging**
  - **Validates: Requirements 4.4**

- [ ] 6. Create migration Lambda function
  - Create new Lambda function `lambdas/migrateCognitoGroupsToDynamoDB/index.py`
  - Implement Cognito group enumeration and user extraction logic
  - Create DynamoDB membership records with admin role for existing users
  - Add migration verification and reporting functionality
  - Ensure migration is idempotent and can be run multiple times safely
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

- [ ]* 6.1 Write property test for migration data extraction
  - **Property 12: Migration data extraction**
  - **Validates: Requirements 3.2**

- [ ]* 6.2 Write property test for migration default role assignment
  - **Property 13: Migration default role assignment**
  - **Validates: Requirements 3.3**

- [ ]* 6.3 Write property test for migration idempotency
  - **Property 16: Migration idempotency**
  - **Validates: Requirements 3.6**

- [x] 7. Update listServers Lambda function
  - Modify `lambdas/listServers/index.py` to use DynamoDB membership queries
  - Replace Cognito group filtering with membership-based server filtering
  - Update authorization logic to use role-based permissions
  - Ensure admin users can see all servers, others see only their assigned servers
  - _Requirements: 4.1, 4.2_

- [ ]* 7.1 Write property test for DynamoDB authorization implementation
  - **Property 17: DynamoDB authorization implementation**
  - **Validates: Requirements 4.1**

- [ ]* 7.2 Write property test for membership-based access validation
  - **Property 18: Membership-based access validation**
  - **Validates: Requirements 4.2**

- [x] 8. Update serverAction Lambda function
  - Modify `lambdas/serverAction/index.py` to use role-based authorization
  - Update `check_authorization` function to query DynamoDB membership
  - Implement role-based permission checking for different operations
  - Update `addUserToServer` to create DynamoDB membership records with default viewer role
  - Add new `updateUserRole` and `removeUserFromServer` handlers
  - _Requirements: 5.2, 5.3, 6.1, 6.2, 6.3, 6.4, 6.5_

- [ ]* 8.1 Write property test for membership record creation
  - **Property 22: Membership record creation**
  - **Validates: Requirements 5.2**

- [ ]* 8.2 Write property test for default role assignment
  - **Property 23: Default role assignment**
  - **Validates: Requirements 5.3**

- [ ]* 8.3 Write property test for role update functionality
  - **Property 25: Role update functionality**
  - **Validates: Requirements 6.1**

- [ ]* 8.4 Write property test for self-admin-role protection
  - **Property 29: Self-admin-role protection**
  - **Validates: Requirements 6.5**

- [x] 9. Update getServerUsers GraphQL resolver
  - Modify the resolver to query DynamoDB membership table instead of Cognito groups
  - Include role information in the response for each user
  - Ensure proper authorization checking for the requesting user
  - Handle empty membership lists gracefully
  - _Requirements: 5.1, 5.4_

- [ ]* 9.1 Write property test for DynamoDB-based user queries
  - **Property 21: DynamoDB-based user queries**
  - **Validates: Requirements 5.1**

- [ ]* 9.2 Write property test for role information in responses
  - **Property 24: Role information in responses**
  - **Validates: Requirements 5.4**

- [x] 10. Add comprehensive error handling and logging
  - Update all Lambda functions with consistent error messages
  - Add detailed logging for membership operations and authorization checks
  - Implement proper error responses for DynamoDB failures
  - Ensure error message consistency across all functions
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 8.1, 8.2, 8.3_

- [ ]* 10.1 Write property test for DynamoDB error messaging
  - **Property 30: DynamoDB error messaging**
  - **Validates: Requirements 7.1**

- [ ]* 10.2 Write property test for error message consistency
  - **Property 34: Error message consistency**
  - **Validates: Requirements 7.5**

- [ ]* 10.3 Write property test for membership operation logging
  - **Property 35: Membership operation logging**
  - **Validates: Requirements 8.1**

- [ ] 11. Update CloudFormation templates
  - Add UserMembership table to `cfn/templates/dynamodb.yaml`
  - Add migration Lambda function to `cfn/templates/lambdas.yaml`
  - Update IAM permissions for all Lambda functions to access new table
  - Add environment variables for UserMembership table name
  - _Requirements: 1.1_

- [x] 12. Create AppSync resolvers for new mutations
  - Create resolver for `updateUserRole` mutation
  - Create resolver for `removeUserFromServer` mutation
  - Ensure proper authorization and error handling in resolvers
  - Update existing resolvers to include role information
  - _Requirements: 6.1, 6.2, 6.3, 6.4_

- [ ] 13. Checkpoint - Deploy infrastructure and run migration
  - Deploy CloudFormation updates to create new table and migration function
  - Run migration function to populate membership data from Cognito groups
  - Verify migration results and generate migration report
  - Ensure all existing users have been migrated with admin role
  - _Requirements: 3.4, 3.5_

- [ ]* 13.1 Write property test for migration completeness verification
  - **Property 14: Migration completeness verification**
  - **Validates: Requirements 3.4**

- [ ]* 13.2 Write property test for migration reporting accuracy
  - **Property 15: Migration reporting accuracy**
  - **Validates: Requirements 3.5**

- [ ] 14. Deploy updated Lambda functions with dual-mode support
  - Deploy Lambda functions that check both Cognito groups and DynamoDB membership
  - Implement fallback logic to ensure backward compatibility during transition
  - Add feature flags to control which authorization method is used
  - Test all functionality with both authorization methods
  - _Requirements: 4.1, 4.2, 4.3_

- [ ] 15. Comprehensive testing and validation
  - Test all GraphQL operations with role-based permissions
  - Verify admin, moderator, and viewer access patterns work correctly
  - Test error scenarios and ensure proper error messages
  - Validate that authorization checks use DynamoDB instead of Cognito
  - Test migration idempotency by running migration multiple times
  - _Requirements: 2.2, 2.3, 2.4, 2.5, 2.6, 4.4, 7.1, 7.2, 7.3, 7.4_

- [ ]* 15.1 Write property test for server-specific permission validation
  - **Property 9: Server-specific permission validation**
  - **Validates: Requirements 2.5**

- [ ]* 15.2 Write property test for role-based operation enforcement
  - **Property 10: Role-based operation enforcement**
  - **Validates: Requirements 2.6**

- [ ] 16. Switch to DynamoDB-only mode and cleanup
  - Remove Cognito group dependencies from all Lambda functions
  - Update feature flags to use DynamoDB-only authorization
  - Remove fallback logic and dual-mode support code
  - Optionally clean up Cognito groups (after verification period)
  - _Requirements: 3.7_

- [ ] 17. Final checkpoint - Ensure all tests pass and system is fully migrated
  - Run complete test suite to ensure all functionality works
  - Verify that all authorization uses DynamoDB membership
  - Confirm that role-based permissions work as expected
  - Validate that migration is complete and Cognito groups are no longer needed
  - Document the new role-based permission system for users

## Notes

- Tasks marked with `*` are optional property-based tests that can be skipped for faster MVP
- Each task references specific requirements for traceability
- The implementation follows a phased approach to ensure zero downtime
- Migration includes verification and rollback capabilities
- All Lambda functions maintain backward compatibility during transition
- Property tests validate universal correctness properties across all inputs
- Unit tests validate specific examples and edge cases
- Both types of tests are valuable and complement each other