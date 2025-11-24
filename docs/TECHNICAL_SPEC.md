# Minecraft Server Dashboard - Technical Specification

## Application Overview

The Minecraft Server Dashboard is a comprehensive web application that enables users to manage and monitor Minecraft servers hosted on AWS EC2 instances. The application follows a modern serverless architecture pattern with a Vue.js frontend and AWS-based backend services.

## Technology Stack

### Frontend
- **Framework**: Vue 3.js
- **UI Library**: Vuetify
- **Build Tool**: Vite
- **AWS Integration**: AWS Amplify
- **State Management**: Vuex/Pinia
- **Real-time Updates**: GraphQL Subscriptions

### Backend
- **API Layer**: AWS AppSync (GraphQL)
- **Compute**: AWS Lambda (Python 3.9+)
- **Database**: Amazon DynamoDB
- **Authentication**: Amazon Cognito with Google OAuth
- **Infrastructure**: AWS CloudFormation via SAM
- **Monitoring**: Amazon CloudWatch
- **Content Delivery**: Amazon CloudFront

## Component Details

### 1. Frontend Application (`./dashboard`)

#### Key Components
- **Authentication Module**: Handles user login/logout and session management
- **Server Dashboard**: Displays server metrics and status
- **Server Control Panel**: Provides start/stop/restart functionality
- **Configuration Manager**: Allows editing server settings
- **User Management**: Controls access to servers
- **Cost Monitor**: Displays usage costs and projections

#### Environment Configuration
The frontend uses a `.env` file with the following parameters:
```
VITE_AWS_REGION=us-west-2
VITE_GRAPHQL_ENDPOINT=[AppSync API Endpoint]
VITE_CLOUDFRONT_URL=[CloudFront Distribution URL]
VITE_IDENTITY_POOL_ID=[Cognito Identity Pool ID]
VITE_COGNITO_USER_POOL_CLIENT_ID=[Cognito User Pool Client ID]
VITE_COGNITO_USER_POOL_ID=[Cognito User Pool ID]
VITE_COGNITO_DOMAIN=[Cognito Domain]
VITE_BUCKET_NAME=[S3 Bucket Name]
VITE_ADMIN_GROUP_NAME=admin
VITE_I18N_LOCALE=en
VITE_I18N_FALLBACK_LOCALE=en
```

#### Build and Deployment
```bash
# Install dependencies
npm install

# Development server
npm run dev

# Production build
npm run build

# Deploy to S3
aws s3 sync dist/ s3://[VITE_BUCKET_NAME]
```

### 2. Backend Lambda Functions (`./lambdas`)

#### eventResponse
- **Purpose**: Processes EC2 state changes and metrics
- **Triggers**: CloudWatch Events, AppSync API calls
- **Key Operations**:
  - Process instance state changes
  - Collect and format metrics
  - Update DynamoDB with current state

#### getMonthlyCost
- **Purpose**: Retrieves cost metrics for servers
- **Triggers**: AppSync API calls
- **Key Operations**:
  - Query AWS Cost Explorer API
  - Calculate instance-specific costs
  - Format cost data for frontend display

#### listServers
- **Purpose**: Lists available Minecraft servers
- **Triggers**: AppSync API calls
- **Key Operations**:
  - Query EC2 for instances with Minecraft tags
  - Retrieve instance metadata
  - Format server list for frontend display

#### serverAction
- **Purpose**: Validates and queues server control operations
- **Triggers**: AppSync API calls
- **Key Operations**:
  - Validate user authorization
  - Queue start/stop/restart/config actions to SQS
  - Send initial PROCESSING status to AppSync
  - Handle read-only operations (getServerConfig, getServerUsers) synchronously

#### serverActionProcessor
- **Purpose**: Processes server control actions asynchronously
- **Triggers**: SQS queue messages
- **Key Operations**:
  - Start/stop/restart EC2 instances
  - Update server configuration (tags, alarms, schedules)
  - Manage EventBridge rules for scheduled operations
  - Send status updates to AppSync (COMPLETED/FAILED)

#### fixServerRole
- **Purpose**: Manages IAM instance profile association
- **Triggers**: AppSync API calls (direct, synchronous)
- **Key Operations**:
  - Validate existing IAM profile on EC2 instance
  - Disassociate incorrect profiles
  - Associate correct instance profile
  - Retry with exponential backoff for eventual consistency

### 3. AppSync API (`./appsync`)

#### GraphQL Schema
The schema defines the following main types:
- **ServerInfo**: Basic server information (ID, name, state, etc.)
- **ServerMetric**: Performance metrics (CPU, memory, network, users)
- **ServerConfig**: Configuration settings (shutdown policies, commands)
- **ServerUsers**: User access management
- **MonthlyCost**: Cost tracking information
- **LogAudit**: Audit trail for actions

