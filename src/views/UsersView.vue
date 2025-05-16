<template>
  <div>
    <v-card>
      <v-card-title>
        Users and Groups
        <v-spacer></v-spacer>
        <v-text-field
          v-model="search"
          append-icon="mdi-magnify"
          label="Search"
          single-line
          hide-details
        ></v-text-field>
      </v-card-title>
      
      <v-data-table
        :headers="headers"
        :items="users"
        :search="search"
        :loading="loading"
        loading-text="Loading users... Please wait"
        class="elevation-1"
      >
        <template v-slot:top>
          <v-dialog v-model="dialog" max-width="500px">
            <template v-slot:activator="{ on, attrs }">
              <v-btn
                color="primary"
                dark
                class="mb-2 ml-4"
                v-bind="attrs"
                v-on="on"
              >
                <v-icon left>mdi-account-plus</v-icon>
                Add User to Group
              </v-btn>
            </template>
            <v-card>
              <v-card-title>
                <span class="text-h5">Add User to Group</span>
              </v-card-title>

              <v-card-text>
                <v-container>
                  <v-row>
                    <v-col cols="12">
                      <v-text-field
                        v-model="editedItem.email"
                        label="Email"
                      ></v-text-field>
                    </v-col>
                    <v-col cols="12">
                      <v-select
                        v-model="editedItem.group"
                        :items="availableGroups"
                        label="Group (Server)"
                      ></v-select>
                    </v-col>
                  </v-row>
                </v-container>
              </v-card-text>

              <v-card-actions>
                <v-spacer></v-spacer>
                <v-btn
                  color="blue darken-1"
                  text
                  @click="close"
                >
                  Cancel
                </v-btn>
                <v-btn
                  color="blue darken-1"
                  text
                  @click="save"
                >
                  Save
                </v-btn>
              </v-card-actions>
            </v-card>
          </v-dialog>
        </template>
        
        <template v-slot:item.groups="{ item }">
          <v-chip
            v-for="(group, index) in parseGroups(item.groups)"
            :key="index"
            class="ma-1"
            small
            color="primary"
          >
            {{ group }}
          </v-chip>
        </template>
        
        <template v-slot:item.actions="{ item }">
          <v-icon
            small
            class="mr-2"
            @click="editItem(item)"
          >
            mdi-pencil
          </v-icon>
        </template>
      </v-data-table>
    </v-card>
    
    <v-snackbar
      v-model="snackbar"
      :timeout="3000"
      :color="snackbarColor"
    >
      {{ snackbarText }}
      <template v-slot:action="{ attrs }">
        <v-btn
          text
          v-bind="attrs"
          @click="snackbar = false"
        >
          Close
        </v-btn>
      </template>
    </v-snackbar>
  </div>
</template>

<script>
import { Auth, API } from "aws-amplify";
import { mapGetters } from "vuex";
import { listServers } from "../graphql/queries";

