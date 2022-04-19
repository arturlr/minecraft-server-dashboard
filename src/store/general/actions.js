import { API, graphqlOperation } from "aws-amplify";
import { listServers, getMonthlyCost } from "../../graphql/queries";

export async function createServersList(
  { commit }) {
  try {
      let servers_list = [];
      let servers_dict = {}
      console.group("store/general/actions/createServersList");
      commit("SET_LOADER", true);
      commit("SET_SERVERS_LIST", []);

      const {
          // @ts-ignore
          data: { listServers: results } 
      } = await API.graphql(graphqlOperation(listServers));
      servers_list = results

      for (let i = 0; i < servers_list.length; i++ ) {
        servers_dict[servers_list[i].id] = {}
        servers_dict[servers_list[i].id].name = servers_list[i].name
        servers_dict[servers_list[i].id].memSize = servers_list[i].memSize
        servers_dict[servers_list[i].id].diskSize = servers_list[i].diskSize
        servers_dict[servers_list[i].id].vCpus = servers_list[i].vCpus
        servers_dict[servers_list[i].id].state = servers_list[i].state
        servers_dict[servers_list[i].id].publicIp = servers_list[i].publicIp
        servers_dict[servers_list[i].id].launchTime = servers_list[i].launchTime
        servers_dict[servers_list[i].id].runCommand = servers_list[i].runCommand
        servers_dict[servers_list[i].id].workingDir = servers_list[i].workingDir
    }
      commit("SET_SERVERS_DICT", servers_dict);
      commit("SET_SERVERS_LIST", servers_list);
      commit("SET_LOADER", false);
      console.groupEnd();
  } catch (error) {
      console.error(error);
      commit("SET_LOADER", false);
      console.groupEnd();
      throw error;
  }
}

export function addServerStats(
  { commit }, { metric}) {
    console.group("store/general/actions/addServerStats");  
    console.log('metrics for: ' + metric.id) 
    commit("ADD_SERVER_METRIC", metric);
    console.groupEnd();
}

export function upadateServersList(
  { commit }, { serverData }) {
    commit("SET_LOADER", true);
    console.group("store/general/actions/upadateServersList");
    console.log(serverData.id + 'state changed to ' + serverData.state)
    commit("UPDATE_SERVERS_DICT", serverData);
    commit("SET_LOADER", false);
    console.groupEnd();
}

export function saveLayout({ commit },
    { name }) {
      console.group("store/layout/actions/saveLayout");
      commit("SET_LAYOUT", name);
    }

export async function getCostUsage({ commit }) {
    console.group("store/layout/actions/getCostUsage");
    commit("SET_COST_USAGE", {});

    const {
        // @ts-ignore
        data: { getMonthlyCost: results } 
    } = await API.graphql(graphqlOperation(getMonthlyCost));

    commit("SET_COST_USAGE", results);
  }