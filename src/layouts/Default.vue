<template>
  <div>
    <v-app-bar dense dark>
      <v-spacer></v-spacer>
      <v-toolbar-title>Gecko-Hosting</v-toolbar-title>
      <v-spacer></v-spacer>
    </v-app-bar>
    
    <v-main>
      <v-container>
        <v-layout row>
        <v-flex md-4>
          <virtual-rack />
        </v-flex>
        <v-flex md-8>
          <router-view></router-view>
        </v-flex>
        </v-layout>
      </v-container>
    </v-main>
  </div>
</template>
<script>
import VirtualRack from "../components/VirtualRack.vue"

export default {
  name: "DefaultLayout",
  components: {
    VirtualRack
  },
  data: () => ({
    
  }),
};
</script>