export default {
  name: "UsersView",
  data() {
    return {
      search: "",
      loading: false,
      dialog: false,
      snackbar: false,
      snackbarText: "",
      snackbarColor: "success",
      headers: [
        { text: "Username", value: "username" },
        { text: "Email", value: "email" },
        { text: "Groups", value: "groups" },
        { text: "Status", value: "status" },
        { text: "Actions", value: "actions", sortable: false }
      ],
      users: [],
      servers: [],
      editedIndex: -1,
      editedItem: {
        email: "",
        group: ""
      },
      defaultItem: {
        email: "",
        group: ""
      }
    };
  },
  computed: {
    ...mapGetters({
      isAuthenticated: "profile/isAuthenticated",
      email: "profile/email"
    }),
    availableGroups() {
      return this.servers.map(server => server.name);
    }
  },
  watch: {
    dialog(val) {
      val || this.close();
    }
  },
  async created() {
    this.loading = true;
    try {
      await this.fetchUsers();
    } catch (error) {
      console.error("Error fetching users:", error);
      this.showSnackbar("Error loading users data", "error");
    } finally {
      this.loading = false;
    }
  },
  methods: {
    async fetchUsers() {
      try {
        // Get current authenticated user
        const currentUser = await Auth.currentAuthenticatedUser();
        
        // Get all users in the Cognito User Pool
        // Note: This requires appropriate permissions
        const cognitoUsers = await this.listCognitoUsers();
        
        // Get server data to extract group members
        const serverData = await this.fetchServerData();
        this.servers = serverData;
        
        // Process and combine the data
        this.users = this.processUserData(cognitoUsers, serverData);
      } catch (error) {
        console.error("Error in fetchUsers:", error);
        throw error;
      }
    },
    
    async listCognitoUsers() {
      try {
        // This is a placeholder - in a real implementation, you would call
        // a Lambda function or API endpoint that has permission to list Cognito users
        // For now, we'll return a mock list with the current user
        const currentUser = await Auth.currentAuthenticatedUser();
        return [
          {
            username: currentUser.username,
            email: currentUser.attributes.email,
            status: "CONFIRMED",
            groups: ["Admin"]
          }
        ];
      } catch (error) {
        console.error("Error listing Cognito users:", error);
        return [];
      }
    },
    
    async fetchServerData() {
      try {
        // Use the existing GraphQL query to get server data
        const response = await API.graphql({
          query: listServers
        });
        
        return response.data.listServers || [];
      } catch (error) {
        console.error("Error fetching server data:", error);
        return [];
      }
    },
    
    processUserData(cognitoUsers, serverData) {
      // Create a map to store user data with their groups
      const userMap = new Map();
      
      // First, add all Cognito users to the map
      cognitoUsers.forEach(user => {
        userMap.set(user.email, {
          username: user.username,
          email: user.email,
          status: user.status,
          groups: user.groups || []
        });
      });
      
      // Then, process server data to extract group members
      serverData.forEach(server => {
        if (server.groupMembers) {
          try {
            const groupMembers = JSON.parse(server.groupMembers);
            
            // For each group member in the server
            Object.entries(groupMembers).forEach(([email, details]) => {
              if (userMap.has(email)) {
                // Update existing user's groups
                const user = userMap.get(email);
                if (!user.groups.includes(server.name)) {
                  user.groups.push(server.name);
                }
              } else {
                // Add new user with this server as their group
                userMap.set(email, {
                  username: email.split('@')[0], // Extract username from email
                  email: email,
                  status: "UNKNOWN", // We don't know their Cognito status
                  groups: [server.name]
                });
              }
            });
          } catch (error) {
            console.error(`Error parsing groupMembers for server ${server.name}:`, error);
          }
        }
      });
      
      // Convert the map back to an array
      return Array.from(userMap.values());
    },
    
    parseGroups(groups) {
      if (!groups) return [];
      return Array.isArray(groups) ? groups : [groups];
    },
    
    editItem(item) {
      this.editedIndex = this.users.indexOf(item);
      this.editedItem = Object.assign({}, item);
      this.dialog = true;
    },
    
    close() {
      this.dialog = false;
      this.$nextTick(() => {
        this.editedItem = Object.assign({}, this.defaultItem);
        this.editedIndex = -1;
      });
    },
    
    async save() {
      // In a real implementation, this would update the server's groupMembers
      // For now, we'll just show a success message
      
      if (this.editedIndex > -1) {
        // Editing existing user
        this.showSnackbar(`User ${this.editedItem.email} updated successfully`, "success");
      } else {
        // Adding new user to group
        this.showSnackbar(`User ${this.editedItem.email} added to ${this.editedItem.group}`, "success");
      }
      
      this.close();
      
      // Refresh the data
      this.loading = true;
      try {
        await this.fetchUsers();
      } catch (error) {
        console.error("Error refreshing users:", error);
      } finally {
        this.loading = false;
      }
    },
    
    showSnackbar(text, color = "success") {
      this.snackbarText = text;
      this.snackbarColor = color;
      this.snackbar = true;
    }
  }
};
</script>