#### Key Operations
- **Queries**:
  - `listServers`: Get all available servers
  - `getMonthlyCost`: Get cost data for a server
  - `getServerConfig`: Get configuration for a server
  - `getServerUsers`: Get users with access to a server
  - `getLogAudit`: Get audit logs for a server

- **Mutations**:
  - `startServer`: Start a server
  - `stopServer`: Stop a server
  - `restartServer`: Restart a server
  - `putServerConfig`: Update server configuration
  - `addUserToServer`: Grant a user access to a server
  - `fixServerRole`: Fix IAM role issues

- **Subscriptions**:
  - `onPutServerMetric`: Real-time metric updates
  - `onChangeState`: Real-time server state changes

#### Authentication
- AppSync API secured with Cognito User Pools
- IAM authentication for system-level operations
- @aws_cognito_user_pools and @aws_iam directives control access

### 4. Infrastructure (`./cfn`)

#### CloudFormation Templates
- **Main Template**: `template.yaml` - Defines the core infrastructure
- **Nested Templates**: Additional templates for specific components

#### Key Resources
- **AppSync API**: GraphQL API with resolvers and data sources
- **Lambda Functions**: Backend compute resources
- **DynamoDB Tables**: Data storage for server information
- **Cognito Resources**: User authentication and authorization
- **IAM Roles**: Permissions for various components
- **CloudWatch Resources**: Monitoring and metrics
- **S3 Bucket**: Frontend hosting
- **CloudFront Distribution**: Content delivery

#### Deployment
```bash
# Build SAM application
sam build

# Deploy with guided prompts
sam deploy --guided

# Deploy with saved parameters
sam deploy
```

## Data Models

### ServerInfo
```
{
  id: String!           # EC2 Instance ID
  name: String          # Server name
  type: String          # Instance type
  userEmail: AWSEmail   # Owner email
  state: String         # Running state
  vCpus: Int            # CPU count
  memSize: Int          # Memory size
  diskSize: Int         # Disk size
  launchTime: String    # Launch timestamp
  publicIp: String      # Public IP address
  initStatus: String    # Initialization status
  iamStatus: String     # IAM role status
  runningMinutes: String # Uptime in minutes
}
```

### ServerConfig
```
{
  id: String!                  # EC2 Instance ID
  shutdownMethod: String       # Auto-shutdown method
  scheduleExpression: String   # Cron schedule for shutdown
  alarmThreshold: Float        # CPU threshold for shutdown
  alarmEvaluationPeriod: Int   # Evaluation period in minutes
  runCommand: String           # Command to run Minecraft
  workDir: String              # Working directory
}
```

### ServerMetric
```
{
  id: String!           # EC2 Instance ID
  cpuStats: AWSJSON     # CPU utilization metrics
  networkStats: AWSJSON # Network I/O metrics
  memStats: AWSJSON     # Memory utilization metrics
  activeUsers: AWSJSON  # Connected players
}
```

## Security Considerations

### Authentication Flow
1. User authenticates via Cognito User Pool
2. User receives JWT tokens
3. Tokens used for AppSync API authorization
4. Temporary AWS credentials obtained via Identity Pool
5. Credentials used for direct AWS service calls

### Authorization
- Admin group has full access to all servers
- Regular users can only access servers they own or are invited to
- IAM roles enforce least privilege access
- AppSync resolvers include authorization checks

### Data Security
- All data in transit encrypted via HTTPS
- DynamoDB tables encrypted at rest
- Sensitive parameters stored in SSM Parameter Store
- EC2 instances use security groups to restrict access

## Monitoring and Logging

### CloudWatch Metrics
- EC2 instance performance (CPU, memory, network)
- Lambda function invocations and errors
- AppSync API calls and latency
- DynamoDB throughput and errors

### CloudWatch Logs
- Lambda function logs
- AppSync resolver logs
- EC2 instance system logs
- Minecraft server logs

### Alarms
- High CPU utilization
- Low memory availability
- API errors above threshold
- Lambda function errors

## Cost Optimization

### Automated Shutdown Policies
- CPU utilization-based shutdown
- Schedule-based shutdown
- Manual shutdown option

### Resource Optimization
- Right-sizing recommendations
- Cost tracking and reporting
- Reserved instance recommendations

## Deployment Pipeline

### Development Workflow
1. Local development using Vite dev server
2. Test against development AWS environment
3. Commit code to repository
4. CI/CD pipeline triggered

### CI/CD Pipeline
1. Build frontend and backend
2. Run automated tests
3. Deploy infrastructure via SAM
4. Deploy frontend to S3
5. Invalidate CloudFront cache
6. Run integration tests

## Testing Strategy

### Unit Testing
- Vue component tests using Jest
- Lambda function tests using pytest
- GraphQL resolver tests

### Integration Testing
- End-to-end API tests
- Frontend-backend integration tests
- Authentication flow tests

### Load Testing
- Simulate multiple concurrent users
- Test real-time subscription performance
- Validate auto-scaling capabilities
