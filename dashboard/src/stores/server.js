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

                const results = await client.graphql({
                    query: queries.listServers
                });

                console.log(results.data.listServers);

                if (results.data.listServers.length == 0) {
                    console.log("No servers found");
                    console.groupEnd();
                    return [];
                }

                this.serversList = results.data.listServers;

                for (let i = 0; i < results.data.listServers.length; i++) {
                    this.serversDict[results.data.listServers[i].id] = {}
                    this.serversDict[results.data.listServers[i].id].id = results.data.listServers[i].id
                    this.serversDict[results.data.listServers[i].id].name = results.data.listServers[i].name
                    this.serversDict[results.data.listServers[i].id].memSize = results.data.listServers[i].memSize
                    this.serversDict[results.data.listServers[i].id].diskSize = results.data.listServers[i].diskSize
                    this.serversDict[results.data.listServers[i].id].vCpus = results.data.listServers[i].vCpus
                    this.serversDict[results.data.listServers[i].id].state = results.data.listServers[i].state
                    this.serversDict[results.data.listServers[i].id].initStatus = results.data.listServers[i].initStatus
                    this.serversDict[results.data.listServers[i].id].iamStatus = results.data.listServers[i].iamStatus
                    this.serversDict[results.data.listServers[i].id].publicIp = results.data.listServers[i].publicIp
                    this.serversDict[results.data.listServers[i].id].launchTime = results.data.listServers[i].launchTime
                    this.serversDict[results.data.listServers[i].id].runningMinutes = results.data.listServers[i].runningMinutes
                    this.serversDict[results.data.listServers[i].id].groupMembers = results.data.listServers[i].groupMembers 
                }

                console.groupEnd();
                return results.data.listServers;

            } catch (error) {
                console.error(error);
                console.groupEnd();
                throw error;
            }
        }

    }

})

