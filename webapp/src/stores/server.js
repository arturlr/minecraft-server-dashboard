import { defineStore } from "pinia";
import { generateClient } from 'aws-amplify/api';
import * as queries from "../graphql/queries";
import * as mutations from "../graphql/mutations";
import * as subscriptions from "../graphql/subscriptions";
import { configAmplify } from "../configAmplify";
import { parseGraphQLError } from "../utils/errorHandler";

configAmplify();
const client = generateClient();

export const useServerStore = defineStore("server", {
  state: () => ({
    servers: [],
    serversById: {},
    serverMetrics: {},
    selectedServerId: null,
    loading: false,
    error: null,
    subscriptionHandles: {}
  }),

  getters: {
    getServerById: (state) => (id) => state.serversById[id],
    getMetricsById: (state) => (id) => state.serverMetrics[id],
    selectedServer: (state) => state.serversById[state.selectedServerId],
    onlineServers: (state) => state.servers.filter(s => s.state === 'running'),
    totalPlayers: (state) => state.servers.reduce((sum, s) => sum + (state.serverMetrics[s.id]?.activeUsers || 0), 0),
  },

  actions: {
    async listServers() {
      this.loading = true;
      this.error = null;
      try {
        const result = await client.graphql({ query: queries.listServers });
        const serverList = result.data.listServers || [];
        
        this.servers = serverList;
        this.serversById = {};
        serverList.forEach(server => {
          this.serversById[server.id] = server;
        });
        
        return serverList;
      } catch (error) {
        this.error = parseGraphQLError(error);
        throw error;
      } finally {
        this.loading = false;
      }
    },

    subscribeToMetrics(serverId) {
      if (this.subscriptionHandles[serverId]) return;
      
      try {
        const sub = client.graphql({
          query: subscriptions.onPutServerMetric,
          variables: { id: serverId }
        }).subscribe({
          next: ({ data }) => {
            if (data?.onPutServerMetric) {
              this.serverMetrics[serverId] = {
                ...data.onPutServerMetric,
                lastUpdate: new Date()
              };
            }
          },
          error: (err) => console.error('Metrics subscription error:', err)
        });
        this.subscriptionHandles[serverId] = sub;
      } catch (e) {
        console.error('Failed to subscribe to metrics:', e);
      }
    },

    unsubscribeFromMetrics(serverId) {
      if (this.subscriptionHandles[serverId]) {
        this.subscriptionHandles[serverId].unsubscribe();
        delete this.subscriptionHandles[serverId];
      }
    },

    unsubscribeAll() {
      Object.keys(this.subscriptionHandles).forEach(id => {
        this.subscriptionHandles[id].unsubscribe();
      });
      this.subscriptionHandles = {};
    },

    async getServerConfig(serverId) {
      try {
        const result = await client.graphql({
          query: queries.getServerConfig,
          variables: { id: serverId || this.selectedServerId }
        });
        return result.data.getServerConfig;
      } catch (error) {
        this.error = parseGraphQLError(error);
        throw error;
      }
    },

    async getServerUsers(serverId) {
      try {
        const result = await client.graphql({
          query: queries.getServerUsers,
          variables: { instanceId: serverId || this.selectedServerId }
        });
        return result.data.getServerUsers || [];
      } catch (error) {
        this.error = parseGraphQLError(error);
        throw error;
      }
    },

    async getAdminUsers() {
      try {
        const result = await client.graphql({
          query: queries.getAdminUsers
        });
        return result.data.getAdminUsers || [];
      } catch (error) {
        this.error = parseGraphQLError(error);
        throw error;
      }
    },

    async getServerMetrics(serverId) {
      try {
        const result = await client.graphql({
          query: queries.getServerMetrics,
          variables: { id: serverId }
        });
        return result.data.getServerMetrics;
      } catch (error) {
        this.error = parseGraphQLError(error);
        throw error;
      }
    },

    async startServer(serverId) {
      try {
        await client.graphql({
          query: mutations.startServer,
          variables: { instanceId: serverId }
        });
      } catch (error) {
        this.error = parseGraphQLError(error);
        throw error;
      }
    },

    async stopServer(serverId) {
      try {
        await client.graphql({
          query: mutations.stopServer,
          variables: { instanceId: serverId }
        });
      } catch (error) {
        this.error = parseGraphQLError(error);
        throw error;
      }
    },

    async restartServer(serverId) {
      try {
        await client.graphql({
          query: mutations.restartServer,
          variables: { instanceId: serverId }
        });
      } catch (error) {
        this.error = parseGraphQLError(error);
        throw error;
      }
    },

    async putServerConfig(config) {
      try {
        const result = await client.graphql({
          query: mutations.putServerConfig,
          variables: { input: config }
        });
        return result.data.putServerConfig;
      } catch (error) {
        this.error = parseGraphQLError(error);
        throw error;
      }
    },

    async fixServerRole(serverId) {
      try {
        await client.graphql({
          query: mutations.fixServerRole,
          variables: { instanceId: serverId }
        });
      } catch (error) {
        this.error = parseGraphQLError(error);
        throw error;
      }
    },

    updateServerState(serverId, newState) {
      if (this.serversById[serverId]) {
        this.serversById[serverId].state = newState;
        const idx = this.servers.findIndex(s => s.id === serverId);
        if (idx !== -1) this.servers[idx].state = newState;
      }
    },

    setSelectedServer(id) {
      this.selectedServerId = id;
    }
  }
});
