# Design Document

## Overview

This design transforms the Minecraft Server Dashboard from a single-server card view to a scalable table-based interface. The new design displays all servers in a Vuetify data table with inline actions, while server configuration and statistics are accessed through modal dialogs. This approach improves scalability, reduces visual clutter, and provides a more efficient workflow for managing multiple Minecraft servers.

## Architecture

### Component Hierarchy

```
HomeView.vue (Refactored)
├── AppToolbar.vue (New)
├── IamAlert.vue (New)
├── ServerTable.vue (New)
│   ├── v-data-table (Vuetify)
│   ├── ServerStatusChip.vue (New)
│   └── ServerActionsMenu.vue (New)
├── ServerConfigDialog.vue (New)
│   └── ServerSettings.vue (Existing - Reused)
├── ServerStatsDialog.vue (New)
│   ├── ServerCharts.vue (Existing - Reused)
│   └── ServerSpecs.vue (Existing - Adapted)
└── PowerControlDialog.vue (New)
```

### Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                         HomeView                             │
│  - Loads server list on mount                                │
│  - Manages dialog visibility states                          │
│  - Handles server selection for dialogs                      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ├─────────────────────────────────┐
                              │                                 │
                              ▼                                 ▼
                    ┌──────────────────┐            ┌──────────────────┐
                    │  ServerTable     │            │  Server Store    │
                    │  - Display data  │◄───────────│  - serversList   │
                    │  - Row actions   │            │  - serversDict   │
                    │  - Sorting       │            │  - selectedId    │
                    │  - Filtering     │            └──────────────────┘
                    └──────────────────┘                      │
                              │                               │
                              │                               ▼
                              │                    ┌──────────────────┐
                              │                    │  GraphQL API     │
                              │                    │  - listServers   │
                              │                    │  - mutations     │
                              │                    │  - subscriptions │
                              │                    └──────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ Config       │    │ Stats        │    │ Power        │
│ Dialog       │    │ Dialog       │    │ Dialog       │
│ - Settings   │    │ - Charts     │    │ - Actions    │
│ - Save/Close │    │ - Metrics    │    │ - Start/Stop │
└──────────────┘    └──────────────┘    └──────────────┘
```

## Components and Interfaces

### 1. HomeView.vue (Refactored)

**Purpose**: Main container for the table-based server management interface

**State**:
```javascript
{
  configDialogVisible: false,
  statsDialogVisible: false,
  powerDialogVisible: false,
  selectedServerId: null,
  snackbar: {
    visible: false,
    text: '',
    color: 'primary',
    timeout: 3500
  },
  loading: false
}
```

**Computed**:
- `serversWithIamIssues` - Filters servers where iamStatus !== 'ok'

**Methods**:
- `openConfigDialog(serverId)` - Opens configuration dialog for specified server
- `openStatsDialog(serverId)` - Opens statistics dialog for specified server
- `openPowerDialog(serverId)` - Opens power control dialog for specified server
- `closeAllDialogs()` - Closes all open dialogs
- `handleActionComplete(message, success)` - Shows snackbar notification
- `refreshServerList()` - Reloads server list from API
- `fixIamRole(serverId)` - Executes fixServerRole mutation for specified server

**Lifecycle**:
- `onMounted()` - Load server list, subscribe to state changes
- `onUnmounted()` - Unsubscribe from GraphQL subscriptions

### 2. AppToolbar.vue (New Component)

**Purpose**: Application toolbar with user information and sign-out functionality

**Props**: None (uses userStore directly)

**Emits**: None (handles sign-out internally)

**Computed**:
- `fullname` - User's full name from userStore
- `email` - User's email from userStore
- `isAdmin` - Admin status from userStore

**Methods**:
- `userSignOut()` - Signs out user and redirects to auth page

**Template Structure**:
```vue
<v-app-bar color="primary" dark>
  <v-app-bar-title>Minecraft Server Dashboard</v-app-bar-title>
  
  <v-spacer></v-spacer>
  
  <div class="d-flex align-center mr-4">
    <v-icon class="mr-2">mdi-account-circle</v-icon>
    <div class="d-flex flex-column">
      <span class="text-body-2 font-weight-medium">{{ fullname }}</span>
      <span class="text-caption">{{ email }}</span>
    </div>
    <v-chip v-if="isAdmin" color="accent" size="small" class="ml-2">Admin</v-chip>
  </div>
  
  <v-btn icon @click="userSignOut">
    <v-icon>mdi-logout</v-icon>
  </v-btn>
