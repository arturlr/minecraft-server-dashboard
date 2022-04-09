/**
 * Profile [Vuex Module getter](https://vuex.vuejs.org/guide/getters.html) - isAuthenticated
 * @param {object} state - Profile state
 * @returns {boolean} - Whether current user is authenticated
 * @see {@link getSession} for more information on action that calls isAuthenticated
 */
export const isAuthenticated = state => {
  console.log("isAuthenticated: " + !!state.user);
  return !!state.user;
};

export const userId = state => {
  return (
    (state.user &&
      state.user.attributes &&
      state.user.attributes.sub) ||
    "no userid"
  );
};

export const email = state => {
  return (
    (state.user &&
      state.user.attributes &&
      state.user.attributes.email) ||
    "no email"
  );
};

export const fullName = state => {
  return (
    (state.user &&
      state.user.attributes &&
      state.user.attributes.given_name + ' ' + state.user.attributes.family_name) ||
    "no email"
  );
};

export const userAttributes = state => {
  return (state.user && state.user.attributes) || "no attributes";
};

export const hasIpAddress = state => {
  console.log("ipaddress: " + !!state.clientIp);
  return !!state.clientIp;
};