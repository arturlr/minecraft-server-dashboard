<template>
  <div>
    <div class="d-flex flex-wrap align-center justify-space-between ga-4 mb-5 pb-3 border-b border-green">
      <div class="d-flex align-center ga-2">
        <span class="material-symbols-outlined text-primary">security</span>
        <h3 class="text-white text-h6 font-weight-bold">Access Control</h3>
      </div>
      <div class="d-flex ga-3">
        <v-text-field
          v-model="search"
          placeholder="Search members..."
          prepend-inner-icon="mdi-magnify"
          density="compact"
          hide-details
          bg-color="surface"
          style="width: 250px"
        />
        <v-btn color="primary" variant="tonal">
          <span class="material-symbols-outlined mr-2" style="font-size: 18px">person_add</span>
          Invite
        </v-btn>
      </div>
    </div>

    <v-card color="surface-variant" class="border-green" border="thin">
      <v-progress-linear v-if="loading" indeterminate color="primary" />
      <v-table class="bg-transparent">
        <thead>
          <tr class="bg-surface">
            <th class="text-muted text-uppercase text-caption">User</th>
            <th class="text-muted text-uppercase text-caption">Role</th>
            <th class="text-muted text-uppercase text-caption d-none d-md-table-cell">Email</th>
            <th class="text-muted text-uppercase text-caption text-right">Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="member in filteredMembers" :key="member.id" class="member-row">
            <td>
              <div class="d-flex align-center ga-3 py-2">
                <v-avatar size="36" color="primary" variant="tonal">
                  <span class="font-weight-bold">{{ (member.fullName || member.email)[0].toUpperCase() }}</span>
                </v-avatar>
                <div>
                  <p class="text-white text-body-2 font-weight-bold">{{ member.fullName || 'User' }}</p>
                  <p class="text-muted text-caption">{{ member.email }}</p>
                </div>
              </div>
            </td>
            <td>
              <v-chip color="primary" variant="tonal" size="small">Member</v-chip>
            </td>
            <td class="d-none d-md-table-cell">
              <span class="text-muted text-caption">{{ member.email }}</span>
            </td>
            <td class="text-right">
              <v-btn icon variant="text" size="small" color="secondary">
                <span class="material-symbols-outlined">more_vert</span>
              </v-btn>
            </td>
          </tr>
          <tr v-if="!loading && members.length === 0">
            <td colspan="4" class="text-center text-muted py-8">No members found</td>
          </tr>
        </tbody>
      </v-table>
    </v-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useServerStore } from '../../stores/server'

const props = defineProps({ serverId: String })

const serverStore = useServerStore()
const search = ref('')
const loading = ref(false)
const members = ref([])

const filteredMembers = computed(() => {
  if (!search.value) return members.value
  return members.value.filter(m => 
    m.email?.toLowerCase().includes(search.value.toLowerCase()) ||
    m.fullName?.toLowerCase().includes(search.value.toLowerCase())
  )
})

const loadMembers = async () => {
  if (!props.serverId) return
  loading.value = true
  try {
    members.value = await serverStore.getServerUsers(props.serverId)
  } catch (e) {
    console.error('Failed to load members:', e)
  } finally {
    loading.value = false
  }
}

onMounted(loadMembers)
</script>

<style scoped lang="scss">
.member-row:hover { background: rgba(255,255,255,0.03); }
</style>
