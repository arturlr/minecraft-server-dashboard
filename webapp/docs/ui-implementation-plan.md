# UI Implementation Plan - BlockNode Dashboard

## Status: ✅ IMPLEMENTED

## Overview

Recreate the wireframe designs from `webapp/wireframe/` using Vue 3 and Vuetify, maintaining the dark gaming aesthetic with green accent colors.

## Design System

### Color Palette
| Token | Value | Usage |
|-------|-------|-------|
| `primary` | `#13ec5b` | Buttons, accents, active states |
| `background-dark` | `#102216` | Main background |
| `surface-dark` | `#1c2e24` | Cards, panels |
| `surface-darker` | `#15261d` | Nested containers |
| `border-green` | `#28392e` | Borders, dividers |
| `text-muted` | `#9db9a6` | Secondary text, labels |

### Typography
- Font: Space Grotesk (Google Fonts)
- Weights: 400 (regular), 500 (medium), 700 (bold)

### Icons
- Material Symbols Outlined (Google Fonts)

---

## Pages to Implement

### 1. Dashboard (Main View)
**Source:** `dashboard.html` / `dashboard.png`

#### Components
| Component | Description |
|-----------|-------------|
| `AppSidebar` | Navigation with logo, menu items, user profile |
| `DashboardHeader` | Title, notifications, "New Instance" button |
| `StatsCards` | "Servers Online" and "Active Players" summary cards |
| `ServerSearch` | Search input with pagination info |
| `ServerCard` | Server instance card with metrics and controls |
| `AccessControlTable` | User management table |

#### ServerCard Features
- Hero image with status badge (ONLINE/OFFLINE)
- Server name and IP address
- CPU load bar chart visualization
- Metrics grid: Players, Memory, Network (RX/TX)
- Action buttons: Start/Stop, Restart, Schedule, Limits
- Offline state: grayscale, disabled controls

---

### 2. Server Settings
**Source:** `ServerSetting.html` / `ServerSetting.png`

#### Components
| Component | Description |
|-----------|-------------|
| `SettingsSidebar` | Settings-specific navigation |
| `SettingsHeader` | Server name, status badge, Restart/Save buttons |
| `GeneralProperties` | Server name, version, difficulty, max players |
| `ResourceWatchdog` | Auto-shutdown toggle, CPU threshold slider, idle duration |
| `TaskScheduler` | Scheduled tasks list, new event form |
| `AccessControlSection` | Member search, invite button, members table |

#### Form Elements
- Text inputs with dark styling
- Select dropdowns with custom chevron
- Toggle switches (green when active)
- Range slider for CPU threshold
- Segmented button group for difficulty

---

## Implementation Phases

### Phase 1: Project Setup ✅
1. Create Vue 3 + Vite project
2. Install Vuetify 3
3. Configure custom theme (colors, typography)
4. Add Google Fonts (Space Grotesk, Material Symbols)
5. Set up Vue Router

### Phase 2: Layout & Navigation ✅
1. Create `AppLayout` wrapper component
2. Implement `AppSidebar` with responsive collapse
3. Build `AppHeader` component
4. Configure routes: `/dashboard`, `/servers/:id/settings`

### Phase 3: Dashboard Page ✅
1. `StatsCards` - summary metrics
2. `ServerSearch` - search input with pagination
3. `ServerCard` - full server card with all states
4. `AccessControlTable` - user table with role badges

### Phase 4: Server Settings Page ✅
1. `SettingsSidebar` - settings navigation
2. `GeneralProperties` - form section
3. `ResourceWatchdog` - auto-shutdown card
4. `TaskScheduler` - scheduled tasks card
5. `AccessControlSection` - members management

### Phase 5: API Integration ✅
1. Added AWS Amplify for Cognito + AppSync
2. Created Pinia stores (server, user)
3. Connected views to GraphQL API
4. Added error handling utilities

---

## File Structure

```
webapp/src/
├── assets/
│   └── styles/
│       └── main.scss          # Global styles, scrollbar
├── components/
│   ├── layout/
│   │   ├── AppSidebar.vue     # ✅ Main navigation sidebar
│   │   ├── AppHeader.vue      # ✅ Top header with actions
│   │   └── AppLayout.vue      # ✅ Layout wrapper
│   ├── dashboard/
│   │   ├── StatsCards.vue     # ✅ Online/players summary
│   │   ├── ServerCard.vue     # ✅ Server instance card
│   │   └── AccessControlTable.vue # ✅ User table
│   └── settings/
│       ├── SettingsSidebar.vue    # ✅ Settings navigation
│       ├── GeneralProperties.vue  # ✅ Server config form
│       ├── ResourceWatchdog.vue   # ✅ Auto-shutdown settings
│       ├── TaskScheduler.vue      # ✅ Schedule settings
│       └── AccessControlSection.vue # ✅ Members management
├── views/
│   ├── DashboardView.vue      # ✅ Main dashboard (API integrated)
│   └── ServerSettingsView.vue # ✅ Server settings (API integrated)
├── stores/
│   ├── server.js              # ✅ Server operations
│   └── user.js                # ✅ Authentication
├── graphql/
│   ├── queries.js             # ✅ GraphQL queries
│   ├── mutations.js           # ✅ GraphQL mutations
│   └── subscriptions.js       # ✅ Real-time subscriptions
├── router/
│   └── index.js               # ✅ Vue Router config
├── plugins/
│   └── vuetify.js             # ✅ Theme configuration
├── utils/
│   └── errorHandler.js        # ✅ Error parsing
└── configAmplify.js           # ✅ AWS Amplify setup
```

