import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';

// Use vi.hoisted to ensure mockGraphQLClient is available in hoisted mock
const { mockGraphQLClient } = vi.hoisted(() => ({
  mockGraphQLClient: {
    graphql: vi.fn()
  }
}));

vi.mock('aws-amplify/api', () => ({
  generateClient: () => mockGraphQLClient
}));

// Mock the stores
vi.mock('../../stores/user', () => ({
  useUserStore: () => ({
    isAdmin: true,
    fullname: 'Test Admin',
    email: 'admin@test.com'
  })
}));

// Now import the component
import HomeView from '../HomeView.vue';

// Mock all the child components to focus on integration logic
vi.mock('../components/AppToolbar.vue', () => ({
  default: {
    name: 'AppToolbar',
    template: '<div data-testid="app-toolbar"><slot /></div>',
    emits: ['server-created'],
    setup(props, { emit }) {
      // Expose method to trigger server creation for testing
      const triggerServerCreated = () => emit('server-created');
      return { triggerServerCreated };
    }
  }
}));

vi.mock('../components/ServerTable.vue', () => ({
  default: {
    name: 'ServerTable',
    template: '<div data-testid="server-table">{{ servers.length }} servers</div>',
    props: ['servers', 'loading'],
    emits: ['server-name-updated']
  }
}));

vi.mock('../components/IamAlert.vue', () => ({
  default: {
    name: 'IamAlert',
    template: '<div data-testid="iam-alert"></div>',
    props: ['servers']
  }
}));

// Mock Vuetify
vi.mock('vuetify', () => ({
  createVuetify: () => ({}),
  VApp: { name: 'VApp', template: '<div><slot /></div>' },
  VMain: { name: 'VMain', template: '<div><slot /></div>' },
  VContainer: { name: 'VContainer', template: '<div><slot /></div>' },
  VSnackbar: { name: 'VSnackbar', template: '<div><slot /></div>' },
  VBtn: { name: 'VBtn', template: '<button><slot /></button>' }
}));

