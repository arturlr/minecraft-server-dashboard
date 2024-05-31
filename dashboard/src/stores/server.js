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
        }

    }

})

