import Vue from 'vue'
import App from './App.vue'
import router from './router'
import store from './store'
import vuetify from './plugins/vuetify'
import Amplify, * as AmplifyModules from 'aws-amplify'
import { AmplifyPlugin } from 'aws-amplify-vue'
import aws_exports from './aws-exports'

var urlsIn = aws_exports.oauth.redirectSignIn.split(",");
var urlsOut = aws_exports.oauth.redirectSignOut.split(",");
const oauth = {
  domain: aws_exports.oauth.domain,
  scope: aws_exports.oauth.scope,
  redirectSignIn: aws_exports.oauth.redirectSignIn,
  redirectSignOut: aws_exports.oauth.redirectSignOut,
  responseType: aws_exports.oauth.responseType
};

var hasLocalhost  = (hostname) => Boolean(hostname.match(/localhost/) || hostname.match(/127(?:\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)){3}/));
var locationArr = location.hostname.split(".")
let authName = ""
if (locationArr.length >=3 ) {
   authName = 'auth.'
   for (let i = 0; i < locationArr.length; i++) { 
      authName += locationArr[i] + '.'
   }
   authName = authName.slice(0, -1); 
}

if (location.hostname === "localhost" || location.hostname === "127.0.0.1") {
  urlsIn.forEach((e) =>   { if (hasLocalhost(e)) { oauth.redirectSignIn = e; }});
  urlsOut.forEach((e) =>  { if (hasLocalhost(e)) { oauth.redirectSignOut = e; }});
}
else {
  urlsIn.forEach((e) =>   { if (!hasLocalhost(e)) { oauth.redirectSignIn = e; }});
  urlsOut.forEach((e) =>  { if (!hasLocalhost(e)) { oauth.redirectSignOut = e; }});
  oauth.domain = authName
}

var configUpdate = aws_exports;
configUpdate.oauth = oauth;

Amplify.configure(configUpdate);

Vue.use(AmplifyPlugin, AmplifyModules)

Vue.config.productionTip = false

Vue.config.productionTip = false

new Vue({
  router,
  store,
  vuetify,
  render: h => h(App)
}).$mount('#app')