</v-app-bar>
```

### 3. IamAlert.vue (New Component)

**Purpose**: Alert banner displaying servers with IAM issues and fix buttons

**Props**:
```javascript
{
  servers: Array<ServerInfo> // Servers with IAM issues
}
```

**Emits**:
- `fix-iam(serverId)` - User clicked fix button for a server

**State**:
```javascript
{
  fixingServers: Set<String> // Track which servers are being fixed
}
```

**Template Structure**:
```vue
<v-alert 
  v-if="servers.length > 0"
  type="warning" 
  variant="tonal"
  border="start"
  class="mb-4"
>
  <template v-slot:prepend>
    <v-icon>mdi-alert-circle</v-icon>
  </template>
  
  <div class="font-weight-medium mb-2">IAM Role Issues Detected</div>
  <div class="mb-3">
    The following servers need IAM role fixes to enable power control:
  </div>
  
  <v-list density="compact" class="bg-transparent">
    <v-list-item 
      v-for="server in servers" 
      :key="server.id"
      class="px-0"
    >
      <template v-slot:prepend>
        <v-icon color="warning" size="small">mdi-server-off</v-icon>
      </template>
      
      <v-list-item-title>{{ server.name || server.id }}</v-list-item-title>
      
      <template v-slot:append>
        <v-btn 
          color="warning" 
          variant="elevated"
          size="small"
          @click="$emit('fix-iam', server.id)"
          :loading="fixingServers.has(server.id)"
          prepend-icon="mdi-wrench"
        >
          Fix IAM Role
        </v-btn>
      </template>
    </v-list-item>
  </v-list>
</v-alert>
```

### 4. ServerTable.vue (New Component)

**Purpose**: Displays all servers in a sortable, filterable data table

**Props**:
```javascript
{
  servers: Array<ServerInfo>,
  loading: Boolean
}
```

**Emits**:
- `open-config(serverId)` - User clicked configuration icon
- `open-stats(serverId)` - User clicked statistics icon
- `open-power(serverId)` - User clicked power icon
- `copy-ip(serverId)` - User clicked copy IP button

**Data Table Configuration**:
```javascript
{
  headers: [
    { title: 'Name', key: 'name', sortable: true },
    { title: 'Instance ID', key: 'id', sortable: true },
    { title: 'State', key: 'state', sortable: true },
    { title: 'Public IP', key: 'publicIp', sortable: false },
    { title: 'CPU', key: 'vCpus', sortable: true },
    { title: 'RAM (GB)', key: 'memSize', sortable: true },
    { title: 'Disk (GB)', key: 'diskSize', sortable: true },
    { title: 'Running Time', key: 'runningMinutes', sortable: true },
    { title: 'Actions', key: 'actions', sortable: false, align: 'end' }
  ],
  itemsPerPage: 25,
  search: '',
  sortBy: [{ key: 'name', order: 'asc' }]
}
```

**Features**:
- Search/filter by server name or instance ID
- Sort by any column
- Responsive column visibility (hide less important columns on mobile)
- Row hover effects
- Empty state when no servers available
- Loading skeleton while fetching data

### 3. ServerStatusChip.vue (New Component)

**Purpose**: Displays server state as a colored chip with icon

**Props**:
```javascript
{
  state: String, // 'running', 'stopped', 'starting', 'stopping'
  size: String   // 'small', 'default', 'large'
}
```

**Computed**:
- `chipColor` - Returns color based on state (success/error/warning)
- `chipIcon` - Returns icon based on state (play/stop/loading)

### 5. ServerActionsMenu.vue (New Component)

**Purpose**: Action buttons for each table row with power control as first action

**Props**:
```javascript
{
  serverId: String,
  serverState: String,
  iamStatus: String
}
```

**Emits**:
- `open-config` - Configuration button clicked
- `open-stats` - Statistics button clicked
- `open-power` - Power button clicked
- `copy-ip` - Copy IP button clicked

**Template Structure**:
```vue
<div class="d-flex align-center gap-1">
  <v-tooltip text="Power Control">
    <template v-slot:activator="{ props }">
      <v-btn icon size="small" v-bind="props" @click="$emit('open-power')">
        <v-icon :color="powerIconColor">mdi-power</v-icon>
      </v-btn>
    </template>
  </v-tooltip>
  
  <v-tooltip text="View Statistics">
    <template v-slot:activator="{ props }">
      <v-btn icon size="small" v-bind="props" @click="$emit('open-stats')">
        <v-icon>mdi-chart-line</v-icon>
      </v-btn>
    </template>
  </v-tooltip>
  
  <v-tooltip text="Configuration">
    <template v-slot:activator="{ props }">
      <v-btn icon size="small" v-bind="props" @click="$emit('open-config')">
        <v-icon>mdi-cog</v-icon>
      </v-btn>
    </template>
  </v-tooltip>
  
  <v-tooltip text="Copy IP Address">
    <template v-slot:activator="{ props }">
      <v-btn icon size="small" v-bind="props" @click="$emit('copy-ip')">
        <v-icon>mdi-content-copy</v-icon>
      </v-btn>
    </template>
  </v-tooltip>
