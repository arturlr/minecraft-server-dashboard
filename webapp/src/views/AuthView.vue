<template>
  <v-container class="fill-height" fluid>
    <v-row align="center" justify="center">
      <v-col cols="12" sm="8" md="5" lg="4">
        <v-card color="surface" class="border-green pa-8" border="thin">
          <!-- Logo -->
          <div class="d-flex align-center ga-3 mb-6">
            <div class="d-flex align-center justify-center rounded-lg pa-3" style="background: rgba(19,236,91,0.2)">
              <span class="material-symbols-outlined text-primary" style="font-size: 32px">dns</span>
            </div>
            <div>
              <h1 class="text-white text-h5 font-weight-bold">BlockNode</h1>
              <p class="text-muted text-caption">Server Dashboard</p>
            </div>
          </div>

          <v-divider class="border-green mb-6" />

          <p class="text-muted text-body-2 mb-6">
            Sign in with your Google account to manage your Minecraft servers.
          </p>

          <v-btn 
            block 
            size="large" 
            color="white"
            class="mb-4"
            :loading="loading"
            @click="signInWithGoogle"
          >
            <v-icon start>mdi-google</v-icon>
            Sign in with Google
          </v-btn>

          <v-alert v-if="error" type="error" variant="tonal" density="compact" class="mt-4">
            {{ error }}
          </v-alert>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { Hub } from 'aws-amplify/utils'
import { signInWithRedirect } from 'aws-amplify/auth'

const loading = ref(false)
const error = ref(null)

const signInWithGoogle = () => {
  loading.value = true
  error.value = null
  signInWithRedirect({ provider: 'Google' })
}

const listener = ({ payload }) => {
  if (payload.event === 'signInWithRedirect_failure') {
    error.value = payload.data?.message || 'Sign in failed'
    loading.value = false
  }
}

onMounted(() => Hub.listen('auth', listener))
onUnmounted(() => Hub.listen('auth', listener)())
</script>
