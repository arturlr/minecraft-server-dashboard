# State Management Improvements

## Current Approach Issues
The current implementation in `server.js` using `updateServerStateDict` has several limitations:

1. Manual state updates through `updateServerStateDict` can lead to inconsistencies
2. Tight coupling between components and state management logic
3. Redundant state updates across components
4. Limited reactivity for nested state changes

## Recommended Solution

### 1. Leverage Pinia's State Management

Instead of manually updating server state through `updateServerStateDict`, utilize Pinia's built-in state management features:

```javascript
export const useServerStore = defineStore("server", {
  state: () => ({
    serversList: [],
    serversDict: {},
    selectedServer: {},
    monthlyUsage: {},
    loading: false,
    paginationToken: ""
  }),

  getters: {
    // Add computed properties as getters
    getServerById: (state) => (id) => state.serversDict[id],
    getServerState: (state) => (id) => state.serversDict[id]?.state,
    getRunningServers: (state) => 
      Object.values(state.serversDict).filter(server => server.state === 'running')
  },

  actions: {
    updateServer(server) {
      if (server.id) {
        // Update both dictionary and selected server if matched
        this.serversDict[server.id] = { ...this.serversDict[server.id], ...server };
        
        if (this.selectedServer.id === server.id) {
          this.selectedServer = { ...this.selectedServer, ...server };
        }
      }
    },

    setSelectedServer(server) {
      this.selectedServer = server;
    },

    // Existing actions remain the same
    async listServers() {
      // Your existing implementation
    }
  }
});
```

### 2. Component Usage

Update components to use the store's actions and getters:

```javascript
// In components
import { useServerStore } from "../stores/server";

const serverStore = useServerStore();

// Update server state
serverStore.updateServer({
  id: "server-1",
  state: "running",
  publicIp: "1.2.3.4"
});

// Access server state
const serverState = serverStore.getServerState("server-1");
```

### Benefits

1. **Better Reactivity**: Pinia automatically handles reactivity for state changes
2. **Centralized State Management**: Single source of truth for server state
3. **Type Safety**: Better TypeScript support and type inference
4. **Developer Tools**: Better debugging with Vue DevTools
5. **Simplified Components**: Components only need to dispatch actions and access state
6. **Optimized Updates**: Prevents unnecessary re-renders with computed properties

### Implementation Steps

1. Remove the `updateServerStateDict` method
2. Add getters for commonly accessed state
3. Create a single `updateServer` action for state mutations
4. Update components to use store actions instead of direct state mutation
5. Add TypeScript interfaces for better type safety (optional)

### Migration Strategy

1. Implement new store structure alongside existing code
2. Gradually update components to use new methods
3. Remove old implementation once all components are migrated
4. Add tests for new store functionality

This solution provides better state management, improved maintainability, and follows Vue.js/Pinia best practices.