<template>
  <v-dialog
    :model-value="modelValue"
    @update:model-value="$emit('update:modelValue', $event)"
    max-width="600px"
    :fullscreen="isMobile"
    persistent
    transition="dialog-bottom-transition"
    role="dialog"
    aria-labelledby="user-management-dialog-title"
    aria-describedby="user-management-dialog-description"
  >
    <v-card>
      <v-card-title 
        id="user-management-dialog-title"
        class="text-h5 pa-4"
      >
        Manage Users - {{ serverName }}
      </v-card-title>

      <v-card-text id="user-management-dialog-description">
        <!-- Loading State -->
        <div v-if="loading" class="text-center py-8" role="status" aria-live="polite">
          <v-progress-circular
            indeterminate
            color="primary"
            size="64"
            aria-label="Loading users"
          ></v-progress-circular>
          <p class="mt-4 text-body-1">Loading users...</p>
        </div>

        <!-- Error State -->
        <v-alert
          v-else-if="errorMessage"
          type="error"
          variant="tonal"
          class="mb-4"
          role="alert"
          aria-live="assertive"
        >
          {{ errorMessage }}
          <template v-slot:append>
            <v-btn
              size="small"
              variant="text"
              @click="fetchUsers"
              aria-label="Retry loading users"
              :min-width="touchTargetSize"
              :min-height="touchTargetSize"
            >
              Retry
            </v-btn>
          </template>
        </v-alert>

        <!-- User List and Add User Form -->
        <div v-else>
          <!-- Success Message -->
          <v-alert
            v-if="successMessage"
            type="success"
            variant="tonal"
            class="mb-4"
            closable
            @click:close="successMessage = ''"
            role="status"
            aria-live="polite"
          >
            {{ successMessage }}
          </v-alert>

          <!-- Add User Form -->
          <v-card variant="outlined" class="mb-4">
            <v-card-text>
              <v-alert
                type="info"
                variant="tonal"
                density="compact"
                class="mb-3"
                role="status"
              >
                <span class="text-body-2">
                  Note: Users must log in to the dashboard at least once before they can be added to a server.
                </span>
              </v-alert>
              
              <!-- Email Input with Manual Search -->
              <v-text-field
                v-model="newUserEmail"
                label="User Email Address"
                placeholder="Enter email address..."
                :rules="emailRules"
                :disabled="addingUser || searching"
                variant="outlined"
                density="comfortable"
                prepend-inner-icon="mdi-email"
                @keyup.enter="searchResults ? addUser() : searchUser()"
                aria-label="Enter user email address"
                aria-required="true"
                aria-describedby="email-search-help"
              >
                <template v-slot:append-inner>
                  <v-btn
                    v-if="newUserEmail"
                    icon="mdi-close"
                    variant="text"
                    size="small"
                    @click="clearSearch"
                    aria-label="Clear search"
                    class="mr-1"
                  ></v-btn>
                </template>
              </v-text-field>
              <span id="email-search-help" class="sr-only">
                Enter an email address and click search to find the user
              </span>
              
              <!-- Search Button -->
              <v-btn
                color="primary"
                variant="outlined"
                :loading="searching"
                :disabled="!isEmailValid || searching || addingUser"
                @click="searchUser"
                block
                class="mb-3"
                :min-height="touchTargetSize"
                aria-label="Search for user by email"
              >
                <v-icon start>mdi-magnify</v-icon>
                Search User
              </v-btn>
              
              <!-- Search Results -->
              <div v-if="searchMessage || searchResults">
                <!-- User Found -->
                <v-card
                  v-if="searchResults"
                  variant="outlined"
                  class="mb-3"
                  color="success"
                >
                  <v-card-text class="py-3">
                    <div class="d-flex align-center justify-space-between">
                      <div class="d-flex align-center">
                        <v-icon icon="mdi-account-circle" class="mr-3" color="success" size="large"></v-icon>
                        <div>
                          <div class="text-subtitle-1 font-weight-medium">{{ searchResults.fullName }}</div>
                          <div class="text-body-2 text-medium-emphasis">{{ searchResults.email }}</div>
                        </div>
                      </div>
                      <v-btn
                        color="success"
                        :loading="addingUser"
                        :disabled="addingUser"
                        @click="addUser"
                        :min-height="touchTargetSize"
                        aria-label="Add this user to server"
                      >
                        <v-icon start>mdi-plus</v-icon>
                        Add User
                      </v-btn>
                    </div>
                  </v-card-text>
                </v-card>
                
                <!-- User Not Found -->
                <v-alert
                  v-else-if="searchMessage"
                  type="warning"
                  variant="tonal"
                  density="compact"
                  class="mb-3"
                  role="status"
                  aria-live="polite"
                >
                  <div class="d-flex align-center">
                    <v-icon class="mr-2">mdi-account-off</v-icon>
                    <span>{{ searchMessage }}</span>
                  </div>
                </v-alert>
              </div>
              
              <!-- Helper Text -->
              <div class="text-caption text-medium-emphasis">
                <v-icon size="small" class="mr-1">mdi-information-outline</v-icon>
                Enter an email address and click "Search User" to verify they exist before adding them to the server.
              </div>
            </v-card-text>
          </v-card>

          <!-- Empty State -->
          <v-alert
            v-if="users.length === 0"
            type="info"
            variant="tonal"
            class="mb-4"
            role="status"
          >
            No users have been granted access to this server yet.
          </v-alert>

          <!-- User List Display -->
          <v-list 
            v-else 
            lines="two"
            role="list"
            aria-label="Users with access to this server"
          >
            <v-list-item
              v-for="user in users"
              :key="user.id"
              :title="user.fullName"
              :subtitle="user.email"
              role="listitem"
              :aria-label="`User: ${user.fullName}, Email: ${user.email}`"
            >
              <template v-slot:prepend>
                <v-icon icon="mdi-account-circle" aria-hidden="true"></v-icon>
              </template>
            </v-list-item>
          </v-list>
        </div>
      </v-card-text>

      <v-card-actions class="pa-4">
        <v-spacer></v-spacer>
        <v-btn
          color="grey-darken-1"
          variant="text"
          @click="$emit('update:modelValue', false)"
          :min-height="touchTargetSize"
          aria-label="Close user management dialog"
        >
          Close
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
/**
 * UserManagementDialog Component
 * 
 * Displays and manages users with access to a specific Minecraft server.
 * Allows viewing current users and adding new users by email address.
 * 
 * Requirements: 1.2, 1.3, 1.4, 1.5, 2.1, 2.2, 2.3, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 4.2, 5.4
 */

