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
    metricsHistory: {},
    selectedServerId: null,
    loading: false,
    error: null,
    subscriptionHandles: {},
    stateSubscription: null
  }),

  getters: {
    getServerById: (state) => (id) => state.serversById[id],
    getMetricsById: (state) => (id) => state.serverMetrics[id],
    getMetricsHistory: (state) => (id) => state.metricsHistory[id] || { cpu: [], mem: [], net: [], players: [] },
    selectedServer: (state) => state.serversById[state.selectedServerId],
    onlineServers: (state) => state.servers.filter(s => s.state === 'running'),
    totalPlayers: (state) => {
      return state.servers.reduce((sum, s) => {
        const metrics = state.serverMetrics[s.id]
        const players = metrics?.activeUsers
        return sum + (typeof players === 'number' ? players : 0)
      }, 0)
    },
  },

  actions: {
    async ec2Discovery() {
      this.loading = true;
      this.error = null;
      try {
        const result = await client.graphql({ query: queries.ec2Discovery });
        const serverList = result.data.ec2Discovery || [];
        
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

    async fetchMetrics(serverId) {
      try {
        const result = await client.graphql({
          query: queries.ec2MetricsHandler,
          variables: { id: serverId }
        });
        const m = result.data.ec2MetricsHandler;
        if (m) {
          this.processMetrics(serverId, m);
        }
      } catch (e) {
        console.error('Failed to fetch metrics:', e);
      }
    },

    processMetrics(serverId, m) {
      // Parse stats - they come as arrays of {x, y} or JSON strings
      const parseStat = (stat) => {
        if (!stat) return []
        const arr = typeof stat === 'string' ? JSON.parse(stat) : stat
        return Array.isArray(arr) ? arr.map(p => p.y ?? p) : []
      }
      
      const cpuValues = parseStat(m.cpuStats)
      const memValues = parseStat(m.memStats)
      const netValues = parseStat(m.networkStats)
      
      console.log('Processing metrics for', serverId, { cpuValues, memValues, netValues, activeUsers: m.activeUsers })
      
      // Get latest value for current metrics
      const latestCpu = cpuValues.length ? cpuValues[cpuValues.length - 1] : 0
      const latestMem = memValues.length ? memValues[memValues.length - 1] : 0
      
      this.serverMetrics = {
        ...this.serverMetrics,
        [serverId]: { 
          ...m, 
          cpuStats: latestCpu,
          memStats: latestMem,
          activeUsers: typeof m.activeUsers === 'number' ? m.activeUsers : 0,
          lastUpdate: new Date() 
        }
      }
      
      // Update history - only add if we have new values
      const oldHistory = this.metricsHistory[serverId] || { cpu: [], mem: [], net: [], players: [] }
      
      if (cpuValues.length > 0 || memValues.length > 0 || netValues.length > 0) {
        this.metricsHistory = {
          ...this.metricsHistory,
          [serverId]: {
            cpu: [...oldHistory.cpu, ...cpuValues].slice(-30),
            mem: [...oldHistory.mem, ...memValues].slice(-30),
            net: [...oldHistory.net, ...netValues].slice(-30),
            players: [...oldHistory.players, m.activeUsers || 0].slice(-30)
          }
        }
      }
      
      console.log('Updated history for', serverId, this.metricsHistory[serverId])
    },

    subscribeToMetrics(serverId) {
      if (this.subscriptionHandles[serverId]) return;
      
      // Initialize history
      if (!this.metricsHistory[serverId]) {
        this.metricsHistory[serverId] = { cpu: [], mem: [], net: [], players: [] }
      }
      
      // Fetch initial metrics
      this.fetchMetrics(serverId)
      
      try {
        const sub = client.graphql({
          query: subscriptions.onPutServerMetric,
          variables: { id: serverId }
        }).subscribe({
          next: ({ data }) => {
            if (data?.onPutServerMetric) {
              this.processMetrics(serverId, data.onPutServerMetric)
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
      if (this.stateSubscription) {
        this.stateSubscription.unsubscribe();
        this.stateSubscription = null;
      }
    },

    subscribeToStateChanges() {
      if (this.stateSubscription) return;
      
      try {
        this.stateSubscription = client.graphql({
          query: subscriptions.onChangeState
        }).subscribe({
          next: ({ data }) => {
            if (data?.onChangeState) {
              const updated = data.onChangeState;
              // Update server in state
              if (this.serversById[updated.id]) {
                this.serversById = {
                  ...this.serversById,
                  [updated.id]: { ...this.serversById[updated.id], ...updated }
                };
                // Update servers array
                const idx = this.servers.findIndex(s => s.id === updated.id);
                if (idx !== -1) {
                  this.servers = [
                    ...this.servers.slice(0, idx),
                    { ...this.servers[idx], ...updated },
                    ...this.servers.slice(idx + 1)
                  ];
                }
              }
            }
          },
          error: (err) => console.error('State subscription error:', err)
        });
      } catch (e) {
        console.error('Failed to subscribe to state changes:', e);
      }
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

    async ec2MetricsHandler(serverId) {
      try {
        const result = await client.graphql({
          query: queries.ec2MetricsHandler,
          variables: { id: serverId }
        });
        return result.data.ec2MetricsHandler;
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

    async iamProfileManager(serverId) {
      try {
        await client.graphql({
          query: mutations.iamProfileManager,
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
