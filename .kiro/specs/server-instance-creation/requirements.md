# Requirements Document

## Introduction

This feature enables users to create new Minecraft server instances directly from the dashboard interface. Users will be able to specify server configuration including name, instance specifications, and shutdown policies through an intuitive dialog interface, leveraging the existing EC2 instance creation capabilities.

## Glossary

- **Dashboard**: The Vue.js frontend application for managing Minecraft servers
- **Instance Creation Dialog**: A modal dialog component for configuring new server instances
- **T3 Instance Types**: AWS EC2 instance family optimized for burstable performance workloads
- **Shutdown Mechanism**: Automated policies for stopping instances (CPU-based, connection-based, or scheduled)
- **Server Creation Service**: Backend Lambda function responsible for creating new EC2 instances
- **AppSync API**: GraphQL API layer for frontend-backend communication

## Requirements

### Requirement 1

**User Story:** As a server administrator, I want to create new Minecraft server instances from the dashboard, so that I can quickly provision new servers without using the AWS console.

#### Acceptance Criteria

1. WHEN a user clicks the "Add Server" button in the toolbar, THE Dashboard SHALL display the instance creation dialog
2. WHEN the instance creation dialog opens, THE Dashboard SHALL present input fields for server name and instance specifications
3. WHEN a user submits valid server configuration, THE Server Creation Service SHALL create a new EC2 instance with the specified parameters
4. WHEN instance creation is successful, THE Dashboard SHALL close the dialog and refresh the server list
5. WHEN instance creation fails, THE Dashboard SHALL display an error message with details

### Requirement 2

**User Story:** As a server administrator, I want to select appropriate instance specifications, so that I can choose the right performance level for my server needs.

#### Acceptance Criteria

1. WHEN the instance creation dialog displays, THE Dashboard SHALL provide a dropdown with T3 instance type options
2. WHEN a user selects an instance type, THE Dashboard SHALL display the corresponding specifications (CPU, memory, network performance)
3. WHEN instance specifications are displayed, THE Dashboard SHALL show estimated hourly costs for the selected instance type
4. THE Dashboard SHALL support T3 instance types: t3.micro, t3.small, t3.medium, t3.large, t3.xlarge, t3.2xlarge
5. THE Dashboard SHALL validate that the selected instance type is available in the current AWS region

### Requirement 3

**User Story:** As a server administrator, I want to configure shutdown mechanisms during instance creation, so that I can set up cost optimization policies from the start.

#### Acceptance Criteria

1. WHEN the instance creation dialog displays, THE Dashboard SHALL provide shutdown mechanism configuration options
2. WHEN a user selects CPU-based shutdown, THE Dashboard SHALL allow configuration of CPU threshold and evaluation period
3. WHEN a user selects connection-based shutdown, THE Dashboard SHALL allow configuration of player count threshold and evaluation period
4. WHEN a user selects scheduled shutdown, THE Dashboard SHALL allow configuration of start and stop schedules using cron expressions
5. THE Dashboard SHALL validate shutdown configuration parameters before submission

### Requirement 4

**User Story:** As a server administrator, I want to provide a meaningful server name, so that I can easily identify and manage multiple servers.

#### Acceptance Criteria

1. WHEN the instance creation dialog displays, THE Dashboard SHALL provide a required text input for server name
2. WHEN a user enters a server name, THE Dashboard SHALL validate that the name is between 3 and 50 characters
3. WHEN a user enters a server name, THE Dashboard SHALL validate that the name contains only alphanumeric characters, hyphens, and underscores
4. WHEN a server name is invalid, THE Dashboard SHALL display validation error messages
5. THE Dashboard SHALL prevent submission until a valid server name is provided

### Requirement 5

**User Story:** As a system, I want to create EC2 instances with proper configuration, so that new servers are ready for Minecraft hosting.

#### Acceptance Criteria

1. WHEN creating a new instance, THE Server Creation Service SHALL use the latest Ubuntu 22.04 AMI
2. WHEN creating a new instance, THE Server Creation Service SHALL configure two EBS volumes (16GB root volume for OS, 50GB data volume for game)
3. WHEN creating a new instance, THE Server Creation Service SHALL apply appropriate tags including Name and App values
4. WHEN creating a new instance, THE Server Creation Service SHALL assign the correct IAM instance profile
5. WHEN creating a new instance, THE Server Creation Service SHALL place the instance in the default subnet and security group

### Requirement 6

**User Story:** As a system, I want to integrate instance creation with existing infrastructure, so that new servers work seamlessly with the current dashboard functionality.

#### Acceptance Criteria

1. WHEN a new instance is created, THE Server Creation Service SHALL configure CloudWatch alarms based on the selected shutdown mechanism
2. WHEN a new instance is created, THE Server Creation Service SHALL create EventBridge rules if scheduled shutdown is configured
3. WHEN a new instance is created, THE Server Creation Service SHALL store server configuration in DynamoDB
4. WHEN a new instance is created, THE Server Creation Service SHALL send status updates via AppSync subscriptions
5. WHEN instance creation completes, THE Dashboard SHALL automatically refresh to show the new server