import { API, graphqlOperation } from "aws-amplify";
import { Auth } from "aws-amplify";
import axios from 'axios'
import { createLoginAudit } from "../../graphql/mutations";
//import { listLoginAudits } from "../../graphql/queries";

export async function getSession({ commit, getters }) {
  console.group("store/profile/actions/getSession");
  console.log("Fetching current session");
  try {
    const user = await Auth.currentAuthenticatedUser();
    commit("SET_USER", user);
    console.groupEnd();
  } catch (err) {
    console.error(err);
    if (getters.isAuthenticated) {
      commit("SET_USER");
      console.groupEnd();
    }
    throw new Error(err);
  }
}

export async function getIpAddress({ commit }) {  
    console.log("profile/getIpAddress");
    await axios.get('https://api.ipify.org?format=json').then((x) => { 
      commit("SET_CLIENT_IP", x.data["ip"]);         
    }).catch((error) => {
      console.error(error);
      commit("SET_CLIENT_IP", "ERROR_IP");
    });
}

export async function saveAuditLogin({ commit },
  { email, action, timestamp, expirationEpoch }) {
  try {
      commit("SET_LOADER", true);
      console.group("store/general/actions/saveagent");
      let result = "";

      var inputAgentLogin = {
          email: email,
          action: action,
          timestamp: timestamp,
          expirationEpoch: expirationEpoch
      }

      const {
          // @ts-ignore
          data: { createDeliveryAgent: auditObj }
      } = await API.graphql(graphqlOperation(createLoginAudit, {
          input: inputAgentLogin
      }));
      result = auditObj
      console.log(result);
      console.groupEnd(); 
      commit("SET_LOADER", false);
      return result;
  } catch (error) {
      console.error(error);
      console.groupEnd();
      commit("SET_LOADER", false);
      throw error;
  }
}