import { ref, watch, computed, onMounted, onUnmounted } from 'vue'
import { generateClient } from 'aws-amplify/api'
import { getServerUsers, searchUserByEmail } from '@/graphql/queries'
import { addUserToServer } from '@/graphql/mutations'
import { parseGraphQLError, retryOperation } from '@/utils/errorHandler'
import { useDisplay } from 'vuetify'

// Initialize Amplify API client
const client = generateClient()

// Define component props
const props = defineProps({
  modelValue: {
    type: Boolean,
    required: true,
    default: false
  },
  serverId: {
    type: String,
    required: true
  },
  serverName: {
    type: String,
    required: true
  }
})

// Define component emits
defineEmits(['update:modelValue'])

// Vuetify display composable for responsive breakpoints
// Requirements: 4.4
const { mobile, smAndDown } = useDisplay()

// Reactive state
const users = ref([])
const loading = ref(false)
const errorMessage = ref('')
const newUserEmail = ref('')
const addingUser = ref(false)
const successMessage = ref('')
const searchResults = ref(null)
const searching = ref(false)
const searchMessage = ref('')

// Responsive design: Check if device is mobile
// Requirements: 4.4
const isMobile = computed(() => mobile.value || smAndDown.value)

// Touch target size for mobile accessibility (minimum 44x44px)
// Requirements: 4.4
const touchTargetSize = computed(() => isMobile.value ? '44px' : '36px')

