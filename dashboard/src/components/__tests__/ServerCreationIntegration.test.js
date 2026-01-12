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

// Mock the user store
vi.mock('../../stores/user', () => ({
  useUserStore: () => ({
    isAdmin: true,
    fullname: 'Test Admin',
    email: 'admin@test.com'
  })
}));

import { useServerStore } from '../../stores/server';

describe('Server Creation Integration', () => {
  let serverStore;
  let pinia;

  beforeEach(() => {
    pinia = createPinia();
    setActivePinia(pinia);
    serverStore = useServerStore();
    
    // Reset mocks
    vi.clearAllMocks();
  });

  describe('Server Store Integration', () => {
    it('should add new server to store when addNewServer is called', () => {
      const newServer = {
        id: 'i-1234567890abcdef0',
        name: 'test-server',
        state: 'pending',
        vCpus: 1,
        memSize: 1024,
        diskSize: 16,
        publicIp: null,
        initStatus: 'initializing',
        iamStatus: 'ok'
      };

      // Initially empty
      expect(serverStore.serversList).toHaveLength(0);
      expect(serverStore.serversDict).toEqual({});

      // Add new server
      serverStore.addNewServer(newServer);

      // Verify server was added
      expect(serverStore.serversList).toHaveLength(1);
      expect(serverStore.serversList[0]).toEqual(newServer);
      expect(serverStore.serversDict[newServer.id]).toEqual(newServer);
    });

    it('should update existing server when addNewServer is called with existing ID', () => {
      const initialServer = {
        id: 'i-1234567890abcdef0',
        name: 'test-server',
        state: 'pending',
        vCpus: 1,
        memSize: 1024,
        diskSize: 16,
        publicIp: null,
        initStatus: 'initializing',
        iamStatus: 'ok'
      };

      const updatedServer = {
        ...initialServer,
        state: 'running',
        publicIp: '1.2.3.4',
        initStatus: 'completed'
      };

      // Add initial server
      serverStore.addNewServer(initialServer);
      expect(serverStore.serversList).toHaveLength(1);

      // Update server
      serverStore.addNewServer(updatedServer);

      // Verify server was updated, not duplicated
      expect(serverStore.serversList).toHaveLength(1);
      expect(serverStore.serversList[0]).toEqual(updatedServer);
      expect(serverStore.serversDict[initialServer.id]).toEqual(updatedServer);
    });

    it('should handle listServers response correctly', async () => {
      const mockServers = [
        {
          id: 'i-1111111111111111',
          name: 'server-1',
          state: 'running',
          vCpus: 1,
          memSize: 1024,
          diskSize: 16,
          publicIp: '1.2.3.4',
          initStatus: 'completed',
          iamStatus: 'ok'
        },
        {
          id: 'i-2222222222222222',
          name: 'server-2',
          state: 'stopped',
          vCpus: 2,
          memSize: 2048,
          diskSize: 32,
          publicIp: null,
          initStatus: 'completed',
          iamStatus: 'ok'
        }
      ];

      // Mock successful GraphQL response
      mockGraphQLClient.graphql.mockResolvedValue({
        data: {
          listServers: mockServers
        }
      });

      // Call listServers
      const result = await serverStore.listServers();

      // Verify the result
      expect(result).toEqual(mockServers);
      expect(serverStore.serversList).toHaveLength(2);
      expect(serverStore.serversDict).toHaveProperty('i-1111111111111111');
      expect(serverStore.serversDict).toHaveProperty('i-2222222222222222');
      expect(serverStore.loading).toBe(false);
    });

    it('should handle empty listServers response', async () => {
      // Mock empty response
      mockGraphQLClient.graphql.mockResolvedValue({
        data: {
          listServers: []
        }
      });

      const result = await serverStore.listServers();

      expect(result).toEqual([]);
      expect(serverStore.serversList).toHaveLength(0);
      expect(serverStore.serversDict).toEqual({});
      expect(serverStore.loading).toBe(false);
    });

    it('should handle listServers error correctly', async () => {
      const mockError = new Error('GraphQL Error');
      mockGraphQLClient.graphql.mockRejectedValue(mockError);

      await expect(serverStore.listServers()).rejects.toThrow();
      expect(serverStore.loading).toBe(false);
    });
  });

  describe('Server State Updates', () => {
    it('should update server state correctly', () => {
      const initialServer = {
        id: 'i-1234567890abcdef0',
        name: 'test-server',
        state: 'pending',
        vCpus: 1,
        memSize: 1024,
        diskSize: 16,
        publicIp: null,
        initStatus: 'initializing',
        iamStatus: 'ok'
      };

      // Add initial server
      serverStore.addNewServer(initialServer);

      // Update server state
      const stateUpdate = {
        id: 'i-1234567890abcdef0',
        state: 'running',
        publicIp: '1.2.3.4',
        initStatus: 'completed'
      };

      serverStore.updateServer(stateUpdate);

      // Verify state was updated
      const updatedServer = serverStore.getServerById('i-1234567890abcdef0');
      expect(updatedServer.state).toBe('running');
      expect(updatedServer.publicIp).toBe('1.2.3.4');
      expect(updatedServer.initStatus).toBe('completed');
      // Other properties should remain unchanged
      expect(updatedServer.name).toBe('test-server');
      expect(updatedServer.vCpus).toBe(1);
    });
  });

  describe('Server Creation Flow Integration', () => {
    it('should handle complete server creation flow', async () => {
      // Step 1: Initial empty state
      expect(serverStore.serversList).toHaveLength(0);

      // Step 2: Mock server creation response (server gets created in backend)
      const newServerId = 'i-1234567890abcdef0';
      
      // Step 3: Mock listServers response after creation (includes new server)
      const serversAfterCreation = [
        {
          id: newServerId,
          name: 'new-minecraft-server',
          state: 'pending',
          vCpus: 2,
          memSize: 4096,
          diskSize: 66, // 16GB root + 50GB data
          publicIp: null,
          initStatus: 'initializing',
          iamStatus: 'ok',
          launchTime: new Date().toISOString(),
          runningMinutes: 0
        }
      ];

      mockGraphQLClient.graphql.mockResolvedValue({
        data: {
          listServers: serversAfterCreation
        }
      });

      // Step 4: Simulate server list refresh after creation
      await serverStore.listServers();

      // Step 5: Verify new server appears in list
      expect(serverStore.serversList).toHaveLength(1);
      expect(serverStore.getServerById(newServerId)).toBeDefined();
      expect(serverStore.getServerById(newServerId).name).toBe('new-minecraft-server');
      expect(serverStore.getServerById(newServerId).state).toBe('pending');
    });

    it('should handle server state transitions during creation', () => {
      const serverId = 'i-1234567890abcdef0';
      
      // Initial server state after creation
      const initialServer = {
        id: serverId,
        name: 'new-server',
        state: 'pending',
        vCpus: 2,
        memSize: 4096,
        diskSize: 66,
        publicIp: null,
        initStatus: 'initializing',
        iamStatus: 'ok'
      };

      serverStore.addNewServer(initialServer);

      // Simulate state transitions
      serverStore.updateServer({ id: serverId, state: 'running', publicIp: '1.2.3.4' });
      expect(serverStore.getServerById(serverId).state).toBe('running');
      expect(serverStore.getServerById(serverId).publicIp).toBe('1.2.3.4');

      serverStore.updateServer({ id: serverId, initStatus: 'completed' });
      expect(serverStore.getServerById(serverId).initStatus).toBe('completed');
    });
  });

  describe('Error Handling', () => {
    it('should handle invalid server data gracefully', () => {
      // Try to add server without ID
      serverStore.addNewServer({ name: 'invalid-server' });
      expect(serverStore.serversList).toHaveLength(0);

      // Try to add null server
      serverStore.addNewServer(null);
      expect(serverStore.serversList).toHaveLength(0);

      // Try to add undefined server
      serverStore.addNewServer(undefined);
      expect(serverStore.serversList).toHaveLength(0);
    });

    it('should handle updateServer with invalid ID gracefully', () => {
      serverStore.updateServer({ id: 'non-existent-id', state: 'running' });
      // Should not throw error, just do nothing
      expect(serverStore.serversList).toHaveLength(0);
    });
  });
});