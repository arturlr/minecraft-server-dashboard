import { describe, it, expect, vi, beforeEach } from 'vitest';
import { createPinia, setActivePinia } from 'pinia';
import { useServerStore } from '../stores/server';

// Mock the GraphQL client
const mockGraphQLClient = {
  graphql: vi.fn()
};

vi.mock('aws-amplify/api', () => ({
  generateClient: () => mockGraphQLClient
}));

describe('Server Creation End-to-End Integration', () => {
  let serverStore;
  let pinia;

  beforeEach(() => {
    pinia = createPinia();
    setActivePinia(pinia);
    serverStore = useServerStore();
    
    // Reset mocks
    vi.clearAllMocks();
  });

  describe('Complete Server Creation Flow', () => {
    it('should handle complete server creation and integration flow', async () => {
      // Step 1: Initial state - no servers
      expect(serverStore.serversList).toHaveLength(0);
      expect(serverStore.serversDict).toEqual({});

      // Step 2: Mock initial listServers call (empty)
      mockGraphQLClient.graphql.mockResolvedValueOnce({
        data: { listServers: [] }
      });

      await serverStore.listServers();
      expect(serverStore.serversList).toHaveLength(0);

      // Step 3: Simulate server creation process
      // (In real flow, CreateServerDialog would call createServer mutation)
      const newServerId = 'i-1234567890abcdef0';
      const newServerName = 'my-minecraft-server';

      // Step 4: Mock listServers call after creation (includes new server)
      const newServer = {
        id: newServerId,
        name: newServerName,
        state: 'pending',
        vCpus: 2,
        memSize: 4096,
        diskSize: 66, // 16GB root + 50GB data
        publicIp: null,
        initStatus: 'initializing',
        iamStatus: 'ok',
        launchTime: new Date().toISOString(),
        runningMinutes: 0,
        runningMinutesCacheTimestamp: null,
        groupMembers: []
      };

      mockGraphQLClient.graphql.mockResolvedValueOnce({
        data: { listServers: [newServer] }
      });

      // Step 5: Simulate server list refresh after creation (triggered by server-created event)
      await serverStore.listServers();

      // Step 6: Verify new server appears in list
      expect(serverStore.serversList).toHaveLength(1);
      expect(serverStore.getServerById(newServerId)).toBeDefined();
      expect(serverStore.getServerById(newServerId).name).toBe(newServerName);
      expect(serverStore.getServerById(newServerId).state).toBe('pending');

      // Step 7: Simulate server state transitions (via onChangeState subscription)
      // Server starts initializing
      serverStore.updateServer({
        id: newServerId,
        state: 'pending',
        initStatus: 'configuring'
      });

      expect(serverStore.getServerById(newServerId).state).toBe('pending');
      expect(serverStore.getServerById(newServerId).initStatus).toBe('configuring');

      // Step 8: Server becomes running
      serverStore.updateServer({
        id: newServerId,
        state: 'running',
        publicIp: '1.2.3.4',
        initStatus: 'completed'
      });

      expect(serverStore.getServerById(newServerId).state).toBe('running');
      expect(serverStore.getServerById(newServerId).publicIp).toBe('1.2.3.4');
      expect(serverStore.getServerById(newServerId).initStatus).toBe('completed');

      // Step 9: Verify server is fully integrated with existing functionality
      const runningServers = serverStore.getRunningServers;
      expect(runningServers).toHaveLength(1);
      expect(runningServers[0].id).toBe(newServerId);

      // Step 10: Test server name update (existing functionality)
      const newName = 'updated-server-name';
      serverStore.updateServerName(newServerId, newName);
      expect(serverStore.getServerById(newServerId).name).toBe(newName);
    });

    it('should handle server creation with multiple existing servers', async () => {
      // Step 1: Start with existing servers
      const existingServers = [
        {
          id: 'i-existing-1',
          name: 'existing-server-1',
          state: 'running',
          vCpus: 1,
          memSize: 1024,
          diskSize: 16,
          publicIp: '1.1.1.1',
          initStatus: 'completed',
          iamStatus: 'ok',
          launchTime: '2024-01-01T00:00:00Z',
          runningMinutes: 120,
          runningMinutesCacheTimestamp: null,
          groupMembers: []
        },
        {
          id: 'i-existing-2',
          name: 'existing-server-2',
          state: 'stopped',
          vCpus: 2,
          memSize: 2048,
          diskSize: 32,
          publicIp: null,
          initStatus: 'completed',
          iamStatus: 'ok',
          launchTime: '2024-01-02T00:00:00Z',
          runningMinutes: 0,
          runningMinutesCacheTimestamp: null,
          groupMembers: []
        }
      ];

      mockGraphQLClient.graphql.mockResolvedValueOnce({
        data: { listServers: existingServers }
      });

      await serverStore.listServers();
      expect(serverStore.serversList).toHaveLength(2);

      // Step 2: Add new server after creation
      const newServer = {
        id: 'i-new-server',
        name: 'new-server',
        state: 'pending',
        vCpus: 4,
        memSize: 8192,
        diskSize: 66,
        publicIp: null,
        initStatus: 'initializing',
        iamStatus: 'ok',
        launchTime: new Date().toISOString(),
        runningMinutes: 0,
        runningMinutesCacheTimestamp: null,
        groupMembers: []
      };

      const allServers = [...existingServers, newServer];
      mockGraphQLClient.graphql.mockResolvedValueOnce({
        data: { listServers: allServers }
      });

      // Step 3: Refresh server list
      await serverStore.listServers();

      // Step 4: Verify all servers are present
      expect(serverStore.serversList).toHaveLength(3);
      expect(serverStore.getServerById('i-existing-1')).toBeDefined();
      expect(serverStore.getServerById('i-existing-2')).toBeDefined();
      expect(serverStore.getServerById('i-new-server')).toBeDefined();

      // Step 5: Verify new server has correct properties
      const newServerFromStore = serverStore.getServerById('i-new-server');
      expect(newServerFromStore.name).toBe('new-server');
      expect(newServerFromStore.state).toBe('pending');
      expect(newServerFromStore.vCpus).toBe(4);
      expect(newServerFromStore.memSize).toBe(8192);
    });

    it('should handle server creation failure gracefully', async () => {
      // Step 1: Initial state
      mockGraphQLClient.graphql.mockResolvedValueOnce({
        data: { listServers: [] }
      });

      await serverStore.listServers();
      expect(serverStore.serversList).toHaveLength(0);

      // Step 2: Simulate server list refresh failure after creation attempt
      mockGraphQLClient.graphql.mockRejectedValueOnce(new Error('Network error'));

      // Step 3: Attempt to refresh server list
      await expect(serverStore.listServers()).rejects.toThrow('Network error');

      // Step 4: Verify store state remains consistent
      expect(serverStore.loading).toBe(false);
      expect(serverStore.serversList).toHaveLength(0);
    });
  });

  describe('Real-time Updates Integration', () => {
    it('should handle real-time updates for newly created servers', async () => {
      // Step 1: Add a new server
      const newServer = {
        id: 'i-realtime-test',
        name: 'realtime-server',
        state: 'pending',
        vCpus: 2,
        memSize: 4096,
        diskSize: 66,
        publicIp: null,
        initStatus: 'initializing',
        iamStatus: 'ok'
      };

      serverStore.addNewServer(newServer);
      expect(serverStore.getServerById('i-realtime-test').state).toBe('pending');

      // Step 2: Simulate real-time state update (from onChangeState subscription)
      const stateUpdate = {
        id: 'i-realtime-test',
        state: 'running',
        publicIp: '2.3.4.5',
        initStatus: 'completed',
        runningMinutes: 5
      };

      serverStore.updateServer(stateUpdate);

      // Step 3: Verify updates were applied
      const updatedServer = serverStore.getServerById('i-realtime-test');
      expect(updatedServer.state).toBe('running');
      expect(updatedServer.publicIp).toBe('2.3.4.5');
      expect(updatedServer.initStatus).toBe('completed');
      expect(updatedServer.runningMinutes).toBe(5);

      // Step 4: Verify other properties remained unchanged
      expect(updatedServer.name).toBe('realtime-server');
      expect(updatedServer.vCpus).toBe(2);
      expect(updatedServer.memSize).toBe(4096);
    });

    it('should handle multiple rapid state updates', async () => {
      const serverId = 'i-rapid-updates';
      const initialServer = {
        id: serverId,
        name: 'rapid-update-server',
        state: 'pending',
        vCpus: 1,
        memSize: 1024,
        diskSize: 16,
        publicIp: null,
        initStatus: 'initializing',
        iamStatus: 'ok'
      };

      serverStore.addNewServer(initialServer);

      // Simulate rapid state changes
      const updates = [
        { id: serverId, state: 'pending', initStatus: 'configuring' },
        { id: serverId, state: 'pending', initStatus: 'installing' },
        { id: serverId, state: 'running', publicIp: '3.4.5.6' },
        { id: serverId, initStatus: 'completed', runningMinutes: 1 }
      ];

      updates.forEach(update => {
        serverStore.updateServer(update);
      });

      // Verify final state
      const finalServer = serverStore.getServerById(serverId);
      expect(finalServer.state).toBe('running');
      expect(finalServer.publicIp).toBe('3.4.5.6');
      expect(finalServer.initStatus).toBe('completed');
      expect(finalServer.runningMinutes).toBe(1);
    });
  });

  describe('Integration with Existing Features', () => {
    it('should integrate with server filtering and search', async () => {
      // Add multiple servers including a new one
      const servers = [
        {
          id: 'i-server-1',
          name: 'production-server',
          state: 'running',
          vCpus: 4,
          memSize: 8192,
          diskSize: 100,
          publicIp: '1.1.1.1',
          initStatus: 'completed',
          iamStatus: 'ok'
        },
        {
          id: 'i-server-2',
          name: 'development-server',
          state: 'stopped',
          vCpus: 2,
          memSize: 4096,
          diskSize: 50,
          publicIp: null,
          initStatus: 'completed',
          iamStatus: 'ok'
        },
        {
          id: 'i-new-server',
          name: 'new-minecraft-server',
          state: 'running',
          vCpus: 2,
          memSize: 4096,
          diskSize: 66,
          publicIp: '2.2.2.2',
          initStatus: 'completed',
          iamStatus: 'ok'
        }
      ];

      servers.forEach(server => serverStore.addNewServer(server));

      // Test getRunningServers getter
      const runningServers = serverStore.getRunningServers;
      expect(runningServers).toHaveLength(2);
      expect(runningServers.map(s => s.id)).toContain('i-new-server');

      // Test getServerById
      const newServer = serverStore.getServerById('i-new-server');
      expect(newServer).toBeDefined();
      expect(newServer.name).toBe('new-minecraft-server');

      // Test server name functionality
      const serverName = serverStore.getServerName;
      serverStore.setSelectedServerId('i-new-server');
      expect(serverStore.getServerName).toBe('new-minecraft-server');
    });

    it('should work with IAM status checking', async () => {
      const serverWithIamIssue = {
        id: 'i-iam-issue',
        name: 'server-with-iam-issue',
        state: 'running',
        vCpus: 2,
        memSize: 4096,
        diskSize: 66,
        publicIp: '3.3.3.3',
        initStatus: 'completed',
        iamStatus: 'missing' // IAM issue
      };

      const serverWithoutIamIssue = {
        id: 'i-iam-ok',
        name: 'server-iam-ok',
        state: 'running',
        vCpus: 2,
        memSize: 4096,
        diskSize: 66,
        publicIp: '4.4.4.4',
        initStatus: 'completed',
        iamStatus: 'ok'
      };

      serverStore.addNewServer(serverWithIamIssue);
      serverStore.addNewServer(serverWithoutIamIssue);

      // Test IAM compliance checking
      serverStore.setSelectedServerId('i-iam-issue');
      expect(serverStore.isServerIamCompliant).toBe(false);

      serverStore.setSelectedServerId('i-iam-ok');
      expect(serverStore.isServerIamCompliant).toBe(true);
    });
  });
});