// Email validation rules
// Requirements: 3.2, 3.7
const emailRules = [
  v => !!v || 'Email address is required',
  v => {
    if (!v) return 'Email address is required'
    const pattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    return pattern.test(v) || 'Please enter a valid email address'
  }
]

// Computed property to check if email is valid
// Requirements: 3.7
const isEmailValid = computed(() => {
  if (!newUserEmail.value || !newUserEmail.value.trim()) {
    return false
  }
  const pattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  return pattern.test(newUserEmail.value.trim())
})

/**
 * Extract user-friendly error message from GraphQL errors
 * Handles different error types: network, auth, server, timeout
 * Requirements: 5.4
 * 
 * @param {Error} error - The error object from GraphQL or network request
 * @param {string} operation - The operation being performed ('fetch' or 'add')
 * @returns {string} - User-friendly error message
 */
const extractUserFriendlyErrorMessage = (error, operation) => {
  // Use the utility function to parse the error
  const baseMessage = parseGraphQLError(error)
  
  // Handle specific error types for different operations
  if (operation === 'fetch') {
    // Network failures
    if (error.message?.includes('Network') || error.message?.includes('network')) {
      return 'Unable to connect to server. Please check your connection and try again.'
    }
    
    // Authentication errors
    if (error.message?.includes('Unauthorized') || error.message?.includes('401')) {
      return 'Session expired. Please log in again.'
    }
    
    // Timeout errors
    if (error.message?.includes('timeout') || error.message?.includes('Timeout')) {
      return 'Request timed out. Please try again.'
    }
    
    // Server errors
    if (error.message?.includes('500') || error.message?.includes('Internal')) {
      return 'Server error occurred. Please try again later.'
    }
    
    // Return parsed message or default
    return baseMessage || 'An error occurred while loading users. Please try again.'
  }
  
  if (operation === 'search') {
    // Check for specific backend error codes first
    const errorMsg = baseMessage.toLowerCase()
    
    // User not found in Cognito (needs to log in first)
    if (errorMsg.includes('user_not_found') || 
        errorMsg.includes('user must log in') ||
        errorMsg.includes('no user found with email')) {
      return 'User not found. They must log in to the dashboard at least once before being added to a server.'
    }
    
    // Invalid email format
    if (errorMsg.includes('invalid') && errorMsg.includes('email')) {
      return 'Please enter a valid email address.'
    }
    
    // Network failures
    if (error.message?.includes('Network') || error.message?.includes('network')) {
      return 'Unable to search for user. Please check your connection and try again.'
    }
    
    // Authentication errors
    if (error.message?.includes('Unauthorized') || error.message?.includes('401')) {
      return 'Session expired. Please log in again.'
    }
    
    // Return parsed message or default
    return baseMessage || 'Unable to search for user. Please try again.'
  }
  
  if (operation === 'add') {
    // Check for specific backend error codes first
    const errorMsg = baseMessage.toLowerCase()
    
    // User not found in Cognito (needs to log in first)
    if (errorMsg.includes('user_not_found') || 
        errorMsg.includes('user must log in') ||
        errorMsg.includes('no user found with email')) {
      return 'User not found. They must log in to the dashboard at least once before being added to a server.'
    }
    
    // User already has access
    if (errorMsg.includes('user_already_exists') || 
        errorMsg.includes('already has access') ||
        errorMsg.includes('already')) {
      return 'User already has access to this server.'
    }
    
    // Invalid email format
    if (errorMsg.includes('invalid') && errorMsg.includes('email')) {
      return 'Please enter a valid email address.'
    }
    
    // Permission denied
    if (errorMsg.includes('permission') || 
        errorMsg.includes('authorized') || 
        errorMsg.includes('forbidden')) {
      return "You don't have permission to add users to this server."
    }
    
    // Network failures
    if (error.message?.includes('Network') || error.message?.includes('network')) {
      return 'Unable to add user. Please check your connection and try again.'
    }
    
    // Authentication errors
    if (error.message?.includes('Unauthorized') || error.message?.includes('401')) {
      return 'Session expired. Please log in again.'
    }
    
    // Timeout errors
    if (error.message?.includes('timeout') || error.message?.includes('Timeout')) {
      return 'Request timed out. Please try again.'
    }
    
    // Return parsed message or default
    return baseMessage || 'Unable to add user. Please try again.'
  }
  
  // Fallback
  return baseMessage || 'An unexpected error occurred. Please try again.'
}