describe('HomeView Server Creation Integration', () => {
  let wrapper;
  let pinia;

  beforeEach(() => {
    pinia = createPinia();
    setActivePinia(pinia);
    
    // Reset mocks
    vi.clearAllMocks();
    
    // Mock successful listServers response
    mockGraphQLClient.graphql.mockResolvedValue({
      data: {
        listServers: []
      }
    });
  });

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount();
    }
  });

  describe('Server Creation Event Handling', () => {
    it('should handle server-created event from AppToolbar', async () => {
      // Mock listServers to return a new server after creation
      const mockServersAfterCreation = [
        {
          id: 'i-1234567890abcdef0',
          name: 'new-server',
          state: 'pending',
          vCpus: 2,
          memSize: 4096,
          diskSize: 66,
          publicIp: null,
          initStatus: 'initializing',
          iamStatus: 'ok'
        }
      ];

      // First call returns empty list, second call returns new server
      mockGraphQLClient.graphql
        .mockResolvedValueOnce({ data: { listServers: [] } })
        .mockResolvedValueOnce({ data: { listServers: mockServersAfterCreation } });

      wrapper = mount(HomeView, {
        global: {
          plugins: [pinia],
          stubs: {
            'v-layout': { template: '<div><slot /></div>' },
            'v-main': { template: '<div><slot /></div>' },
            'v-container': { template: '<div><slot /></div>' },
            'v-snackbar': { template: '<div><slot /></div>' },
            'v-btn': { template: '<button><slot /></button>' },
            'ErrorBoundary': { template: '<div><slot /></div>' }
          }
        }
      });

      // Wait for initial load
      await wrapper.vm.$nextTick();
      
      // Verify initial state
      expect(wrapper.vm.serverStore.serversList).toHaveLength(0);

      // Trigger server creation event
      const appToolbar = wrapper.findComponent({ name: 'AppToolbar' });
      await appToolbar.vm.$emit('server-created');

      // Wait for the server list to refresh
      await wrapper.vm.$nextTick();
      await new Promise(resolve => setTimeout(resolve, 0)); // Wait for async operations

      // Verify listServers was called again
      expect(mockGraphQLClient.graphql).toHaveBeenCalledTimes(2);
      
      // Verify server was added to store
      expect(wrapper.vm.serverStore.serversList).toHaveLength(1);
      expect(wrapper.vm.serverStore.serversList[0].id).toBe('i-1234567890abcdef0');
    });

    it('should handle server creation refresh error gracefully', async () => {
      // Mock listServers to fail on second call
      mockGraphQLClient.graphql
        .mockResolvedValueOnce({ data: { listServers: [] } })
        .mockRejectedValueOnce(new Error('Network error'));

      wrapper = mount(HomeView, {
        global: {
          plugins: [pinia],
          stubs: {
            'v-layout': { template: '<div><slot /></div>' },
            'v-main': { template: '<div><slot /></div>' },
            'v-container': { template: '<div><slot /></div>' },
            'v-snackbar': { template: '<div><slot /></div>' },
            'v-btn': { template: '<button><slot /></button>' },
            'ErrorBoundary': { template: '<div><slot /></div>' }
          }
        }
      });

      await wrapper.vm.$nextTick();

      // Trigger server creation event
      const appToolbar = wrapper.findComponent({ name: 'AppToolbar' });
      await appToolbar.vm.$emit('server-created');

      await wrapper.vm.$nextTick();
      await new Promise(resolve => setTimeout(resolve, 0));

      // Should handle error gracefully without crashing
      expect(wrapper.vm.snackbar.visible).toBe(true);
      expect(wrapper.vm.snackbar.color).toBe('error');
    });
  });

  describe('Server List Refresh Integration', () => {
    it('should refresh server list on mount', async () => {
      const mockServers = [
        {
          id: 'i-existing-server',
          name: 'existing-server',
          state: 'running',
          vCpus: 1,
          memSize: 1024,
          diskSize: 16,
          publicIp: '1.2.3.4',
          initStatus: 'completed',
          iamStatus: 'ok'
        }
      ];

      mockGraphQLClient.graphql.mockResolvedValue({
        data: { listServers: mockServers }
      });

      wrapper = mount(HomeView, {
        global: {
          plugins: [pinia],
          stubs: {
            'v-layout': { template: '<div><slot /></div>' },
            'v-main': { template: '<div><slot /></div>' },
            'v-container': { template: '<div><slot /></div>' },
            'v-snackbar': { template: '<div><slot /></div>' },
            'v-btn': { template: '<button><slot /></button>' },
            'ErrorBoundary': { template: '<div><slot /></div>' }
          }
        }
      });

      await wrapper.vm.$nextTick();

      // Verify listServers was called on mount
      expect(mockGraphQLClient.graphql).toHaveBeenCalledWith({
        query: expect.any(String)
      });

      // Verify servers were loaded
      expect(wrapper.vm.serverStore.serversList).toHaveLength(1);
      expect(wrapper.vm.serverStore.serversList[0].id).toBe('i-existing-server');
    });

    it('should handle server list loading error on mount', async () => {
      mockGraphQLClient.graphql.mockRejectedValue(new Error('API Error'));

      wrapper = mount(HomeView, {
        global: {
          plugins: [pinia],
          stubs: {
            'v-layout': { template: '<div><slot /></div>' },
            'v-main': { template: '<div><slot /></div>' },
            'v-container': { template: '<div><slot /></div>' },
            'v-snackbar': { template: '<div><slot /></div>' },
            'v-btn': { template: '<button><slot /></button>' },
            'ErrorBoundary': { template: '<div><slot /></div>' }
          }
        }
      });

      await wrapper.vm.$nextTick();
      await new Promise(resolve => setTimeout(resolve, 0));

      // Should handle error gracefully
      expect(wrapper.vm.snackbar.visible).toBe(true);
      expect(wrapper.vm.snackbar.color).toBe('error');
      expect(wrapper.vm.serverStore.loading).toBe(false);
    });
  });

  describe('Real-time Updates Integration', () => {
    it('should subscribe to state changes on mount', async () => {
      // Mock subscription
      const mockSubscription = {
        subscribe: vi.fn().mockReturnValue({
          unsubscribe: vi.fn()
        })
      };

      mockGraphQLClient.graphql
        .mockResolvedValueOnce({ data: { listServers: [] } })
        .mockReturnValueOnce(mockSubscription);

      wrapper = mount(HomeView, {
        global: {
          plugins: [pinia],
          stubs: {
            'v-layout': { template: '<div><slot /></div>' },
            'v-main': { template: '<div><slot /></div>' },
            'v-container': { template: '<div><slot /></div>' },
            'v-snackbar': { template: '<div><slot /></div>' },
            'v-btn': { template: '<button><slot /></button>' },
            'ErrorBoundary': { template: '<div><slot /></div>' }
          }
        }
      });

      await wrapper.vm.$nextTick();

      // Verify subscription was set up
      expect(mockGraphQLClient.graphql).toHaveBeenCalledWith({
        query: expect.stringContaining('onChangeState')
      });
      expect(mockSubscription.subscribe).toHaveBeenCalled();
    });

    it('should clean up subscriptions on unmount', async () => {
      const mockUnsubscribe = vi.fn();
      const mockSubscription = {
        subscribe: vi.fn().mockReturnValue({
          unsubscribe: mockUnsubscribe
        })
      };

      mockGraphQLClient.graphql
        .mockResolvedValueOnce({ data: { listServers: [] } })
        .mockReturnValueOnce(mockSubscription);

      wrapper = mount(HomeView, {
        global: {
          plugins: [pinia],
          stubs: {
            'v-layout': { template: '<div><slot /></div>' },
            'v-main': { template: '<div><slot /></div>' },
            'v-container': { template: '<div><slot /></div>' },
            'v-snackbar': { template: '<div><slot /></div>' },
            'v-btn': { template: '<button><slot /></button>' },
            'ErrorBoundary': { template: '<div><slot /></div>' }
          }
        }
      });

      await wrapper.vm.$nextTick();

      // Unmount component
      wrapper.unmount();

      // Verify subscription was cleaned up
      expect(mockUnsubscribe).toHaveBeenCalled();
    });
  });

  describe('Snackbar Notifications', () => {
    it('should show success notification for server creation', async () => {
      mockGraphQLClient.graphql
        .mockResolvedValueOnce({ data: { listServers: [] } })
        .mockResolvedValueOnce({ data: { listServers: [{ id: 'new-server' }] } });

      wrapper = mount(HomeView, {
        global: {
          plugins: [pinia],
          stubs: {
            'v-layout': { template: '<div><slot /></div>' },
            'v-main': { template: '<div><slot /></div>' },
            'v-container': { template: '<div><slot /></div>' },
            'v-snackbar': { template: '<div><slot /></div>' },
            'v-btn': { template: '<button><slot /></button>' },
            'ErrorBoundary': { template: '<div><slot /></div>' }
          }
        }
      });

      await wrapper.vm.$nextTick();

      // Trigger server creation
      const appToolbar = wrapper.findComponent({ name: 'AppToolbar' });
      await appToolbar.vm.$emit('server-created');

      await wrapper.vm.$nextTick();

      // Verify success notification
      expect(wrapper.vm.snackbar.visible).toBe(true);
      expect(wrapper.vm.snackbar.color).toBe('success');
      expect(wrapper.vm.snackbar.text).toContain('Server creation completed');
    });
  });
});