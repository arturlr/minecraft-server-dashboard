export const SET_LAYOUT = (state, payload) => {
    state.layoutName = payload;
  };

export const SET_SERVERS_LIST = (state, data) => {
  state.serversList = data;
};

export const SET_SERVERS_DICT = (state, data) => {
  state.serversDict = data;
};

export const UPDATE_SERVERS_DICT = (state, data) => {
  state.serversDict[data.id].state = data.state
  state.serversDict[data.id].launchTime = data.launchTime
  state.serversDict[data.id].publicIp = data.publicIp    
};

export const ADD_SERVER_METRIC = (state, data) => {
  console.log(data)
  state.serversDict[data.id].cpuStats = JSON.parse(data.cpuStats)
  state.serversDict[data.id].networkStats = JSON.parse(data.networkStats)
};

export const SET_LOADER = (state, isLoading) => {
  state.loading = isLoading;
};

export const SET_PAGINATION = (state, paginationToken) => {
  state.paginationToken = paginationToken;
};