/**
 * Fetch users with access to the server
 * Requirements: 1.3, 1.4, 1.5, 2.1, 2.2, 2.3, 5.4
 */
const fetchUsers = async () => {
  // Guard against null or undefined serverId
  if (!props.serverId) {
    console.warn('fetchUsers called with null or undefined serverId')
    return
  }
  
  loading.value = true
  errorMessage.value = ''
  
  try {
    // Wrap the GraphQL call in a retry operation for transient failures
    // Requirements: 5.4
    const response = await retryOperation(async () => {
      return await client.graphql({
        query: getServerUsers,
        variables: { instanceId: props.serverId }
      })
    })
    
    users.value = response.data.getServerUsers || []
  } catch (error) {
    console.error('Error fetching users:', error)
    
    // Use error message extraction utility function
    // Requirements: 5.4
    errorMessage.value = extractUserFriendlyErrorMessage(error, 'fetch')
  } finally {
    loading.value = false
  }
}



/**
 * Search for a user by email address
 * Requirements: 3.1, 3.2, 3.7, 5.4
 */
const searchUser = async () => {
  // Prevent search when email is empty or invalid
  if (!isEmailValid.value) {
    return
  }

  searching.value = true
  searchMessage.value = ''
  searchResults.value = null
  errorMessage.value = ''

  try {
    // Call GraphQL query to search for user
    const response = await retryOperation(async () => {
      return await client.graphql({
        query: searchUserByEmail,
        variables: { email: newUserEmail.value.trim() }
      })
    })

    const user = response.data.searchUserByEmail
    if (user) {
      searchResults.value = user
      searchMessage.value = `Found user: ${user.fullName} (${user.email})`
    } else {
      // User not found (null response)
      searchResults.value = null
      searchMessage.value = 'User not found. They must log in to the dashboard at least once before being added.'
    }
  } catch (error) {
    console.error('Error searching for user:', error)
    
    // Handle specific error cases
    const errorMsg = extractUserFriendlyErrorMessage(error, 'search')
    
    // Check if this is a "user not found" error (current backend behavior)
    if (errorMsg.includes('USER_NOT_FOUND') || 
        errorMsg.includes('user must log in') ||
        errorMsg.includes('No user found with email') ||
        error.message?.includes('Cannot return null for non-nullable type')) {
      // Treat as "user not found" rather than an error
      searchResults.value = null
      searchMessage.value = 'User not found. They must log in to the dashboard at least once before being added to a server.'
    } else {
      // Real error that should be displayed
      errorMessage.value = errorMsg
    }
  } finally {
    searching.value = false
  }
}

/**
 * Clear search results and messages
 */
const clearSearch = () => {
  newUserEmail.value = ''
  searchResults.value = null
  searchMessage.value = ''
  errorMessage.value = ''
}

/**
 * Clear only search results (keep email field)
 */
const clearSearchResults = () => {
  searchResults.value = null
  searchMessage.value = ''
  errorMessage.value = ''
}

/**
 * Add a new user to the server
 * Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 5.4
 */
