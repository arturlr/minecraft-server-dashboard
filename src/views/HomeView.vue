<template>
<div>

</div>
</template>

<script>
import { mapGetters } from "vuex";

export default {
  name: "HomeView",

  data() {
    return {
      id: null
    }
  },
  computed: {
    ...mapGetters({
      isAuthenticated: "profile/isAuthenticated",
      email: "profile/email",
      fullName: "profile/fullName",
    }),
  },
  methods: {

  },
  watch: {

  },
};
</script>
