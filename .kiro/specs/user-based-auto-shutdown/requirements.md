# Requirements Document

## Introduction

The User-Based Auto-Shutdown feature enables Minecraft server administrators to automatically shutdown EC2 instances when the number of connected players falls below a specified threshold for a sustained period. This feature helps optimize AWS costs by ensuring servers don't run idle when no players are connected, while preventing premature shutdowns during brief player disconnections.

## Glossary

- **System**: The Minecraft Server Dashboard application
- **User**: A Minecraft server administrator using the dashboard
- **Player**: A person connected to the Minecraft server
- **Connection**: An established TCP connection on port 25565 (Minecraft default port)
- **UserCount Metric**: A CloudWatch custom metric tracking the number of active player connections
- **Threshold**: The maximum number of connected players that triggers shutdown evaluation
- **Evaluation Period**: The duration in minutes that the connection count must remain at or below the threshold before shutdown
- **CloudWatch Alarm**: An AWS CloudWatch alarm that monitors the UserCount metric and triggers EC2 stop action
- **Metric Collection Script**: A bash script (`port_count.sh`) that runs via cron to count active connections
- **EC2 Instance**: The AWS virtual machine hosting the Minecraft server

## Requirements

### Requirement 1

**User Story:** As a server administrator, I want to configure user-based auto-shutdown settings, so that my server automatically stops when player activity is low.

#### Acceptance Criteria

1. WHEN a user selects the "Connections" shutdown method in the settings UI THEN the System SHALL display threshold and evaluation period input fields
2. WHEN a user enters a threshold value THEN the System SHALL accept only non-negative integer values representing player count
3. WHEN a user enters an evaluation period THEN the System SHALL accept only positive integer values representing minutes
4. WHEN a user saves the configuration THEN the System SHALL persist the threshold and evaluation period to EC2 instance tags
5. WHEN a user saves the configuration THEN the System SHALL create or update a CloudWatch alarm with the specified parameters

### Requirement 2

**User Story:** As a server administrator, I want the system to accurately count connected players, so that shutdown decisions are based on correct data.

#### Acceptance Criteria

1. WHEN the metric collection script executes THEN the System SHALL count all established TCP connections on port 25565
2. WHEN the metric collection script completes counting THEN the System SHALL publish the count to CloudWatch as a custom metric
3. WHEN publishing the metric THEN the System SHALL include the instance ID as a dimension
4. WHEN publishing the metric THEN the System SHALL use the namespace "MinecraftDashboard" and metric name "UserCount"
5. WHEN the metric collection script runs THEN the System SHALL execute every minute via cron

### Requirement 3

**User Story:** As a server administrator, I want CloudWatch alarms to monitor player connections, so that the server shuts down automatically when conditions are met.

#### Acceptance Criteria

1. WHEN a CloudWatch alarm is created for user-based shutdown THEN the System SHALL configure it to monitor the UserCount metric
2. WHEN the UserCount metric is at or below the threshold for the evaluation period THEN the CloudWatch alarm SHALL transition to ALARM state
3. WHEN the CloudWatch alarm enters ALARM state THEN the System SHALL trigger an EC2 stop action
4. WHEN configuring the alarm THEN the System SHALL use the Maximum statistic for the UserCount metric
5. WHEN configuring the alarm THEN the System SHALL set the comparison operator to LessThanOrEqualToThreshold

### Requirement 4

**User Story:** As a server administrator, I want validation warnings for my configuration, so that I can avoid settings that might cause unintended shutdowns.

#### Acceptance Criteria

1. WHEN the threshold is greater than 0 and evaluation period is less than 5 minutes THEN the System SHALL display a warning about brief disconnections
2. WHEN the user hovers over or focuses on configuration fields THEN the System SHALL display helpful hints about appropriate values
3. WHEN the configuration is invalid THEN the System SHALL prevent form submission
4. WHEN the configuration is valid THEN the System SHALL enable the save button
5. WHEN displaying warnings THEN the System SHALL use clear, actionable language

### Requirement 5

**User Story:** As a server administrator, I want to see a summary of my shutdown configuration, so that I understand exactly when the server will stop.

#### Acceptance Criteria

1. WHEN metric-based configuration is active THEN the System SHALL display a summary card showing the shutdown condition
2. WHEN displaying the shutdown condition THEN the System SHALL include the threshold value and evaluation period
3. WHEN displaying the shutdown condition THEN the System SHALL use clear language describing the trigger
4. WHEN the configuration includes helpful tips THEN the System SHALL display context-specific recommendations
5. WHEN the shutdown method is Connections THEN the System SHALL suggest setting threshold to 0 for empty server detection

### Requirement 6

**User Story:** As a system operator, I want the metric collection script to be installed automatically, so that user counting works without manual setup.

#### Acceptance Criteria

1. WHEN an EC2 instance is bootstrapped THEN the System SHALL create the port_count.sh script in /usr/local/
2. WHEN creating the script THEN the System SHALL include the instance ID and region from instance metadata
3. WHEN creating the script THEN the System SHALL make it executable
4. WHEN the script is created THEN the System SHALL add a cron job to execute it every minute
5. WHEN the cron job already exists THEN the System SHALL not create duplicate entries

### Requirement 7

**User Story:** As a server administrator, I want to switch between different shutdown methods, so that I can choose the best approach for my usage pattern.

#### Acceptance Criteria

1. WHEN a user changes from Connections to another shutdown method THEN the System SHALL remove the existing CloudWatch alarm
2. WHEN a user changes to Connections from another method THEN the System SHALL create a new CloudWatch alarm with Connections configuration
3. WHEN switching shutdown methods THEN the System SHALL preserve the threshold and evaluation period values in the UI
4. WHEN switching shutdown methods THEN the System SHALL update the EC2 instance tags with the new shutdown method
5. WHEN switching shutdown methods THEN the System SHALL provide visual feedback of the active method

### Requirement 8

**User Story:** As a server administrator, I want the system to handle edge cases gracefully, so that the feature works reliably in all scenarios.

#### Acceptance Criteria

1. WHEN no players are connected THEN the metric collection script SHALL report a UserCount of 0
2. WHEN the CloudWatch agent is not running THEN the metric collection script SHALL still execute without errors
3. WHEN network connectivity is temporarily lost THEN the metric collection script SHALL retry publishing metrics
4. WHEN the EC2 instance is stopped THEN the cron job SHALL not execute
5. WHEN the EC2 instance is restarted THEN the cron job SHALL resume automatic execution
