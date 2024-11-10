<script setup>
import { onMounted, onUnmounted, ref } from "vue"
import { Hub, ConsoleLogger } from "aws-amplify/utils";
import { signInWithRedirect, getCurrentUser } from "aws-amplify/auth";
// import { useRouter } from 'vue-router'

// const router = useRouter();
const loginError = ref(null);

const logger = new ConsoleLogger('mineDash');

const signInWithGoogle = () => {
  signInWithRedirect({ provider: 'Google' });
};

const listener = async ({ payload }) => {
    console.log("Auth listener: " + payload.event);
    switch (payload.event) {
        case "signInWithRedirect":
            console.log("Sign in success with token: " + payload.data);
            const user = await getCurrentUser();
            console.log(user.username);
            break;
        case "signInWithRedirect_failure":
            // handle sign in failure
            console.error(payload.data)
            loginError.value = payload.data;
            break;
        case "customOAuthState":
            const state = payload.data; // this will be customState provided on signInWithRedirect function
            console.log(state);
            break;
    }
};

onMounted(() => {
    Hub.listen("auth", listener);
});

onUnmounted(() => {
  const cleanup = Hub.listen('auth', listener);
  cleanup()
});

</script>

<template>
    <v-container fill-height fluid>
        <v-card class="mx-auto" elevation="1" max-width="500">
            <v-card-title class="py-5 font-weight-black">Minecraft Dashboard by GeckoByte</v-card-title>

            <v-card-text>This application requires you to login using your Google Account.</v-card-text>

            <v-btn append-icon="mdi-google" class="text-none mb-4" color="deep-orange-darken-4" size="x-large" variant="flat"
                block @click="signInWithGoogle">
                Sign in with Google
                <template v-slot:append>
                    <v-icon color="white"></v-icon>
                </template>
            </v-btn>

            <v-card-text>
                {{ loginError }}
            </v-card-text>
        </v-card>
    </v-container>
</template>
