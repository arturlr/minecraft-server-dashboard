<template>
  <v-app>
    <router-view></router-view>
  </v-app>
</template>

<script>
import { components } from "aws-amplify-vue";
export default {
  name: "app",
  components: {
    ...components
  }
};
</script>