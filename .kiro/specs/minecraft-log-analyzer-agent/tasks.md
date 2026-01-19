# Implementation Plan: Minecraft Log Analyzer Agent

## Overview

This implementation plan breaks down the Minecraft Log Analyzer Agent feature into discrete, incremental coding tasks. The approach follows a bottom-up strategy: building core infrastructure first (log collection and parsing), then agent tools, then the agent itself, and finally the frontend integration. Each task builds on previous work, with checkpoints to ensure stability before proceeding.

## Tasks

- [ ] 1. Set up project infrastructure and dependencies
  - Create Lambda function directories: `lambdas/logAgentQuery/` and `lambdas/logCollector/`
  - Create Lambda layer directory: `layers/logAnalyzer/`
  - Add Strands Agents SDK to layer requirements: `strands-agents`, `strands-agents-tools`
  - Add Hypothesis to layer requirements for property testing
  - Update CloudFormation templates to include new Lambda functions and layer
  - Create DynamoDB table definition for `LogAnalyzerSessions` with TTL
  - _Requirements: 8.1, 8.4_

- [ ] 2. Implement log collection and parsing
  - [ ] 2.1 Create Log Collector Lambda function
    - Implement `fetch_cloudwatch_logs()` to retrieve logs from CloudWatch Logs
    - Implement `fetch_ec2_logs()` to retrieve logs from EC2 instances via SSM
    - Implement time-range filtering logic
    - Implement pagination for logs exceeding 10MB
    - Add error handling with descriptive messages
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_
  
  - [ ]* 2.2 Write property test for log retrieval
    - **Property 1: Log Retrieval Correctness**
    - **Property 2: Time-Range Filtering**
    - **Property 3: Pagination for Large Logs**
    - **Property 4: Error Message Descriptiveness**
    - **Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5**
  
  - [ ] 2.3 Implement log parsing functions
    - Create `parse_log_line()` to extract timestamp, level, thread, message
    - Support multiple formats: vanilla, Spigot, Paper, Forge
    - Implement `categorize_event()` for player/server/error/performance events
    - Extract player names and event types from messages
    - Extract performance metrics (TPS, memory) from log lines
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_
  
  - [ ]* 2.4 Write property tests for log parsing
    - **Property 5: Log Parsing Completeness**
    - **Property 6: Event Categorization Accuracy**
    - **Property 7: Performance Metric Extraction**
    - **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6**
  
  - [ ]* 2.5 Write unit tests for log parsing edge cases
    - Test empty logs, malformed lines, missing components
    - Test each log format (vanilla, Spigot, Paper, Forge)
    - Test special characters and encoding issues
    - _Requirements: 2.1, 2.6_

- [ ] 3. Implement agent tools for log analysis
  - [ ] 3.1 Create search_logs tool
    - Implement keyword filtering (case-insensitive)
    - Implement log level filtering
    - Implement time range filtering
    - Implement result limiting
    - Add Strands `@tool` decorator with comprehensive docstring
    - _Requirements: 5.1_
  
  - [ ] 3.2 Create get_player_activity tool
    - Filter logs by player name
    - Filter by event types (join, leave, chat, death, achievement)
    - Generate summary statistics (joins, leaves, chat count, etc.)
    - Add `@tool` decorator with docstring
    - _Requirements: 5.2_
  
  - [ ]* 3.3 Write property test for get_player_activity
    - **Property 12: Player Activity Tool Correctness**
    - **Validates: Requirements 5.2**
  
  - [ ] 3.4 Create get_error_summary tool
    - Aggregate errors by type
    - Count error occurrences
    - Track first and last occurrence timestamps
    - Include sample error messages
    - Add `@tool` decorator with docstring
    - _Requirements: 5.3_
  
  - [ ]* 3.5 Write property test for get_error_summary
    - **Property 13: Error Aggregation Accuracy**
    - **Validates: Requirements 5.3**
  
  - [ ] 3.6 Create get_performance_metrics tool
    - Extract TPS values from logs
    - Extract memory usage values
    - Calculate average, min, max statistics
    - Identify lag events
    - Add `@tool` decorator with docstring
    - _Requirements: 5.4_
  
  - [ ]* 3.7 Write property test for get_performance_metrics
    - **Property 14: Performance Metric Calculation**
    - **Validates: Requirements 5.4**
  
  - [ ] 3.8 Create get_recent_events tool
    - Retrieve N most recent log entries
    - Filter by event category (all, player, server, error)
    - Sort by timestamp (newest first)
    - Add `@tool` decorator with docstring
    - _Requirements: 5.5_
  
  - [ ]* 3.9 Write property test for get_recent_events
    - **Property 15: Recent Events Ordering**
    - **Validates: Requirements 5.5**
  
  - [ ] 3.10 Create count_events tool
    - Count occurrences of specific event types
    - Support time range filtering
    - Return count with time range metadata
    - Add `@tool` decorator with docstring
    - _Requirements: 5.6_
  
  - [ ]* 3.11 Write property test for count_events
    - **Property 16: Event Counting Accuracy**
    - **Validates: Requirements 5.6**
  
  - [ ] 3.12 Create get_security_events tool (admin only)
    - Filter for authentication and permission events
    - Include ban/kick events
    - Add role-based access check
    - Add `@tool` decorator with docstring
    - _Requirements: 5.7_
  
  - [ ]* 3.13 Write unit tests for tool registration
    - **Property 10: Tool Registration Completeness**
    - **Property 11: Admin Tool Access Control**
    - **Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7**

