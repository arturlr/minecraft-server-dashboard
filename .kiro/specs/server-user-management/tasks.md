# Implementation Plan

- [x] 1. Create UserManagementDialog component with basic structure
  - Create new file `dashboard/src/components/UserManagementDialog.vue`
  - Set up component with `<script setup>` using Vue 3 Composition API
  - Define props: `modelValue` (Boolean), `serverId` (String), `serverName` (String)
  - Define emits: `update:modelValue`
  - Create basic Vuetify v-dialog structure with v-card
  - Add dialog header with server name display
  - _Requirements: 1.2, 4.2_

- [x] 2. Implement user list fetching and display
  - Import `getServerUsers` query from `@/graphql/queries`
  - Import Amplify API client
  - Create reactive state: `users` array, `loading` boolean, `errorMessage` string
  - Implement `fetchUsers()` method to call GraphQL query with serverId
  - Add watcher to fetch users when dialog opens (watch modelValue)
  - Display loading indicator (v-progress-circular) during fetch
  - Display user list using v-list and v-list-item components
  - Show each user's email and fullName in list items
  - Display empty state message when users array is empty
  - Display error message with retry button on fetch failure
  - _Requirements: 1.3, 1.4, 1.5, 2.1, 2.2, 2.3_

- [ ]* 2.1 Write property test for user display completeness
  - **Property 1: User display completeness**
  - **Validates: Requirements 2.1**

- [x] 3. Implement add user functionality
  - Import `addUserToServer` mutation from `@/graphql/mutations`
  - Create reactive state: `newUserEmail` string, `addingUser` boolean, `successMessage` string
  - Add v-text-field for email input with v-model binding to `newUserEmail`
  - Implement email validation rules using `emailRules` array
  - Add "Add User" button that calls `addUser()` method
  - Implement `addUser()` method to call GraphQL mutation with instanceId and userEmail
  - Handle successful addition: refresh user list, clear input, show success message
  - Handle failed addition: display error message
  - Prevent submission when email is empty or invalid
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7_

- [ ]* 3.1 Write property test for email validation correctness
  - **Property 2: Email validation correctness**
  - **Validates: Requirements 3.2**

- [x] 4. Implement error handling and user feedback
  - Create error message extraction utility function
  - Handle different GraphQL error types (network, auth, server, timeout)
  - Display user-friendly error messages using v-alert component
  - Add retry mechanism for transient failures
  - Display success messages using v-alert component with auto-dismiss
  - _Requirements: 5.4_

- [ ]* 4.1 Write property test for error message extraction
  - **Property 3: Error message extraction**
  - **Validates: Requirements 5.4**

- [x] 5. Add responsive design and accessibility
  - Add responsive breakpoints for mobile, tablet, and desktop
  - Make dialog full-screen on mobile devices using Vuetify's fullscreen prop
  - Ensure touch targets are at least 44x44px on mobile
  - Add proper ARIA labels to dialog and form elements
  - Ensure keyboard navigation works correctly
  - Test color contrast for accessibility
  - _Requirements: 4.4_

- [x] 6. Update ec2ActionValidatorsMenu component
  - Open `dashboard/src/components/ec2ActionValidatorsMenu.vue`
  - Add new v-tooltip with "Manage Users" text
  - Add v-btn with icon="mdi-account-multiple"
  - Emit 'open-users' event on button click
  - Follow existing styling patterns from other action buttons
  - Ensure responsive design matches other buttons
  - _Requirements: 1.1, 4.1_

- [x] 7. Update ServerTable component
  - Open `dashboard/src/components/ServerTable.vue`
  - Import UserManagementDialog component
  - Add reactive state: `userManagementDialog` (Boolean), `selectedServerId` (String), `selectedServerName` (String)
  - Add UserManagementDialog to template with v-model binding
  - Pass `selectedServerId` and `selectedServerName` as props to dialog
  - Implement `openUserManagement(serverId, serverName)` method
  - Add event handler for 'open-users' event from ec2ActionValidatorsMenu
  - Pass 'open-users' event through from ec2ActionValidatorsMenu to openUserManagement method
  - _Requirements: 1.2_

- [ ]* 8. Write unit tests for UserManagementDialog
  - Test dialog opens and closes correctly
  - Test users are fetched on dialog open
  - Test loading state is displayed during fetch
  - Test error state is displayed on fetch failure
  - Test empty state is displayed when no users exist
  - Test add user form submission with valid email
  - Test add user form validation prevents empty submission
  - Test success message after successful user addition
  - Test error message after failed user addition
  - Test user list refreshes after successful addition
  - _Requirements: All_

- [ ]* 9. Write unit tests for ec2ActionValidatorsMenu updates
  - Test user management button is rendered
  - Test correct icon is used (mdi-account-multiple)
  - Test click event emits 'open-users' event
  - _Requirements: 1.1, 4.1_

- [ ]* 10. Write unit tests for ServerTable updates
  - Test dialog state management
  - Test correct server context is passed to dialog
  - Test event handling from ec2ActionValidatorsMenu
  - _Requirements: 1.2_

- [ ] 11. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.
