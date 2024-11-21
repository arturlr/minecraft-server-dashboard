# Dashboard Application

This README provides an overview of the Dashboard application, a Vue.js-based project that integrates with AWS services to manage and monitor server resources.

## Structure and Functionality

The Dashboard application is a Vue.js project that utilizes various AWS services, including AWS Amplify, for authentication and API interactions. It provides functionality for managing servers, monitoring metrics, and handling user authentication.

### High-Level Folder Layout

- `dashboard/`: Root directory of the application
  - `src/`: Contains the main source code
    - `graphql/`: GraphQL queries, mutations, and subscriptions
    - `router/`: Vue Router configuration
    - `stores/`: Pinia stores for state management
    - `views/`: Vue components for different views
  - `public/`: Public assets
  - `package.json`: Project dependencies and scripts
  - `vite.config.js`: Vite build tool configuration

## Data Flow

The application follows this general data flow for requests:

1. User interacts with the Vue.js frontend
2. Vue Router handles navigation
3. Pinia stores manage application state
4. AWS Amplify facilitates authentication and API calls
5. GraphQL queries/mutations communicate with the backend
6. Real-time updates are received through GraphQL subscriptions

```
+-------------+     +------------+     +-------------+
|   Vue.js    |     |    Pinia   |     |    AWS      |
|  Components | <-> |   Stores   | <-> |   Amplify   |
+-------------+     +------------+     +-------------+
       ^                                     ^
       |                                     |
       v                                     v
+-------------+                        +-------------+
| Vue Router  |                        |   GraphQL   |
+-------------+                        |    API      |
                                       +-------------+
```

## Usage

### Building

To build the application, you need:

- Node.js
- npm or yarn

Run the following command to install dependencies:

```
npm install
```

### Running

To run the application in development mode:

```
npm run dev
```

For production build:

```
npm run build
```

To preview the production build:

```
npm run preview
```

### Testing

No specific testing commands are provided in the given configuration.

### Deployment

The application is built using Vite. To deploy:

1. Run `npm run build` to create a production build
2. Deploy the contents of the `dist` directory to your web server or hosting platform

### Code Samples and Examples

Here's an example of how to use the server store in a Vue component:

```javascript
import { useServerStore } from '../stores/server';

export default {
  setup() {
    const serverStore = useServerStore();

    // Fetch list of servers
    serverStore.listServers();

    // Get server configuration
    const getConfig = async (instanceId) => {
      const config = await serverStore.getServerConfig(instanceId);
      console.log(config);
    };

    return { serverStore, getConfig };
  }
};
```

### Troubleshooting

- Check browser console for any JavaScript errors
- Verify AWS Amplify configuration in `src/configAmplify.js`
- Ensure all required environment variables are set
- Review GraphQL queries and mutations in case of API issues

## Contributors/Contribution

No specific contribution guidelines were provided in the given information.