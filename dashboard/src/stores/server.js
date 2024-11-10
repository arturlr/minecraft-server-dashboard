import { defineStore } from "pinia";
import { fetchAuthSession } from 'aws-amplify/auth';
import * as mutations from "../graphql/mutations";
import * as queries from "../graphql/queries";
import { useUserStore } from "../stores/user";
import { ConsoleLogger } from 'aws-amplify/utils';
import { configAmplify } from "../configAmplify";
import { generateClient } from 'aws-amplify/api';

const logger = new ConsoleLogger('mineDash');
configAmplify();
const client = generateClient();

export const useServerStore = defineStore("server", {
    state: () => ({
        serversList: [],
        serversDict: {},
        selectedServer: {},
        monthlyUsage: {},
        loading: false,
        paginationToken: ""
    }),

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

        updateServerStateDict(server) {
            const serverAttributes = this.serversDict[server.id];
            if (serverAttributes) {
                // Servers Dictionary update state
                this.serversDict[server.id] = { 
                    ...serverAttributes, 
                    state: server.state,
                    initStatus: server.initStatus,  
                    publicIp: server.publicIp,
                    runningMinutes: server.runningMinutes        
                };

                // If selectedServer is populated, update state
                if (this.selectedServer) {
                    this.selectedServer = {
                        ...serverAttributes, 
                        state: server.state,
                        initStatus: server.initStatus,
                        publicIp: server.publicIp,
                        runningMinutes: server.runningMinutes                  
                    }
                }
                
            } else {
                console.warn(`Server with ID ${server.id} not found in serversDict`);
            }
        },

        async getServerConfig(instanceId) {
            try {
                const results = await client.graphql({
                    query: queries.getServerConfig,
                    variables: { instanceId: instanceId }
                });

                if (results.data.getServerConfig === null) {
                    console.log(`Server with ID ${instanceId} not found`);
                    return null;
                }

                return results.data.getServerConfig;

            } catch (error) {
                console.error(error);
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