- [ ] 4. Checkpoint - Verify tools work independently
  - Run all tool tests to ensure they pass
  - Manually test each tool with sample log data
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 5. Implement Insight Engine
  - [ ] 5.1 Create peak activity detection
    - Analyze player activity logs across time periods
    - Identify periods with highest event counts
    - Return peak times with activity counts
    - _Requirements: 6.2_
  
  - [ ]* 5.2 Write property test for peak activity detection
    - **Property 17: Peak Activity Detection**
    - **Validates: Requirements 6.2**
  
  - [ ] 5.3 Create daily summary generator
    - Aggregate player count, error count, performance metrics
    - Calculate daily statistics
    - Format summary report
    - _Requirements: 6.5_
  
  - [ ]* 5.4 Write property test for daily summary
    - **Property 18: Daily Summary Generation**
    - **Validates: Requirements 6.5**

- [ ] 6. Implement session management
  - [ ] 6.1 Create Session Manager module
    - Implement `get_or_create_session()` to retrieve or create DynamoDB session
    - Implement `save_conversation_turn()` to append messages to history
    - Implement conversation context limiting (last 10 turns)
    - Set TTL for 30-minute automatic cleanup
    - _Requirements: 8.4, 8.5_
  
  - [ ]* 6.2 Write property tests for session management
    - **Property 24: Session History Storage**
    - **Property 25: Conversation Context Limit**
    - **Validates: Requirements 8.4, 8.5**
  
  - [ ]* 6.3 Write unit tests for session edge cases
    - Test session creation, retrieval, expiration
    - Test DynamoDB write failures
    - Test TTL calculation
    - _Requirements: 8.4_

- [ ] 7. Implement authentication and authorization
  - [ ] 7.1 Create authorization helper functions
    - Implement `verify_cognito_token()` to validate authentication
    - Implement `check_server_access()` to verify user has access to server
    - Implement `is_admin()` to check admin privileges
    - Add authorization checks to all query handlers
    - _Requirements: 7.1, 7.2, 7.3, 7.4_
  
  - [ ]* 7.2 Write property tests for authorization
    - **Property 19: Authentication Verification**
    - **Property 20: Server Access Authorization**
    - **Property 21: Admin Unrestricted Access**
    - **Property 22: Security Query Authorization**
    - **Validates: Requirements 7.1, 7.2, 7.3, 7.4**
  
  - [ ] 7.3 Implement audit logging
    - Log all queries with user ID, server ID, query text, timestamp
    - Write to CloudWatch Logs in structured format
    - _Requirements: 7.5_
  
  - [ ]* 7.4 Write property test for audit logging
    - **Property 23: Query Audit Logging**
    - **Validates: Requirements 7.5**