</div>
```

### 6. ServerConfigDialog.vue (New Component)

**Purpose**: Modal dialog wrapper for server configuration

**Props**:
```javascript
{
  visible: Boolean,
  serverId: String
}
```

**Emits**:
- `update:visible(Boolean)` - Dialog visibility changed
- `config-saved` - Configuration successfully saved

**Template Structure**:
```vue
<v-dialog 
  :model-value="visible" 
  @update:model-value="$emit('update:visible', $event)"
  max-width="900px" 
  persistent 
  scrollable
>
  <v-card>
    <v-card-title class="bg-primary text-white">
      <v-icon class="mr-2">mdi-cog</v-icon>
      Server Configuration
      <v-spacer></v-spacer>
      <v-btn icon @click="$emit('update:visible', false)">
        <v-icon>mdi-close</v-icon>
      </v-btn>
    </v-card-title>
    
    <v-card-text class="pa-0">
      <ServerSettings 
        @config-saved="handleConfigSaved"
        @close="$emit('update:visible', false)"
      />
    </v-card-text>
  </v-card>
</v-dialog>
```

### 7. ServerStatsDialog.vue (New Component)

**Purpose**: Modal dialog for viewing server statistics and metrics

**Props**:
```javascript
{
  visible: Boolean,
  serverId: String
}
```

**Emits**:
- `update:visible(Boolean)` - Dialog visibility changed

**State**:
```javascript
{
  metricsSubscription: null,
  stateSubscription: null
}
```

**Methods**:
- `subscribeToMetrics()` - Subscribe to real-time metrics
- `unsubscribeFromMetrics()` - Clean up subscriptions
- `formatRunningTime(minutes)` - Format running time display

**Lifecycle**:
- `watch(visible)` - Subscribe when opened, unsubscribe when closed

**Template Structure**:
```vue
<v-dialog 
  :model-value="visible" 
  @update:model-value="$emit('update:visible', $event)"
  max-width="1000px"
  scrollable
>
  <v-card>
    <v-card-title class="bg-primary text-white">
      <v-icon class="mr-2">mdi-chart-line</v-icon>
      Server Statistics - {{ serverName }}
      <v-spacer></v-spacer>
      <v-btn icon @click="$emit('update:visible', false)">
        <v-icon>mdi-close</v-icon>
      </v-btn>
    </v-card-title>
    
    <v-card-text>
      <!-- Server Specs Section -->
      <v-row class="mb-4">
        <v-col>
          <v-chip-group>
            <v-chip><v-icon>mdi-chip</v-icon> {{ vCpus }} vCPU</v-chip>
            <v-chip><v-icon>mdi-memory</v-icon> {{ memSize }} GB</v-chip>
            <v-chip><v-icon>mdi-disc</v-icon> {{ diskSize }} GB</v-chip>
            <v-chip><v-icon>mdi-clock</v-icon> {{ runningTime }}</v-chip>
          </v-chip-group>
        </v-col>
      </v-row>
      
      <!-- Charts Section -->
      <ServerCharts />
    </v-card-text>
  </v-card>
