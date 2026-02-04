<template>
  <div>
    <div class="section-header">
      <span class="material-symbols-outlined">security</span>
      <h3>Access Control</h3>
      <div class="header-actions">
        <v-text-field
          v-model="search"
          placeholder="Search..."
          density="compact"
          variant="outlined"
          hide-details
          style="width: 200px"
        />
        <v-btn variant="outlined" size="small">
          <span class="material-symbols-outlined" style="font-size: 18px">person_add</span>
        </v-btn>
      </div>
    </div>

    <div class="members-table">
      <v-progress-linear v-if="loading" indeterminate color="#171717" />
      <table>
        <thead>
          <tr>
            <th>User</th>
            <th>Role</th>
            <th>Email</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="member in filteredMembers" :key="member.id">
            <td>
              <div class="user-cell">
                <div class="user-avatar">{{ (member.fullName || member.email)[0].toUpperCase() }}</div>
                <div>
                  <div class="user-name">{{ member.fullName || 'User' }}</div>
                  <div class="user-email">{{ member.email }}</div>
                </div>
              </div>
            </td>
            <td>
              <span class="role-badge">Member</span>
            </td>
            <td class="email-col">{{ member.email }}</td>
            <td class="actions-col">
              <v-btn icon variant="text" size="small">
                <span class="material-symbols-outlined">more_vert</span>
              </v-btn>
            </td>
          </tr>
          <tr v-if="!loading && members.length === 0">
            <td colspan="4" class="empty-state">No members found</td>
          </tr>
        </tbody>
      </table>
    </div>
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

<style scoped>
.section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px solid #e5e5e5;
}
.section-header .material-symbols-outlined {
  font-size: 20px;
  color: #171717;
}
.section-header h3 {
  font-size: 16px;
  font-weight: 500;
  color: #171717;
  margin: 0;
  flex: 1;
}
.header-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}
.members-table {
  border: 1px solid #e5e5e5;
  border-radius: 8px;
  overflow: hidden;
}
.members-table table {
  width: 100%;
  border-collapse: collapse;
}
.members-table th {
  text-align: left;
  padding: 12px 16px;
  font-size: 11px;
  font-weight: 500;
  color: #a3a3a3;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  background: #fafafa;
  border-bottom: 1px solid #e5e5e5;
}
.members-table td {
  padding: 12px 16px;
  border-bottom: 1px solid #f5f5f5;
}
.members-table tbody tr:last-child td {
  border-bottom: none;
}
.members-table tbody tr:hover {
  background: #fafafa;
}
.user-cell {
  display: flex;
  align-items: center;
  gap: 12px;
}
.user-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: #171717;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 500;
  font-size: 14px;
}
.user-name {
  font-size: 14px;
  font-weight: 500;
  color: #171717;
}
.user-email {
  font-size: 12px;
  color: #737373;
}
.role-badge {
  display: inline-block;
  padding: 4px 12px;
  background: #f5f5f5;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
  color: #171717;
}
.email-col {
  color: #737373;
  font-size: 13px;
}
.actions-col {
  text-align: right;
}
.empty-state {
  text-align: center;
  padding: 48px 16px !important;
  color: #a3a3a3;
  font-size: 13px;
}
</style>