- [ ] 8. Implement Query Handler Lambda with Strands Agent
  - [ ] 8.1 Create agent initialization function
    - Initialize Bedrock model with Claude 4 Sonnet
    - Configure temperature (0.3) and max_tokens (4096)
    - Register all tools based on user role (include get_security_events for admins)
    - Set system prompt for log analysis expertise
    - _Requirements: 8.3_
  
  - [ ] 8.2 Implement query handler
    - Verify authentication and authorization
    - Retrieve or create session
    - Initialize agent with tools
    - Process user query through agent
    - Save conversation turn to session
    - Log query for audit
    - Return response with citations and tool calls
    - _Requirements: 4.7, 7.1, 7.5_
  
  - [ ]* 8.3 Write property test for response citations
    - **Property 9: Response Citation Inclusion**
    - **Validates: Requirements 4.7**
  
  - [ ] 8.4 Implement error handling
    - Handle Bedrock API failures with retry logic (exponential backoff, 3 retries)
    - Handle token limit exceeded with conversation summarization
    - Handle tool execution failures gracefully
    - Log all errors to CloudWatch with context
    - Return user-friendly error messages
    - _Requirements: 10.1, 10.3, 10.4, 10.5_
  
  - [ ]* 8.5 Write property tests for error handling
    - **Property 27: Error Handling with User Feedback**
    - **Property 28: Retry with Exponential Backoff**
    - **Property 29: Token Limit Handling**
    - **Property 30: Error Logging to CloudWatch**
    - **Validates: Requirements 10.1, 10.3, 10.4, 10.5**
  
  - [ ]* 8.6 Write unit tests for query handler
    - Test successful query processing
    - Test authentication failures
    - Test authorization failures
    - Test session creation and retrieval
    - _Requirements: 7.1, 7.2, 8.4_

- [ ] 9. Implement performance optimizations
  - [ ] 9.1 Add log caching
    - Implement 5-minute cache for log segments
    - Use in-memory cache with TTL
    - Cache key based on server ID and time range
    - _Requirements: 11.4_
  
  - [ ]* 9.2 Write property test for caching
    - **Property 33: Log Caching Behavior**
    - **Validates: Requirements 11.4**
  
  - [ ] 9.3 Implement rate limiting
    - Track queries per user per minute
    - Reject queries exceeding 30/minute threshold
    - Return rate limit error with retry-after time
    - _Requirements: 11.5_
  
  - [ ]* 9.4 Write property test for rate limiting
    - **Property 34: Rate Limiting Enforcement**
    - **Validates: Requirements 11.5**
  
  - [ ]* 9.5 Write performance tests
    - **Property 31: Response Time Performance**
    - **Property 32: Concurrent Session Support**
    - **Validates: Requirements 11.1, 11.2, 11.3**

- [ ] 10. Checkpoint - Backend integration testing
  - Test end-to-end query flow from AppSync to agent to tools
  - Verify session management works correctly
  - Verify authentication and authorization
  - Test error handling and recovery
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 11. Implement cost tracking and monitoring
  - [ ] 11.1 Add token usage tracking
    - Record input/output tokens for each query
    - Store usage in DynamoDB with user ID and server ID
    - Log estimated costs to CloudWatch
    - _Requirements: 12.1, 12.2_
  
  - [ ]* 11.2 Write property test for usage tracking
    - **Property 35: Token Usage Tracking**
    - **Validates: Requirements 12.1, 12.2**
  
  - [ ] 11.3 Implement cost alerting
    - Monitor cumulative monthly costs
    - Send CloudWatch alarm when threshold exceeded
    - Alert administrators via SNS
    - _Requirements: 12.3_
  
  - [ ]* 11.4 Write property test for cost alerting
    - **Property 36: Cost Threshold Alerting**
    - **Validates: Requirements 12.3**
  
  - [ ] 11.5 Add feature disable control
    - Check configuration for feature enabled/disabled per server
    - Check global feature flag
    - Reject queries when feature is disabled
    - _Requirements: 12.5_
  
  - [ ]* 11.6 Write property test for feature control
    - **Property 37: Feature Disable Control**
    - **Validates: Requirements 12.5**

- [ ] 12. Update GraphQL schema and resolvers
  - [ ] 12.1 Add GraphQL types and operations
    - Add `LogAgentResponse`, `ToolCall`, `LogCitation`, `TokenUsage` types
    - Add `queryLogAgent` query
    - Add `onLogAgentResponse` subscription
    - Update schema.graphql file
    - _Requirements: 3.1, 3.2, 3.3_
  
  - [ ] 12.2 Create AppSync resolvers
    - Create Lambda resolver for `queryLogAgent`
    - Create resolver for subscription
    - Configure authorization with Cognito
    - _Requirements: 7.1, 8.2_
  
  - [ ] 12.3 Update CloudFormation templates
    - Add GraphQL schema updates to `cfn/templates/appsync.yaml`
    - Add Lambda function resources to `cfn/templates/lambdas.yaml`
    - Add DynamoDB table to CloudFormation
    - Add IAM roles and permissions
    - _Requirements: 8.1, 8.4_

