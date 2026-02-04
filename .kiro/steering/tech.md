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
- **Log Streaming**: Custom Rust service (msd-logs) on port 25566

## Rust Services
- **msd-metrics**: Collects and sends server metrics (CPU, memory, network, active users) to CloudWatch
- **msd-logs**: HTTP server that streams Minecraft logs via journalctl with JWT authentication
  - Listens on port 25566
  - Validates JWT token format (Bearer token)
  - Provides GET /logs?lines=N endpoint (max 1000 lines)
  - Provides GET /health endpoint for monitoring
  - Runs as systemd service with auto-restart

## Development Tools
- **Package Manager**: npm
- **Module System**: ES modules
- **Environment**: Node.js with Vite dev server
- **Rust Toolchain**: 1.70+ with musl target for static binaries

## Common Commands

### Frontend Development
```bash
# Navigate to webapp directory
cd webapp

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

# Validate templates with linting
sam validate --lint

# Build SAM application
sam build

# Deploy with guided setup (first time)
sam deploy --guided

# Deploy with existing configuration
sam deploy
```

### Rust Binary Building
```bash
# Build msd-metrics
cd rust/msd-metrics
cargo build --release --target x86_64-unknown-linux-musl

# Build msd-logs
cd rust/msd-logs
cargo build --release --target x86_64-unknown-linux-musl
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
- **Pattern**: Queue-based asynchronous processing for server control actions
- **Components**:
  - `ec2ActionValidator` Lambda: Receives GraphQL mutations (start/stop/restart/config), validates, and queues to SQS
  - SQS Queue: Buffers server actions for reliable processing
  - `ec2ActionWorker` Lambda: Processes server control actions from queue, updates AppSync
  - Dead Letter Queue (DLQ): Captures failed messages for troubleshooting
- **Benefits**: Improved reliability, timeout handling, decoupled processing
- **Status Updates**: Real-time status via GraphQL subscriptions (PROCESSING/COMPLETED/FAILED)
- **Note**: IAM profile management (`iamProfileManager`) is handled synchronously by a dedicated Lambda, not queued

### IAM Profile Management
- **Pattern**: Synchronous IAM profile association/disassociation
- **Components**:
  - `iamProfileManager` Lambda: Dedicated function for IAM profile management
  - Direct execution (no SQS queue needed)
- **Operations**:
  - Validates existing IAM profile on EC2 instance
  - Disassociates incorrect profiles
  - Associates correct instance profile with `iam:PassRole` permission
  - Retries with exponential backoff for eventual consistency
- **Permissions**: Requires `iam:PassRole` on EC2 role (not instance profile ARN)
- **Benefits**: Focused permissions, simpler architecture, faster execution

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
  - Cron expression validation and formatting (5-field to 6-field EventBridge format)
  - Separate start/stop schedules with independent cron expressions
  - Automatic rule creation/deletion based on configuration
  - Integration with CloudWatch alarms (mutually exclusive)
  - Quick schedule presets (weekday evenings, weekends, business hours)
  - Smart validation warnings (start > stop time, short duration, etc.)
- **Cron Format**: Frontend sends standard 5-field cron, backend converts to EventBridge 6-field format
- **Example**: `30 14 * * 1,2,3` → `cron(30 14 * * 1,2,3 *)`

### User-Based Auto-Shutdown
- **Pattern**: CloudWatch custom metrics and alarms for player connection monitoring
- **Components**:
  - `port_count.sh`: Bash script that counts TCP connections on port 25565 (Minecraft)
  - Cron Job: Executes script every minute on EC2 instance
  - CloudWatch Custom Metric: `UserCount` metric in `MinecraftDashboard` namespace
  - CloudWatch Alarm: Monitors UserCount and triggers EC2 stop when threshold breached
- **Configuration**:
  - Threshold: Number of connected players (0-N)
  - Evaluation Period: Minutes below threshold before shutdown (1-60)
  - Statistic: Maximum (captures peak connections in period)
  - Action: EC2 stop automation when alarm fires
- **Benefits**: Automatic shutdown when server is idle, prevents premature shutdown during brief disconnections
- **Cost Savings**: ~$20-50/month in EC2 costs vs ~$0.40/month in CloudWatch costs (50-125x ROI)

## Code Style Conventions
- Use ES6+ features and async/await for asynchronous operations
- Follow Vue 3 Composition API patterns
- Use TypeScript-style JSDoc comments for Python functions
- Implement proper error handling with try/catch blocks
- Use environment variables for configuration (VITE_ prefix for frontend)
- Lambda functions should send status updates to AppSync for real-time UI feedback
- Separate data concerns: server config and user data use different queries
- Validate and format data at boundaries (e.g., cron expressions at backend entry)

## Recent Improvements & Fixes

### IAM Permissions (Fixed)
- **Issue**: `iam:PassRole` permission was incorrectly targeting instance profile ARN
- **Fix**: Updated to target EC2 role ARN (required for associating instance profiles)
- **Location**: `cfn/templates/lambdas.yaml` - iamProfileManager Lambda policies

### Schedule Expression Validation (Fixed)
- **Issue**: EventBridge rejected cron expressions from frontend
- **Fix**: Added validation and formatting in `ec2Helper.py` to convert 5-field to 6-field format
- **Features**: Validates ranges, handles wildcards, strips leading zeros, converts day-of-week
- **Location**: `layers/ec2Helper/ec2Helper.py` - `_format_schedule_expression()` method

### Server Settings Data Loading (Fixed)
- **Issue**: GraphQL queries outdated, missing fields, data type mismatches
- **Fix**: Updated queries to match schema, separated user data loading
- **Changes**:
  - Added `stopScheduleExpression`, `startScheduleExpression` to queries
  - Created separate `getServerUsers` query
  - Fixed data type handling in ServerSettings component
- **Location**: `webapp/src/graphql/queries.js`, `webapp/src/components/ServerSettings.vue`

### UI/UX Improvements
- **Quick Schedule Presets**: One-click common schedules (weekday evenings, weekends, etc.)
- **Smart Validation**: Warnings for timing conflicts, short durations, high thresholds
- **Visual Feedback**: Day chips, runtime calculations, color-coded summaries
- **Better Layout**: Card-based design with progressive disclosure
- **Location**: `webapp/src/components/ServerSettings.vue`

## GraphQL Schema & Data Models

### Main GraphQL Types
- **ServerInfo**: Basic server information (ID, name, state, IP, config validation status)
- **ServerMetric**: Performance metrics (CPU, memory, network, active users)
- **ServerConfig**: Configuration settings (shutdown policies, commands, schedules)
- **ServerUsers**: User access management
- **MonthlyCost**: Cost tracking information
- **LogAudit**: Audit trail for actions
- **ec2ActionValidatorStatus**: Real-time action status tracking (start/stop/restart/config updates)

### Key GraphQL Operations
- **Queries**: `ec2Discovery`, `ec2CostCalculator`, `getServerConfig`, `getServerUsers`, `getLogAudit`, `getec2ActionValidatorStatus`
- **Mutations**: `startServer`, `stopServer`, `restartServer`, `putServerConfig`, `updateServerConfig`, `addUserToServer`, `iamProfileManager`, `putec2ActionValidatorStatus`
- **Subscriptions**: `onPutServerMetric`, `onChangeState`, `onPutec2ActionValidatorStatus` (real-time action status updates)

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