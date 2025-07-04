import { defineStore } from "pinia";
import { fetchAuthSession } from 'aws-amplify/auth';
import * as mutations from "../graphql/mutations";
import * as queries from "../graphql/queries";
import { useUserStore } from "../stores/user";
import { ConsoleLogger } from 'aws-amplify/utils';
import { configAmplify } from "../configAmplify";
import { generateClient, get } from 'aws-amplify/api';

const logger = new ConsoleLogger('mineDash');
configAmplify();
const client = generateClient();

export const useServerStore = defineStore("server", {
    state: () => ({
        serversList: [],
        serversDict: {},
        selectedServerId: null,
        monthlyUsage: {},
        loading: false,
        paginationToken: ""
    }),

    getters: {
        getServerById: (state) => (id) => state.serversDict[id],
        getServerName: (state) => {
            const selectedServer = state.serversDict[state.selectedServerId];
            if (selectedServer?.name && selectedServer.name.length > 2) {
                return selectedServer.name;
            }
            return selectedServer?.id;
        },
        isServerIamCompliant: (state) => {
            const selectedServer = state.serversDict[state.selectedServerId];            
            return selectedServer?.iamStatus === 'ok';
        },
        getServerState: (state) => (id) => state.serversDict[id]?.state,
        getServerStateColor: (state) => {
            const serverState = state.serversDict[state.selectedServerId]?.state;
            switch(serverState) {
                case 'running': return 'success'
                case 'stopped': return 'error'
                default: return 'warning'
            }
        },
        getRunningServers: (state) => 
            Object.values(state.serversDict).filter(server => server.state === 'running')
    },

    actions: {
        async listServers() {
            try {
                console.group("listServers");

                this.loading = true

                const results = await client.graphql({
                    query: queries.listServers
                });

                if (results.data.listServers === null || results.data.listServers.length === 0) {
                    console.warn("No servers found");
                    console.groupEnd();
                    this.loading = false
                    return [];
                }

                // Populating serversDict
                this.serversDict = {};
                results.data.listServers.forEach(({ id, name, memSize, diskSize, vCpus, state, initStatus, iamStatus, publicIp, launchTime, runningMinutes, groupMembers }) => {
                    this.serversDict[id] = { id, name, memSize, diskSize, vCpus, state, initStatus, iamStatus, publicIp, launchTime, runningMinutes, groupMembers };
                });

                console.groupEnd();
                this.loading = false
                return results.data.listServers;

            } catch (error) {
                console.error(error);
                this.loading = false
                console.groupEnd();
                throw error;
            }
        },

        updateServer(server) {
            if (server.id) {
                //console.log('Before update:', this.serversDict[server.id]);
                //console.log('Update payload:', server);
                
                this.serversDict[server.id] = 
                {   ...this.serversDict[server.id],
                    state: server.state,
                    initStatus: server.initStatus,
                    publicIp: server.publicIp,
                    runningMinutes: server.runningMinutes  
                 }
            };                
                //console.log('After update:', this.serversDict[server.id]);
        },
                
        setSelectedServerId(id) {
            console.log("setSelectedServerId", id);
            this.selectedServerId = id;
          },

        async getServerConfig() {
            console.group("getServerConfig");
            try {
                const results = await client.graphql({
                    query: queries.getServerConfig,
                    variables: { id: this.selectedServerId }
                });

                if (results.data.getServerConfig === null) {
                    console.log(`Server with ID ${this.selectedServerId} not found`);
                    return null;
                }

                console.groupEnd();
                return results.data.getServerConfig;

            } catch (error) {
                console.error(error);
                console.groupEnd();
                throw error;
            }
        },

        async getServerUsers(instanceId) {
            console.group("getServerUsers");
            try {
                const results = await client.graphql({
                    query: queries.getServerUsers,
                    variables: { instanceId: instanceId || this.selectedServerId }
                });

                if (results.data.getServerUsers === null) {
                    console.log(`No users found for server ${instanceId || this.selectedServerId}`);
                    return [];
                }

                console.groupEnd();
                return results.data.getServerUsers;

            } catch (error) {
                console.error(error);
                console.groupEnd();
                throw error;
            }
        },

        async putServerConfig(input) {
            try {
                console.log(input);
                const results = await client.graphql({
                    query: mutations.putServerConfig,
                    variables: { input: input }
                });

                if (results.data.putServerConfig === null) {
                    console.log(results);
                    return null;
                }

                return results.data.putServerConfig;

            } catch (error) {
                console.error(error);
                throw error;
            }
        },

        async verifyEmail(code, email) {
            const verifyEmailQuery = `
              mutation VerifyUserEmail($code: String!) {
                verifyUserEmail(id: $code) 
              }
            `
            
            try {
                const results = await client.graphql({
                    query: verifyEmailQuery,
                    variables: { code: code }
                });

                if (results.data.verifyUserEmail) {
                    const record = JSON.parse(results.data.verifyUserEmail);
                    if (record.inviteeEmail == email)
                        return true                    
                }
                return false
            } catch (err) {
              this.message = 'Error verifying email'
              console.error('error verifying email', err) 
              return false
            }
          },

        async getLogAudit(id) {
            try {
                const results = await client.graphql({
                    query: queries.getLogAudit,
                    variables: { id: id }
                });

                if (results.data.getLogAudit === null) {
                    console.log(results.data.getLogAudit);
                    return null;
                }

                return results.data.getLogAudit;

            } catch (error) {
                console.error(error);
                throw error;
            }
        },

        async putLogAudit(input) {
            let results = null;
            try {
                if (input.inviteeEmail) {
                    results = await client.graphql({
                        query: mutations.PutLogAuditWithInviteeEmail,
                        variables: { input: input }
                    });
                }
                else {
                    results = await client.graphql({
                        query: mutations.PutLogAudit,
                        variables: { input: input }
                    });
                }

                if (results.data.putLogAudit === null) {
                    return null;
                }

                return results.data.putLogAudit;

            } catch (error) {
                console.error(error);
                throw error;
            }
        },
    }

})

