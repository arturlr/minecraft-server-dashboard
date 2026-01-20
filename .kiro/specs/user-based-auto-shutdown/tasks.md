# Implementation Plan

## Note on Current Status

The user-based auto-shutdown feature is **already fully implemented** in the codebase. These tasks focus on:
- Adding comprehensive test coverage
- Documenting the implementation
- Optional enhancements

## Core Implementation Tasks

- [x] 1. Verify and document existing implementation
  - Review ServerSettings.vue Connections method UI
  - Review ec2ActionWorker Lambda configuration handling
  - Review ec2Helper.py alarm management functions
  - Review port_count.sh script installation in BootstrapSSMDoc
  - Document any gaps or issues found
  - _Requirements: All_

- [x] 2. Add unit tests for frontend validation
- [x] 2.1 Test threshold input validation
  - Write tests for valid numeric inputs (0, 1, 10, 100)
  - Write tests for invalid inputs (negative, non-numeric, empty)
  - Verify validation error messages display correctly
  - _Requirements: 1.2_

- [x] 2.2 Test evaluation period validation
  - Write tests for valid numeric inputs (1, 5, 10, 60)
  - Write tests for invalid inputs (0, negative, non-numeric, empty)
  - Verify validation error messages display correctly
  - _Requirements: 1.3_

- [x] 2.3 Test warning display logic
  - Test warning appears when threshold > 0 and period < 5
  - Test warning does not appear for valid configurations
  - Verify warning message content
  - _Requirements: 4.1_

- [x] 3. Add unit tests for backend configuration handling
- [x] 3.1 Test handle_update_server_config function
  - Test successful configuration with valid Connections parameters
  - Test error handling for missing arguments
  - Test error handling for missing threshold/period
  - Verify EC2 tags are updated correctly
  - _Requirements: 1.4, 1.5_

- [x] 3.2 Test alarm creation logic
  - Test update_alarm creates alarm with correct parameters
  - Verify alarm uses UserCount metric
  - Verify alarm uses Maximum statistic
  - Verify alarm uses MinecraftDashboard namespace
  - Verify alarm action is EC2 stop automation
  - _Requirements: 3.1, 3.4, 3.5_

- [ ]* 3.3 Test alarm removal logic
  - Test remove_alarm handles existing alarms
  - Test remove_alarm handles non-existent alarms gracefully
  - _Requirements: 7.1_

- [x] 4. Add unit tests for EC2 helper functions
- [x] 4.1 Test get_instance_attributes_from_tags
  - Test retrieval of shutdownMethod tag
  - Test conversion of alarmThreshold string to float
  - Test conversion of alarmEvaluationPeriod string to int
  - Test handling of missing tags (default values)
  - Test handling of invalid numeric values
  - _Requirements: 1.4_

- [x] 4.2 Test set_instance_attributes_to_tags
  - Test tag creation with valid configuration
  - Test tag deletion and recreation
  - Test handling of empty/null values
  - _Requirements: 1.4_

- [x] 4.3 Write property test for configuration round-trip
  - **Property 1: Configuration Persistence**
  - **Validates: Requirements 1.4**
  - Generate random valid threshold (0-100) and period (1-60)
  - Save configuration via set_instance_attributes_to_tags
  - Retrieve configuration via get_instance_attributes_from_tags
  - Assert retrieved values match original (with type conversions)
  - _Requirements: 1.4_

- [ ] 5. Add integration tests for metric collection
- [ ] 5.1 Test port_count.sh script execution
  - Verify script exists at /usr/local/port_count.sh
  - Verify script is executable
  - Verify script contains correct instance ID and region
  - Test script execution produces valid output
  - _Requirements: 2.1, 2.2, 2.3, 2.4_

- [x] 5.2 Test cron job configuration
  - Verify cron job is installed during bootstrap
  - Verify cron job runs every minute
  - Verify cron job does not create duplicates
  - _Requirements: 2.5, 6.5_

- [ ]* 5.3 Write property test for metric accuracy
  - **Property 2: Metric Collection Accuracy**
  - **Validates: Requirements 2.1, 2.2**
  - Simulate random number of connections (0-20) on port 25565
  - Execute metric collection script
  - Verify published metric value equals connection count
  - Verify metric has correct namespace and dimensions
  - _Requirements: 2.1, 2.2, 2.3, 2.4_

- [ ] 6. Add integration tests for CloudWatch alarm behavior
- [ ] 6.1 Test alarm creation via API
  - Create alarm with test configuration
  - Verify alarm exists in CloudWatch
  - Verify alarm parameters match configuration
  - Clean up test alarm
  - _Requirements: 3.1, 3.4, 3.5_

- [ ]* 6.2 Test alarm state transitions
  - Create alarm with threshold 0, period 5 minutes
  - Publish metrics above threshold
  - Verify alarm stays in OK state
  - Publish metrics at/below threshold for 5 minutes
  - Verify alarm transitions to ALARM state
  - _Requirements: 3.2_

- [ ]* 6.3 Write property test for alarm threshold enforcement
  - **Property 3: Alarm Threshold Enforcement**
  - **Validates: Requirements 3.2**
  - Generate random threshold T and period E
  - Simulate metric values above and below T
  - Verify alarm state matches expected based on evaluation logic
  - _Requirements: 3.2_