---

## Vuetify Theme Configuration

```javascript
// plugins/vuetify.js
export default createVuetify({
  theme: {
    defaultTheme: 'dark',
    themes: {
      dark: {
        colors: {
          primary: '#13ec5b',
          background: '#102216',
          surface: '#1c2e24',
          'surface-variant': '#15261d',
          'on-surface': '#ffffff',
          'on-surface-variant': '#9db9a6',
        }
      }
    }
  }
})
```

---

## Key Vuetify Components Mapping

| Wireframe Element | Vuetify Component |
|-------------------|-------------------|
| Sidebar | `v-navigation-drawer` |
| Cards | `v-card` |
| Buttons | `v-btn` |
| Text inputs | `v-text-field` |
| Selects | `v-select` |
| Toggles | `v-switch` |
| Sliders | `v-slider` |
| Tables | `v-data-table` |
| Chips/Badges | `v-chip` |
| Progress bars | `v-progress-linear` |
| Button groups | `v-btn-toggle` |

---

## Custom Styling Requirements

1. **Scrollbar**: Custom dark scrollbar with green hover
2. **Glow effects**: `box-shadow` with primary color on buttons
3. **Status badges**: Rounded pills with pulse animation for online
4. **Bar chart**: Custom CSS bars for CPU visualization
5. **Card hover**: Subtle background change on hover

---

## Responsive Breakpoints

| Breakpoint | Behavior |
|------------|----------|
| `< 960px` | Sidebar collapses to hamburger menu |
| `< 600px` | Server cards stack vertically, simplified metrics |

---

## API Integration

### Dependencies Added
- `aws-amplify` - AWS Amplify SDK for Cognito auth and AppSync GraphQL
- `pinia` - Vue state management

### Files Structure
```
webapp/src/
├── graphql/
│   ├── queries.js       # GraphQL queries (listServers, getServerConfig, etc.)
│   ├── mutations.js     # GraphQL mutations (startServer, stopServer, etc.)
│   └── subscriptions.js # Real-time subscriptions
├── stores/
│   ├── server.js        # Server operations store
│   └── user.js          # Authentication store
├── utils/
│   └── errorHandler.js  # GraphQL error parsing
├── configAmplify.js     # AWS Amplify configuration
└── .env                 # Environment variables
```

### Server Store Methods
| Method | Description |
|--------|-------------|
| `listServers()` | Fetch all servers |
| `getServerConfig(id)` | Get server configuration |
| `getServerUsers(id)` | Get server members |
| `getServerMetrics(id)` | Get server metrics |
| `startServer(id)` | Start a server |
| `stopServer(id)` | Stop a server |
| `restartServer(id)` | Restart a server |
| `putServerConfig(config)` | Save server configuration |
| `fixServerRole(id)` | Fix IAM instance profile |

### User Store Methods
| Method | Description |
|--------|-------------|
| `getSession()` | Check authentication status |
| `login()` | Redirect to Google OAuth |
| `logout()` | Sign out user |

### Environment Variables
```
VITE_AWS_REGION=us-west-2
VITE_GRAPHQL_ENDPOINT=[AppSync endpoint]
VITE_IDENTITY_POOL_ID=[Cognito Identity Pool]
VITE_COGNITO_USER_POOL_CLIENT_ID=[User Pool Client ID]
VITE_COGNITO_USER_POOL_ID=[User Pool ID]
VITE_COGNITO_DOMAIN=[Cognito domain]
```

---

## Integration Points

- **GraphQL**: Queries/mutations copied from `dashboard/src/graphql/`
- **Auth**: Cognito OAuth via AWS Amplify (same as original dashboard)
- **State**: Pinia stores for server data and user auth
- **Real-time**: Subscriptions available for `onPutServerMetric`, `onChangeState`

---

## Running the App

```bash
cd webapp
npm install
npm run dev
```

Build for production:
```bash
npm run build
```
