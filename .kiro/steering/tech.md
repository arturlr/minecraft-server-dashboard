# Technology Stack

## Frontend
- **Framework**: Vue 3.js
- **UI Library**: Vuetify for Material Design components
- **Build Tool**: Vite for fast development and building
- **State Management**: Vuex/Pinia for reactive state management
- **AWS Integration**: AWS Amplify SDK
- **Real-time Updates**: GraphQL Subscriptions

## Backend
- **API Layer**: AWS AppSync (GraphQL)
- **Compute**: AWS Lambda functions (Python 3.9+)
- **Message Queue**: Amazon SQS for asynchronous action processing
- **Database**: Amazon DynamoDB for server state and configuration
- **Authentication**: Amazon Cognito User Pools with Google OAuth
- **Infrastructure**: AWS CloudFormation via SAM
- **Monitoring**: Amazon CloudWatch for metrics, logs, and alarms
- **Scheduling**: Amazon EventBridge for scheduled server operations
- **Content Delivery**: Amazon CloudFront

## Development Tools
- **Package Manager**: npm
- **Module System**: ES modules
- **Environment**: Node.js with Vite dev server

## Common Commands

### Frontend Development
```bash
# Navigate to dashboard directory
cd dashboard

# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

### Infrastructure Deployment
```bash
# Navigate to CloudFormation directory
cd cfn

# Build SAM application
sam build

# Deploy with guided setup (first time)
sam deploy --guided

# Deploy with existing configuration
sam deploy
```

### Lambda Layer Building
```bash
# Build specific layer (from layer directory)
make

# Example: Build auth helper layer
cd layers/authHelper && make
```

## Architecture Patterns

### Asynchronous Action Processing
- **Pattern**: Queue-based asynchronous processing for server actions
- **Components**:
  - `serverAction` Lambda: Receives GraphQL mutations, validates, and queues to SQS
  - SQS Queue: Buffers server actions for reliable processing
  - `serverActionProcessor` Lambda: Processes actions from queue, updates AppSync
  - Dead Letter Queue (DLQ): Captures failed messages for troubleshooting
- **Benefits**: Improved reliability, timeout handling, decoupled processing
- **Status Updates**: Real-time status via GraphQL subscriptions (PROCESSING/COMPLETED/FAILED)

### Auto-Configuration System
- **Pattern**: Automatic default configuration for unconfigured servers
- **Defaults Applied**:
  - CPU-based shutdown (5% threshold, 30-minute evaluation)
  - Minecraft run command and working directory
  - CloudWatch alarm creation
- **Validation**: Parallel tag validation with comprehensive error/warning reporting
- **Status Indicators**: `configStatus`, `configValid`, `configWarnings`, `configErrors`, `autoConfigured`

### Scheduled Operations
- **Pattern**: EventBridge rules for time-based server operations
- **Features**:
  - Cron expression validation
  - Separate start/stop schedules
  - Automatic rule creation/deletion based on configuration
  - Integration with CloudWatch alarms (mutually exclusive)

## Code Style Conventions
- Use ES6+ features and async/await for asynchronous operations
- Follow Vue 3 Composition API patterns
- Use TypeScript-style JSDoc comments for Python functions
- Implement proper error handling with try/catch blocks
- Use environment variables for configuration (VITE_ prefix for frontend)
- Lambda functions should send status updates to AppSync for real-time UI feedback

## GraphQL Schema & Data Models

### Main GraphQL Types
- **ServerInfo**: Basic server information (ID, name, state, IP, config validation status)
- **ServerMetric**: Performance metrics (CPU, memory, network, active users)
- **ServerConfig**: Configuration settings (shutdown policies, commands, schedules)
- **ServerUsers**: User access management
- **MonthlyCost**: Cost tracking information
- **LogAudit**: Audit trail for actions
- **ServerActionStatus**: Real-time action status tracking (start/stop/restart/config updates)

### Key GraphQL Operations
- **Queries**: `listServers`, `getMonthlyCost`, `getServerConfig`, `getServerUsers`, `getLogAudit`, `getServerActionStatus`
- **Mutations**: `startServer`, `stopServer`, `restartServer`, `putServerConfig`, `updateServerConfig`, `addUserToServer`, `fixServerRole`, `putServerActionStatus`
- **Subscriptions**: `onPutServerMetric`, `onChangeState`, `onPutServerActionStatus` (real-time action status updates)

## Authentication & Authorization
- **Primary Auth**: Amazon Cognito User Pools with Google OAuth
- **API Security**: AppSync secured with @aws_cognito_user_pools and @aws_iam directives
- **User Roles**: Admin group has full access, regular users access owned/invited servers
- **Token Flow**: JWT tokens → AppSync authorization → Temporary AWS credentials via Identity Pool

## Security Best Practices
- All data in transit encrypted via HTTPS
- DynamoDB tables encrypted at rest
- Sensitive parameters stored in SSM Parameter Store
- EC2 instances use security groups to restrict access
- IAM roles enforce least privilege access