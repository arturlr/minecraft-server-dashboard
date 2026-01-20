# Implementation Plan

- [x] 1. Update GraphQL schema and backend infrastructure
  - Add CreateServerInput type and createServer mutation to GraphQL schema
  - Update AppSync resolvers to handle new mutation
  - _Requirements: 1.3, 5.1-5.5, 6.1-6.4_

- [ ]* 1.1 Write property test for GraphQL input validation
  - **Property 9: Shutdown parameter validation**
  - **Validates: Requirements 3.5**

- [x] 2. Extend ec2ActionValidator Lambda for server creation
  - Add handle_create_server() function with admin authorization check
  - Implement input validation for server name, instance type, and shutdown configuration
  - Add SQS message queuing for createServer action
  - _Requirements: 1.3, 4.2-4.5, 3.5_

- [ ]* 2.1 Write property test for server name validation
  - **Property 5: Server name length validation**
  - **Validates: Requirements 4.2**

- [ ]* 2.2 Write property test for character validation
  - **Property 6: Server name character validation**
  - **Validates: Requirements 4.3**

- [ ]* 2.3 Write property test for admin authorization
  - **Property 2: Admin-only access**
  - **Validates: Requirements 1.1**

- [x] 3. Enhance ec2ActionWorker Lambda for instance creation
  - Add process_create_server() function to handle SQS messages
  - Integrate with existing ec2Helper.create_ec2_instance() method
  - Add CloudWatch alarm and EventBridge rule creation logic
  - Add DynamoDB configuration storage
  - Add AppSync status update integration
  - _Requirements: 5.1-5.5, 6.1-6.4_

- [ ]* 3.1 Write property test for EC2 instance creation
  - **Property 10: Ubuntu AMI usage**
  - **Validates: Requirements 5.1**

- [ ]* 3.2 Write property test for EBS volume configuration
  - **Property 11: EBS volume configuration**
  - **Validates: Requirements 5.2**

- [ ]* 3.3 Write property test for instance tagging
  - **Property 12: Instance tagging**
  - **Validates: Requirements 5.3**

- [ ]* 3.4 Write property test for CloudWatch alarm creation
  - **Property 15: CloudWatch alarm creation**
  - **Validates: Requirements 6.1**

- [x] 4. Update ec2Helper.py for configurable instance types
  - Modify create_ec2_instance() method to accept instance_type parameter
  - Ensure proper error handling and logging
  - Maintain existing two-volume EBS configuration (16GB root for OS, 50GB data for game)
  - _Requirements: 2.1-2.4, 5.1-5.5_

- [ ]* 4.1 Write property test for IAM profile assignment
  - **Property 13: IAM profile assignment**
  - **Validates: Requirements 5.4**

- [ ]* 4.2 Write property test for network placement
  - **Property 14: Network placement**
  - **Validates: Requirements 5.5**

- [x] 5. Create CreateServerDialog Vue component
  - Build modal dialog with form fields for server name, instance type, and shutdown configuration
  - Implement client-side validation for all input fields
  - Add instance type dropdown with specifications and cost display
  - Add conditional field display based on shutdown method selection
  - Integrate with GraphQL createServer mutation
  - _Requirements: 1.1-1.5, 2.1-2.4, 3.1-3.5, 4.1-4.5_

- [ ]* 5.1 Write property test for dialog visibility control
  - **Property 1: Dialog visibility control**
  - **Validates: Requirements 1.1**

- [ ]* 5.2 Write property test for instance type specifications
  - **Property 2: Instance type specifications display**
  - **Validates: Requirements 2.2**

- [ ]* 5.3 Write property test for cost display
  - **Property 3: Instance type cost display**
  - **Validates: Requirements 2.3**

- [ ]* 5.4 Write property test for conditional field display
  - **Property 4: Conditional shutdown field display**
  - **Validates: Requirements 3.2, 3.3, 3.4**

- [ ]* 5.5 Write property test for error message display
  - **Property 7: Invalid name error display**
  - **Validates: Requirements 4.4**

- [ ]* 5.6 Write property test for form submission prevention
  - **Property 8: Form submission prevention**
  - **Validates: Requirements 4.5**

- [x] 6. Update AppToolbar component
  - Add "Add Server" button visible only to admin users
  - Integrate with CreateServerDialog component
  - Handle dialog open/close state management
  - _Requirements: 1.1_

- [x] 7. Add GraphQL mutations and queries to frontend
  - Add createServer mutation to mutations.js
  - Update existing queries if needed for server list refresh
  - Add error handling for creation failures
  - _Requirements: 1.3-1.5, 6.5_

- [ ]* 7.1 Write property test for UI error handling
  - **Property 20: UI error handling**
  - **Validates: Requirements 1.5**

- [ ]* 7.2 Write property test for UI refresh after creation
  - **Property 19: UI refresh after creation**
  - **Validates: Requirements 1.4, 6.5**

- [x] 8. Integrate server creation with existing dashboard functionality
  - Ensure new servers appear in server list after creation
  - Add real-time status updates via AppSync subscriptions
  - Test integration with existing server management features
  - _Requirements: 6.4, 6.5_

- [ ]* 8.1 Write property test for status update propagation
  - **Property 18: Status update propagation**
  - **Validates: Requirements 6.4**

- [ ]* 8.2 Write property test for EventBridge rule creation
  - **Property 16: EventBridge rule creation**
  - **Validates: Requirements 6.2**

- [ ]* 8.3 Write property test for configuration persistence
  - **Property 17: Configuration persistence**
  - **Validates: Requirements 6.3**

- [ ] 9. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 10. Add comprehensive error handling and user feedback
  - Implement proper error messages for all failure scenarios
  - Add loading states and progress indicators
  - Add success notifications and automatic dialog closure
  - Test error scenarios (AWS API failures, validation errors, network issues)
  - _Requirements: 1.4, 1.5_

- [ ]* 10.1 Write unit tests for error handling scenarios
  - Test AWS API failure handling
  - Test validation error display
  - Test network error recovery
  - _Requirements: 1.5_

- [ ] 11. Final integration testing and validation
  - Test complete end-to-end server creation flow
  - Verify CloudWatch alarms are created correctly
  - Verify EventBridge rules work for scheduled shutdown
  - Verify DynamoDB configuration storage
  - Verify server appears in dashboard after creation
  - _Requirements: All requirements_

- [ ] 12. Final Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.