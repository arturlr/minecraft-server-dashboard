# Requirements Document

## Introduction

This feature transforms the Minecraft Server Dashboard frontend from a single-server card-based view to a minimalist table-based view that displays all servers in a data table. Server configuration and statistics will be accessible through dialog modals opened from table row actions, providing a more scalable and efficient interface for managing multiple Minecraft servers.

## Glossary

- **Dashboard**: The main Vue.js frontend application for managing Minecraft servers
- **Server Table**: A data table component displaying all available Minecraft servers with key information
- **Configuration Dialog**: A modal dialog for viewing and editing server configuration settings
- **Statistics Dialog**: A modal dialog for viewing real-time server performance metrics and charts
- **Table Row Actions**: Interactive buttons/icons in each table row for accessing server operations
- **HomeView**: The main view component that currently displays a single server card
- **Vuetify Data Table**: The v-data-table component used for displaying tabular data

## Requirements

### Requirement 1: Server List Table Display

**User Story:** As a server administrator, I want to see all my Minecraft servers in a table format, so that I can quickly scan and compare multiple servers at once.

#### Acceptance Criteria

1. WHEN the HomeView loads, THE Dashboard SHALL display a Vuetify data table containing all available servers
2. THE Server Table SHALL display columns for server name, instance ID, state, public IP address, CPU (vCPUs), RAM (memory size), disk size, and IAM status
3. THE Server Table SHALL display a status chip indicating whether each server is running, stopped, or in a transitional state
4. THE Server Table SHALL support sorting by any column
5. THE Server Table SHALL support searching/filtering servers by name or instance ID

### Requirement 2: Table Row Actions

**User Story:** As a server administrator, I want action buttons in each table row, so that I can quickly access server operations without navigating away.

#### Acceptance Criteria

1. THE Server Table SHALL include an actions column with icon buttons for each server row
2. WHEN a user clicks the configuration icon, THE Dashboard SHALL open the Configuration Dialog for that server
3. WHEN a user clicks the statistics icon, THE Dashboard SHALL open the Statistics Dialog for that server
4. WHEN a user clicks the power icon, THE Dashboard SHALL open the power control dialog for that server
5. THE Server Table SHALL display the copy IP address button in each row for quick access

### Requirement 3: Configuration Dialog

**User Story:** As a server administrator, I want to view and edit server configuration in a dialog, so that I can manage settings without leaving the table view.

#### Acceptance Criteria

1. WHEN a user opens the Configuration Dialog, THE Dashboard SHALL display the ServerSettings component content in a modal dialog
2. THE Configuration Dialog SHALL be scrollable for long configuration forms
3. WHEN a user saves configuration changes, THE Dashboard SHALL update the server configuration and close the dialog
4. WHEN a user cancels or closes the Configuration Dialog, THE Dashboard SHALL discard unsaved changes
5. THE Configuration Dialog SHALL display a loading indicator while fetching or saving configuration data

### Requirement 4: Statistics Dialog

**User Story:** As a server administrator, I want to view server performance metrics in a dialog, so that I can monitor server health without cluttering the main table view.

#### Acceptance Criteria

1. WHEN a user opens the Statistics Dialog, THE Dashboard SHALL display the ServerCharts component with real-time metrics
2. THE Statistics Dialog SHALL show CPU, memory, network, and active users charts
3. THE Statistics Dialog SHALL subscribe to GraphQL updates for real-time metric streaming
4. WHEN a user closes the Statistics Dialog, THE Dashboard SHALL unsubscribe from metric updates to conserve resources
5. THE Statistics Dialog SHALL display server specifications including vCPUs, memory size, and disk size

### Requirement 5: Power Control Integration

**User Story:** As a server administrator, I want to start, stop, or restart servers from the table view, so that I can manage server power states efficiently.

#### Acceptance Criteria

1. WHEN a user clicks the power icon for a stopped server, THE Dashboard SHALL display a dialog with a Start button
2. WHEN a user clicks the power icon for a running server, THE Dashboard SHALL display a dialog with Stop and Restart buttons
3. WHEN a user executes a power action, THE Dashboard SHALL send the appropriate GraphQL mutation
4. THE Dashboard SHALL display a snackbar notification with the action result
5. THE Server Table SHALL update the server state in real-time via GraphQL subscriptions

### Requirement 6: IAM Status Indicator

**User Story:** As a server administrator, I want to see IAM compliance status in the table, so that I can quickly identify servers with permission issues.

#### Acceptance Criteria

1. THE Server Table SHALL display an IAM status indicator for each server
2. WHEN a server has IAM issues, THE Dashboard SHALL display a warning icon with error color
3. WHEN a user clicks on an IAM warning, THE Dashboard SHALL display the fix IAM role dialog
4. THE Dashboard SHALL provide a "Fix Now" button to automatically correct IAM permissions
5. THE Server Table SHALL update the IAM status after successful remediation

### Requirement 7: Responsive Design

**User Story:** As a server administrator, I want the table view to work on different screen sizes, so that I can manage servers from any device.

#### Acceptance Criteria

1. THE Server Table SHALL be responsive and adapt to mobile, tablet, and desktop screen sizes
2. WHEN viewed on mobile devices, THE Server Table SHALL hide less critical columns
3. THE Configuration Dialog SHALL be full-screen on mobile devices
4. THE Statistics Dialog SHALL be full-screen on mobile devices
5. THE Server Table SHALL maintain usability with touch interactions on mobile devices

### Requirement 8: Server Selection State Management

**User Story:** As a server administrator, I want the system to remember which server I'm viewing, so that dialog operations work correctly.

#### Acceptance Criteria

1. WHEN a user opens a Configuration Dialog, THE Dashboard SHALL set the selected server ID in the store
2. WHEN a user opens a Statistics Dialog, THE Dashboard SHALL set the selected server ID in the store
3. THE Dashboard SHALL maintain the selected server context for all dialog operations
4. WHEN a user closes a dialog, THE Dashboard SHALL clear or maintain the selection based on user workflow
5. THE Dashboard SHALL ensure GraphQL subscriptions target the correct server instance

### Requirement 9: Performance Optimization

**User Story:** As a server administrator, I want the table view to load quickly, so that I can access server information without delays.

#### Acceptance Criteria

1. THE Server Table SHALL load and display server data within 2 seconds
2. THE Dashboard SHALL only subscribe to metrics for servers with open Statistics Dialogs
3. THE Dashboard SHALL unsubscribe from metrics when Statistics Dialogs are closed
4. THE Server Table SHALL use virtual scrolling for lists exceeding 50 servers
5. THE Dashboard SHALL cache server configuration data to reduce redundant API calls

### Requirement 10: User Experience Enhancements

**User Story:** As a server administrator, I want visual feedback for all actions, so that I understand what the system is doing.

#### Acceptance Criteria

1. THE Dashboard SHALL display loading indicators during data fetching operations
2. THE Dashboard SHALL show success snackbar notifications after successful operations
3. THE Dashboard SHALL show error snackbar notifications when operations fail
4. THE Server Table SHALL highlight rows on hover to improve readability
5. THE Dashboard SHALL display empty state messaging when no servers are available
