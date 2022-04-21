import Vue from 'vue'
import App from './App.vue'
import router from './router'
import store from './store'
import vuetify from './plugins/vuetify'
import Amplify, * as AmplifyModules from 'aws-amplify'
import { AmplifyPlugin } from 'aws-amplify-vue'
import aws_exports from './aws-exports'

const oauth = {
  domain: aws_exports.oauth.domain,
  scope: aws_exports.oauth.scope,
  redirectSignIn: `${window.location.origin}/`,
  redirectSignOut: `${window.location.origin}/`,
  responseType: aws_exports.oauth.responseType
};
//https://github.com/aws-amplify/amplify-cli/issues/2792

var configUpdate = aws_exports;
configUpdate.oauth = oauth;

Amplify.configure(configUpdate);

Vue.use(AmplifyPlugin, AmplifyModules)
Vue.config.productionTip = false

new Vue({
  router,
  store,
  vuetify,
  render: h => h(App)
}).$mount('#app')