- [ ] 7. Add integration tests for method switching
- [ ] 7.1 Test switching from Schedule to Connections
  - Configure instance with Schedule method
  - Verify EventBridge rules exist
  - Switch to Connections method
  - Verify EventBridge rules removed
  - Verify CloudWatch alarm created
  - _Requirements: 7.1, 7.2_

- [ ]* 7.2 Test switching from Connections to Schedule
  - Configure instance with Connections method
  - Verify CloudWatch alarm exists
  - Switch to Schedule method
  - Verify CloudWatch alarm removed
  - Verify EventBridge rules created
  - _Requirements: 7.1, 7.2_

- [ ]* 7.3 Write property test for shutdown method exclusivity
  - **Property 4: Shutdown Method Exclusivity**
  - **Validates: Requirements 7.1, 7.2**
  - For any instance with Connections method
  - Verify no EventBridge rules exist
  - Verify CloudWatch alarm exists
  - _Requirements: 7.1, 7.2_

- [ ] 8. Add edge case tests
- [ ] 8.1 Test zero threshold configuration
  - Configure threshold = 0, period = 10
  - Publish UserCount = 0 for 10 minutes
  - Verify alarm triggers
  - Publish UserCount = 1
  - Verify alarm clears
  - _Requirements: 5.5, 8.1_

- [ ]* 8.2 Test large evaluation period
  - Configure period = 60 minutes
  - Publish metrics below threshold for 59 minutes
  - Verify alarm does not trigger
  - Publish metric below threshold at 60 minutes
  - Verify alarm triggers
  - _Requirements: 3.2_

- [ ]* 8.3 Test rapid connection changes
  - Configure threshold = 2, period = 5
  - Simulate connections fluctuating between 1 and 3
  - Verify alarm only triggers after sustained period below threshold
  - _Requirements: 3.2, 4.1_

- [ ]* 8.4 Test instance restart scenario
  - Stop EC2 instance
  - Start EC2 instance
  - Verify cron job resumes automatically
  - Verify metric collection continues
  - _Requirements: 8.4, 8.5_

- [ ]* 8.5 Write property test for zero user detection
  - **Property 5: Zero User Detection**
  - **Validates: Requirements 8.1**
  - For any instance with threshold = 0
  - When no TCP connections exist on port 25565
  - Verify metric collection script publishes UserCount = 0
  - _Requirements: 8.1_

- [ ] 9. Add error handling tests
- [ ] 9.1 Test missing configuration arguments
  - Call handle_update_server_config with None arguments
  - Verify function returns False
  - Verify error is logged
  - _Requirements: 1.4_

- [ ]* 9.2 Test CloudWatch API errors
  - Mock CloudWatch API to return errors
  - Verify error handling and logging
  - Verify function returns False
  - _Requirements: 3.1_

- [ ]* 9.3 Test network connectivity loss during metric publishing
  - Simulate network failure during metric publish
  - Verify AWS CLI retry behavior
  - Verify metric published when connectivity restored
  - _Requirements: 8.3_

- [ ] 10. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Documentation Tasks

- [ ] 11. Create user documentation
  - Write guide for configuring user-based auto-shutdown
  - Document recommended threshold and period values
  - Add troubleshooting section for common issues
  - Include cost savings examples
  - _Requirements: All_

- [ ] 12. Create developer documentation
  - Document metric collection architecture
  - Document CloudWatch alarm configuration
  - Document tag-based configuration storage
  - Add sequence diagrams for key flows
  - _Requirements: All_

## Optional Enhancement Tasks

- [ ] 13. Add real-time metric display to UI (Optional)
  - Fetch current UserCount metric from CloudWatch
  - Display current player count in ServerSettings
  - Add refresh button to update metric
  - Show last update timestamp
  - _Requirements: 5.1_

- [ ] 14. Add historical connection graph (Optional)
  - Query CloudWatch for UserCount metric history
  - Display line graph of player connections over time
  - Add time range selector (1h, 6h, 24h, 7d)
  - Highlight alarm threshold on graph
  - _Requirements: 5.1_

- [ ] 15. Add cost savings calculator (Optional)
  - Calculate hours saved per month based on configuration
  - Estimate cost savings based on instance type
  - Display estimated monthly savings in UI
  - Show ROI of auto-shutdown feature
  - _Requirements: 5.4_

- [ ] 16. Add enhanced metric collection (Optional)
  - Track unique player UUIDs from server logs
  - Distinguish authenticated vs unauthenticated connections
  - Add metric for player join/leave events
  - Publish additional metrics to CloudWatch
  - _Requirements: 2.1_

- [ ] 17. Add composite alarm support (Optional)
  - Support combining CPU AND Connections in single alarm
  - Add UI for configuring composite conditions
  - Update backend to create composite alarms
  - Test composite alarm behavior
  - _Requirements: 3.1_

- [ ] 18. Add pre-shutdown notifications (Optional)
  - Configure SNS topic for shutdown warnings
  - Send notification 5 minutes before shutdown
  - Add in-game warning message to players
  - Allow grace period for players to finish
  - _Requirements: 3.3_

- [ ] 19. Final Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