</v-dialog>
```

### 8. PowerControlDialog.vue (New Component)

**Purpose**: Dialog for server power operations (start/stop/restart)

**Props**:
```javascript
{
  visible: Boolean,
  serverId: String,
  serverName: String,
  serverState: String,
  iamStatus: String
}
```

**Emits**:
- `update:visible(Boolean)` - Dialog visibility changed
- `action-complete(message, success)` - Action completed

**Methods**:
- `executeAction(action)` - Execute start/stop/restart mutation
- `fixIamRole()` - Fix IAM permissions

**Template Structure**:
```vue
<v-dialog 
  :model-value="visible" 
  @update:model-value="$emit('update:visible', $event)"
  max-width="400px"
>
  <v-card>
    <v-card-title class="bg-primary text-white">
      <v-icon class="mr-2">mdi-power</v-icon>
      {{ serverName }}
    </v-card-title>
    
    <v-card-text class="pt-4">
      <!-- IAM Error Alert -->
      <v-alert v-if="iamStatus !== 'ok'" type="error" variant="tonal">
        <v-icon>mdi-alert-circle</v-icon>
        You need to fix the IAM role to perform any actions!
        <v-btn @click="fixIamRole" class="mt-2">Fix Now</v-btn>
      </v-alert>
      
      <!-- Power Actions -->
      <div v-else>
        <div v-if="serverState === 'stopped'">
          <v-btn color="success" @click="executeAction('startServer')">
            <v-icon>mdi-play</v-icon> Start
          </v-btn>
        </div>
        <div v-else class="d-flex gap-2">
          <v-btn color="warning" @click="executeAction('stopServer')">
            <v-icon>mdi-stop</v-icon> Stop
          </v-btn>
          <v-btn color="info" @click="executeAction('restartServer')">
            <v-icon>mdi-restart</v-icon> Restart
          </v-btn>
        </div>
      </div>
    </v-card-text>
    
    <v-card-actions>
      <v-spacer></v-spacer>
      <v-btn @click="$emit('update:visible', false)">Cancel</v-btn>
    </v-card-actions>
  </v-card>