- [ ] 13. Implement frontend Chat Interface component
  - [ ] 13.1 Create LogAnalyzerChat.vue component
    - Create component structure with props (serverId, serverName)
    - Implement data model (messages, sessionId, isLoading, inputText)
    - Add Vuetify UI elements (chat container, message list, input field)
    - Style with Material Design theme
    - _Requirements: 9.1, 9.2, 9.6_
  
  - [ ] 13.2 Implement GraphQL integration
    - Create GraphQL query for `queryLogAgent`
    - Create GraphQL subscription for `onLogAgentResponse`
    - Implement `sendQuery()` method to submit queries
    - Implement subscription handler for real-time responses
    - _Requirements: 3.1, 3.2_
  
  - [ ] 13.3 Implement message display
    - Display user messages in conversation history
    - Display agent responses with markdown rendering
    - Show loading indicator during processing
    - Optionally show tool calls used by agent
    - Format timestamps in readable format
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.6_
  
  - [ ]* 13.4 Write property test for conversation history
    - **Property 8: Conversation History Persistence**
    - **Validates: Requirements 3.1, 3.5**
  
  - [ ] 13.5 Implement session management
    - Initialize new session on component mount
    - Clear session when switching servers
    - Maintain conversation history for current session
    - _Requirements: 3.5, 9.5_
  
  - [ ]* 13.6 Write property test for session clearing
    - **Property 26: Session History Clearing**
    - **Validates: Requirements 9.5**
  
  - [ ] 13.7 Add suggested queries
    - Display suggested queries on initialization
    - Examples: "What errors occurred today?", "Show recent player activity", "What's the server performance?"
    - Make suggestions clickable to auto-fill input
    - _Requirements: 9.3_
  
  - [ ]* 13.8 Write unit tests for Chat Interface
    - Test component rendering
    - Test message display
    - Test user input handling
    - Test GraphQL query/subscription integration
    - _Requirements: 3.1, 3.2, 3.3_

- [ ] 14. Integrate Chat Interface into Server Dashboard
  - [ ] 14.1 Add Log Analyzer tab to server view
    - Add "Log Analyzer" tab to server dashboard navigation
    - Conditionally show tab only for servers user has access to
    - Pass serverId and serverName as props to LogAnalyzerChat
    - _Requirements: 9.1_
  
  - [ ] 14.2 Update router configuration
    - Add route for log analyzer view
    - Configure route guards for authentication
    - _Requirements: 7.1_
  
  - [ ]* 14.3 Write integration tests
    - Test navigation to log analyzer
    - Test tab visibility based on user access
    - Test component initialization with server context
    - _Requirements: 9.1, 9.2_

- [ ] 15. Final checkpoint - End-to-end testing
  - Test complete user workflow: login → select server → open log analyzer → ask questions
  - Test with different user roles (regular user vs admin)
  - Test error scenarios (network failures, invalid queries, rate limiting)
  - Test performance with concurrent users
  - Verify all property tests pass (100+ iterations each)
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 16. Documentation and deployment
  - [ ] 16.1 Update documentation
    - Add feature documentation to `docs/` directory
    - Document agent capabilities and example queries
    - Document cost estimates and optimization tips
    - Update README with new feature
    - _Requirements: 12.4_
  
  - [ ] 16.2 Deploy infrastructure
    - Build SAM application with new Lambda functions and layers
    - Deploy CloudFormation stack updates
    - Verify DynamoDB table creation
    - Verify AppSync schema updates
    - _Requirements: 8.1, 8.4_
  
  - [ ] 16.3 Deploy frontend
    - Build Vue.js application with new component
    - Deploy to S3 and invalidate CloudFront cache
    - Verify component loads correctly in production
    - _Requirements: 9.1_
  
  - [ ]* 16.4 Set up monitoring
    - Create CloudWatch dashboard for agent metrics
    - Configure alarms for error rate, response time, cost
    - Set up SNS notifications for administrators
    - _Requirements: 12.3_

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation before proceeding
- Property tests validate universal correctness properties with 100+ iterations
- Unit tests validate specific examples and edge cases
- Tools are built and tested independently before agent integration
- Backend is fully tested before frontend development begins
- All components integrate with existing AWS infrastructure (Cognito, AppSync, DynamoDB)
