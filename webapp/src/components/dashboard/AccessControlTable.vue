<template>
  <v-card color="surface" class="border-green" border="thin">
    <v-table class="bg-transparent">
      <thead>
        <tr class="bg-surface-variant">
          <th class="text-muted text-uppercase text-caption">User</th>
          <th class="text-muted text-uppercase text-caption">Role</th>
          <th class="text-muted text-uppercase text-caption d-none d-md-table-cell">Last Active</th>
          <th class="text-muted text-uppercase text-caption text-right">Actions</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="user in users" :key="user.email" class="user-row">
          <td>
            <div class="d-flex align-center ga-3 py-2">
              <v-avatar size="36" :color="user.color" variant="tonal">
                <span class="font-weight-bold">{{ user.name[0] }}</span>
              </v-avatar>
              <div>
                <p class="text-white text-body-2 font-weight-bold">{{ user.name }}</p>
                <p class="text-muted text-caption">{{ user.email }}</p>
              </div>
            </div>
          </td>
          <td>
            <v-chip :color="roleColor(user.role)" variant="tonal" size="small" class="font-weight-medium">
              <span v-if="user.role === 'Administrator'" class="role-dot" />
              {{ user.role }}
            </v-chip>
          </td>
          <td class="text-muted text-caption font-mono d-none d-md-table-cell">{{ user.lastActive }}</td>
          <td class="text-right">
            <v-btn icon variant="text" size="small" color="secondary">
              <span class="material-symbols-outlined">more_vert</span>
            </v-btn>
          </td>
        </tr>
      </tbody>
    </v-table>
  </v-card>
</template>

<script setup>
defineProps({
  users: { type: Array, default: () => [] }
})

const roleColor = (role) => {
  const colors = { Administrator: 'primary', Moderator: 'purple', Viewer: 'blue' }
  return colors[role] || 'grey'
}
</script>

<style scoped lang="scss">
.user-row:hover { background: rgba(255,255,255,0.03); }
.role-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
  margin-right: 6px;
}
.font-mono { font-family: monospace; }
</style>