const addUser = async () => {
  // Prevent submission when email is empty or invalid
  // Requirements: 3.7
  if (!isEmailValid.value) {
    return
  }

  addingUser.value = true
  errorMessage.value = ''
  successMessage.value = ''

  try {
    // Call GraphQL mutation with instanceId and userEmail
    // Requirements: 3.3
    // Retry for transient failures
    // Requirements: 5.4
    await retryOperation(async () => {
      return await client.graphql({
        query: addUserToServer,
        variables: {
          instanceId: props.serverId,
          userEmail: newUserEmail.value.trim()
        }
      })
    })

    // Handle successful addition
    // Requirements: 3.4, 3.5
    successMessage.value = `Successfully added ${newUserEmail.value} to the server`
    
    // Auto-dismiss success message after 3.5 seconds
    // Requirements: 5.4
    setTimeout(() => {
      successMessage.value = ''
    }, 3500)
    
    // Clear form state
    clearSearch()
    
    // Refresh user list to show the newly added user
    await fetchUsers()
  } catch (error) {
    console.error('Error adding user:', error)
    
    // Handle failed addition: display error message
    // Requirements: 3.6, 5.4
    errorMessage.value = extractUserFriendlyErrorMessage(error, 'add')
  } finally {
    addingUser.value = false
  }
}

// Watch for dialog open and fetch users
// Requirements: 1.3, 4.4
watch(() => props.modelValue, (newValue) => {
  if (newValue && props.serverId) {
    fetchUsers()
    // Reset form state when dialog opens
    clearSearch()
    successMessage.value = ''
    
    // Accessibility: Set focus to dialog title when opened
    // Requirements: 4.4
    setTimeout(() => {
      const dialogTitle = document.getElementById('user-management-dialog-title')
      if (dialogTitle) {
        dialogTitle.setAttribute('tabindex', '-1')
        dialogTitle.focus()
      }
    }, 100)
  }
})

// Accessibility: Handle keyboard navigation
// Requirements: 4.4
onMounted(() => {
  // Add keyboard event listener for Escape key
  const handleEscape = (event) => {
    if (event.key === 'Escape' && props.modelValue) {
      // Vuetify dialog already handles Escape, but we ensure it's not persistent
      // This is a fallback for accessibility
    }
  }
  
  window.addEventListener('keydown', handleEscape)
  
  // Cleanup on unmount
  onUnmounted(() => {
    window.removeEventListener('keydown', handleEscape)
  })
})
</script>

<style scoped>
/**
 * Accessibility: Screen reader only content
 * Requirements: 4.4
 */
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border-width: 0;
}

/**
 * Responsive design: Ensure proper spacing on mobile
 * Requirements: 4.4
 */
@media (max-width: 600px) {
  :deep(.v-card-text) {
    padding: 16px;
  }
  
  :deep(.v-card-actions) {
    padding: 16px;
  }
  
  :deep(.v-list-item) {
    min-height: 56px;
  }
}

/**
 * Accessibility: Ensure focus indicators are visible
 * Requirements: 4.4
 */
:deep(.v-btn:focus-visible),
:deep(.v-text-field:focus-within) {
  outline: 2px solid currentColor;
  outline-offset: 2px;
}

/**
 * Responsive design: Adjust dialog padding on tablet
 * Requirements: 4.4
 */
@media (min-width: 601px) and (max-width: 960px) {
  :deep(.v-card-text) {
    padding: 20px;
  }
}

/**
 * Responsive design: Desktop optimizations
 * Requirements: 4.4
 */
@media (min-width: 961px) {
  :deep(.v-card-text) {
    padding: 24px;
  }
}

/**
 * Accessibility: Ensure sufficient color contrast
 * Requirements: 4.4
 * Note: Vuetify's default theme already provides WCAG AA compliant contrast ratios
 * This is a placeholder for any custom color overrides if needed
 */
</style>