</v-dialog>
```

## Data Models

### Server Store Updates

No changes required to the existing Pinia store structure. The store already provides:
- `serversList` - Array of all servers
- `serversDict` - Dictionary for quick lookup by ID
- `selectedServerId` - Currently selected server
- `listServers()` - Fetch all servers
- `updateServer()` - Update server state
- `setSelectedServerId()` - Set selected server

### GraphQL Subscriptions

**State Change Subscription** (Existing):
```graphql
subscription OnChangeState {
  onChangeState {
    id
    state
    publicIp
    runningMinutes
    initStatus
    iamStatus
  }
}
```

**Metrics Subscription** (Existing):
```graphql
subscription OnPutServerMetric($id: String!) {
  onPutServerMetric(id: $id) {
    id
    cpuStats
    memStats
    networkStats
    activeUsers
  }
}
```

## Error Handling

### Network Errors
- Display error snackbar with retry option
- Show loading skeleton during retries
- Fallback to cached data if available

### GraphQL Errors
- Parse error messages from GraphQL responses
- Display user-friendly error messages
- Log detailed errors to console for debugging

### Subscription Errors
- Automatically attempt to reconnect
- Display connection status indicator
- Gracefully degrade to polling if subscriptions fail

### Validation Errors
- Display inline validation errors in forms
- Prevent form submission until errors resolved
- Highlight invalid fields

## Testing Strategy

### Unit Tests

**ServerTable.vue**:
- Test column rendering with mock data
- Test sorting functionality
- Test search/filter functionality
- Test action button emissions
- Test empty state display
- Test loading state display

**ServerStatusChip.vue**:
- Test color mapping for each state
- Test icon mapping for each state
- Test size variations

**ServerActionsMenu.vue**:
- Test button click emissions
- Test tooltip display
- Test disabled states based on IAM status

**PowerControlDialog.vue**:
- Test action button visibility based on server state
- Test IAM error display
- Test mutation execution
- Test success/error handling

### Integration Tests

**HomeView Flow**:
1. Load server list on mount
2. Display servers in table
3. Click configuration icon → opens dialog
4. Save configuration → updates server
5. Close dialog → returns to table

**Real-time Updates**:
1. Subscribe to state changes
2. Receive state update via GraphQL
3. Update table row in real-time
4. Verify UI reflects new state

**Power Control Flow**:
1. Open power dialog for stopped server
2. Click start button
3. Execute mutation
4. Display loading state
5. Show success message
6. Update server state in table

### E2E Tests

**Complete User Journey**:
1. User logs in
2. Views server table
3. Opens statistics dialog
4. Views real-time metrics
5. Closes statistics dialog
6. Opens configuration dialog
7. Updates server settings
8. Saves configuration
9. Opens power dialog
10. Starts server
11. Verifies server state change

## Performance Considerations

### Optimization Strategies

1. **Lazy Loading Dialogs**:
   - Use `v-if` instead of `v-show` for dialogs
   - Only render dialog content when visible
   - Destroy dialog components when closed

2. **Subscription Management**:
   - Only subscribe to metrics for open statistics dialogs
   - Unsubscribe immediately when dialog closes
   - Use single state change subscription for all servers

3. **Virtual Scrolling**:
   - Implement virtual scrolling for tables with >50 servers
   - Use Vuetify's `v-virtual-scroll` component
   - Render only visible rows

4. **Debounced Search**:
   - Debounce search input by 300ms
   - Prevent excessive filtering operations
   - Use computed properties for filtered data

5. **Memoization**:
   - Cache formatted values (running time, etc.)
   - Use computed properties for derived data
   - Avoid recalculating on every render

### Bundle Size

- Reuse existing components (ServerSettings, ServerCharts)
- Minimize new component code
- Use tree-shaking for unused Vuetify components
- Lazy load dialog components

## Responsive Design

### Breakpoints

**Mobile (< 600px)**:
- Hide instance ID column
- Hide CPU, RAM, and Disk columns
- Hide running time column
- Stack action buttons vertically
- Full-screen dialogs
- Simplified table layout

**Tablet (600px - 960px)**:
- Show all columns
- Horizontal action buttons
- Standard dialog sizes
- Compact table padding

**Desktop (> 960px)**:
- Full table layout
- All features visible
- Optimal spacing
- Large dialog sizes

### Touch Interactions

- Increase button touch targets to 48x48px minimum
- Add ripple effects for feedback
- Support swipe gestures for dialogs
- Prevent accidental clicks with confirmation dialogs

## Accessibility

### ARIA Labels
- Add `aria-label` to all icon buttons
- Use `role="table"` for data table
- Add `aria-sort` for sortable columns
- Use `aria-expanded` for dialogs

### Keyboard Navigation
- Tab through table rows
- Enter key to open dialogs
- Escape key to close dialogs
- Arrow keys for table navigation

### Screen Reader Support
- Announce state changes
- Describe action buttons
- Read table headers
- Announce dialog open/close

## Migration Strategy

### Phase 1: Create New Components
1. Build ServerTable.vue with mock data
2. Build ServerStatusChip.vue
3. Build ServerActionsMenu.vue
4. Test components in isolation

### Phase 2: Create Dialog Wrappers
1. Build ServerConfigDialog.vue
2. Build ServerStatsDialog.vue
3. Build PowerControlDialog.vue
4. Integrate existing components

### Phase 3: Refactor HomeView
1. Replace card layout with table
2. Add dialog state management
3. Wire up event handlers
4. Test complete flow

### Phase 4: Polish and Optimize
1. Add loading states
2. Implement error handling
3. Add responsive breakpoints
4. Performance optimization

### Phase 5: Cleanup
1. Remove unused code from HomeView
2. Update tests
3. Update documentation
4. Deploy to production
