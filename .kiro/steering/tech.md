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
- **Message Queue**: Amazon SQS for asynchronous action processing (main queue + DLQ)
- **Database**: Amazon DynamoDB for server state and configuration
- **Authentication**: Amazon Cognito User Pools with Google OAuth
- **Infrastructure**: AWS CloudFormation via SAM (nested stacks)
- **Monitoring**: Amazon CloudWatch for metrics, logs, and alarms
- **Scheduling**: Amazon EventBridge for scheduled server operations
- **Content Delivery**: Amazon CloudFront
- **Log Streaming**: Custom Rust service (msd-logs) on port 25566
- **Configuration Management**: AWS Systems Manager (SSM) Parameter Store for secrets
- **Container Registry**: Amazon ECR for custom Docker images (msd-metrics, msd-logs)
- **Container Runtime**: Docker with docker-compose on EC2 instances
- **Storage**: Amazon S3 for docker-compose files and frontend hosting

## Docker Services
- **minecraft**: itzg/minecraft-server image from Docker Hub
  - Configurable via environment variables (VERSION, MEMORY, TYPE)
  - Health checks, resource limits, RCON enabled
  - World data persisted on EBS volume at /mnt/minecraft-world
- **msd-metrics**: Custom image (ECR) - Collects and sends server metrics to CloudWatch
  - Runs as Docker container with 60-second intervals
  - Static binary built with musl target (multi-stage Dockerfile)
- **msd-logs**: Custom image (ECR) - HTTP server that streams Minecraft logs with JWT authentication
  - Listens on port 25566
  - Reads logs from shared volume (/data/logs)
  - Validates JWT token (Bearer token)
  - Provides GET /logs?lines=N endpoint (max 1000 lines)
  - Provides GET /health endpoint for monitoring

## Container Update Flow
- CircleCI builds and pushes Docker images to ECR on every commit
- EC2 instances run a systemd service (docker-update.service) on every boot
- Service pulls latest images from ECR and starts containers
- Users stop/start EC2 instance to update containers

## Development Tools
- **Package Manager**: npm (frontend), pip (Python dependencies)
- **Module System**: ES modules (frontend), Python modules (backend)
- **Environment**: Node.js with Vite dev server
- **Rust Toolchain**: 1.70+ with musl target for static binaries
- **Build Tools**: AWS SAM CLI for infrastructure, Make for Lambda layers
- **CI/CD**: CircleCI for automated deployments
  - Separate dev and prod pipelines
  - Parallel Docker image builds (msd-metrics, msd-logs) and ECR push
  - Automated CloudFormation stack deployment
  - Frontend build and CloudFront invalidation
  - Stack rollback handling
- **Version Control**: Git with semantic versioning for bootstrap scripts
- **AWS CLI**: For manual deployments and debugging

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

# What 'make' does:
# 1. Creates python/ subdirectory
# 2. Installs requirements.txt to python/
# 3. Copies layer code to python/
# 4. SAM packages this structure as a layer
```

### Docker Image Deployment
```bash
# Images are built and pushed by CircleCI:
# msd-metrics → ECR (tagged with SHA + latest)
# msd-logs → ECR (tagged with SHA + latest)

# EC2 instances pull latest on every boot via systemd:
# docker-compose pull && docker-compose up -d
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

### Docker Container Architecture
- **Pattern**: Containerized services with automatic updates on EC2 boot
- **Components**:
  - **ECR Repositories**: Store msd-metrics and msd-logs Docker images
  - **docker-compose.yml**: Defines 3 services (minecraft, msd-metrics, msd-logs)
  - **Systemd Service**: docker-update.service pulls and starts containers on every boot
  - **EC2 User Data**: One-time setup (Docker install, EBS mount, secrets)
- **Update Flow**:
  1. CircleCI builds and pushes images to ECR (tagged with SHA + latest)
  2. User stops/starts EC2 instance from dashboard
  3. Systemd service pulls latest images and starts containers
- **Benefits**: Simple updates, no SSM complexity, automatic on boot

### CloudFormation Nested Stack Pattern
- **Pattern**: Modular infrastructure with nested CloudFormation stacks
- **Main Template**: `cfn/template.yaml` orchestrates all nested stacks
- **Nested Stacks**:
  - **DynamoDBStack**: Core data tables (base dependency)
  - **CognitoStack**: Authentication resources (base dependency)
  - **ECRStack**: ECR repositories, Secrets Manager, SSM parameters
  - **EC2Stack**: IAM roles and instance profiles (depends on DynamoDB, ECR)
  - **LambdasStack**: Functions, layers, AppSync API, SQS (depends on Cognito, DynamoDB)
- **Stack Exports**: Each stack exports values (ARNs, IDs) for cross-stack references
- **Benefits**: Modular deployment, clear dependencies, easier updates, resource isolation
- **Deployment**: `sam build && sam deploy` handles nested stack orchestration

## Code Style Conventions
- Use ES6+ features and async/await for asynchronous operations
- Follow Vue 3 Composition API patterns
- Use TypeScript-style JSDoc comments for Python functions
- Implement proper error handling with try/catch blocks
- Use environment variables for configuration (VITE_ prefix for frontend)
- Lambda functions should send status updates to AppSync for real-time UI feedback
- Separate data concerns: server config and user data use different queries
- Validate and format data at boundaries (e.g., cron expressions at backend entry)

## Data Flow Patterns

### Server Control Flow (Start/Stop/Restart)
1. **Frontend**: User clicks start/stop/restart button
2. **GraphQL Mutation**: `startServer`, `stopServer`, or `restartServer` sent to AppSync
3. **ec2ActionValidator Lambda**: Validates request, queues to SQS, returns PROCESSING status
4. **SQS Queue**: Buffers action for reliable processing
5. **ec2ActionWorker Lambda**: Processes action from queue, performs EC2 operation
6. **Status Update**: Worker sends status to AppSync via `putec2ActionValidatorStatus` mutation
7. **GraphQL Subscription**: Frontend receives real-time status update (COMPLETED/FAILED)
8. **UI Update**: Button state and server status updated in real-time

### Server Discovery and Auto-Configuration Flow
1. **Frontend**: Dashboard loads, queries `ec2Discovery`
2. **ec2Discovery Lambda**: Lists EC2 instances with specific tags
3. **Tag Validation**: Parallel validation of required tags (name, commands, shutdown config)
4. **Auto-Configuration**: If tags missing, applies defaults (CPU shutdown, Minecraft commands)
5. **CloudWatch Alarm Creation**: Creates alarms for auto-configured servers
6. **Response**: Returns server list with validation status (warnings, errors, autoConfigured flag)
7. **Frontend**: Displays servers with configuration status indicators

### Metrics Collection and Display Flow
1. **EC2 Instance**: msd-metrics service collects system metrics every 60 seconds
2. **CloudWatch**: Metrics sent to `MinecraftDashboard` namespace
3. **Frontend**: Subscribes to `onPutServerMetric` GraphQL subscription
4. **ec2StateHandler Lambda**: Triggered by CloudWatch events, queries latest metrics
5. **AppSync**: Publishes metrics to subscribed clients
6. **Frontend**: Updates charts and displays in real-time (CPU, memory, network, users)

### Log Streaming Flow
1. **Frontend**: User opens logs view, requests logs from server
2. **getServerLogs Lambda**: Validates user authorization for server
3. **JWT Generation**: Lambda generates short-lived JWT token for msd-logs service
4. **HTTP Request**: Lambda calls msd-logs service on EC2 (port 25566) with JWT
5. **msd-logs Service**: Validates JWT, reads logs from systemd journal (minecraft.service)
6. **Response**: Returns formatted logs (up to 1000 lines)
7. **Frontend**: Displays logs with syntax highlighting and auto-refresh

### Docker Container Update Flow
1. **CircleCI**: Builds Docker images and pushes to ECR (tagged with SHA + latest)
2. **User**: Stops server from dashboard (EC2 stops)
3. **User**: Starts server from dashboard (EC2 starts)
4. **Systemd**: docker-update.service runs on boot
5. **Docker Compose**: Pulls latest images from ECR
6. **Docker Compose**: Starts all containers (minecraft, msd-metrics, msd-logs)
7. **Ready**: Server running with latest code

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
- JWT tokens for service-to-service authentication (msd-logs)
- AppSync authorization with Cognito user pools and IAM
- S3 buckets with restricted access policies

## Testing and Debugging

### Lambda Function Testing
```bash
# Local testing with SAM
sam local invoke FunctionName -e events/test-event.json

# View Lambda logs
aws logs tail /aws/lambda/FunctionName --follow

# Test specific Lambda with payload
aws lambda invoke --function-name FunctionName \
  --payload '{"key":"value"}' response.json
```

### Frontend Testing
```bash
# Run development server with hot reload
cd webapp && npm run dev

# Test GraphQL queries in browser console
# AppSync provides GraphQL playground at API endpoint

# Check browser console for errors
# Network tab shows GraphQL requests/responses
```

### Docker Container Testing
```bash
# Check container status
cd /opt/minecraft-dashboard
docker-compose ps

# View container logs
docker-compose logs minecraft
docker-compose logs msd-metrics
docker-compose logs msd-logs

# Restart a specific container
docker-compose restart minecraft

# Pull latest images and restart
docker-compose pull && docker-compose up -d

# Check systemd boot service
systemctl status docker-update.service
journalctl -u docker-update.service
```

### Common Debugging Commands
```bash
# Check EC2 instance metadata
curl http://169.254.169.254/latest/meta-data/instance-id

# Test msd-logs service
curl -H "Authorization: Bearer {JWT_TOKEN}" \
  http://localhost:25566/logs?lines=100

# Check CloudWatch metrics
aws cloudwatch get-metric-statistics \
  --namespace MinecraftDashboard \
  --metric-name UserCount \
  --dimensions Name=InstanceId,Value=i-xxxxx \
  --start-time 2026-02-04T00:00:00Z \
  --end-time 2026-02-04T23:59:59Z \
  --period 300 --statistics Maximum

# View DynamoDB items
aws dynamodb scan --table-name {TableName} --limit 10

# Check SQS queue
aws sqs get-queue-attributes \
  --queue-url {QueueURL} \
  --attribute-names All
```

## Performance Considerations

### Lambda Optimization
- **Cold Start Mitigation**: Keep functions warm with EventBridge scheduled pings
- **Memory Allocation**: Right-size memory (affects CPU allocation)
- **Layer Usage**: Share common code via layers to reduce deployment package size
- **Connection Pooling**: Reuse DynamoDB and AppSync connections across invocations

### Frontend Optimization
- **Code Splitting**: Vite automatically splits code by route
- **Asset Optimization**: Images and assets served via CloudFront CDN
- **GraphQL Subscriptions**: Use subscriptions for real-time updates instead of polling
- **Lazy Loading**: Load components and data on-demand

### Database Optimization
- **DynamoDB Design**: Single-table design with composite keys (PK: SERVER#{id}, SK: CONFIG/USERS/METRICS)
- **Query Patterns**: Use Query instead of Scan operations
- **Indexes**: GSI for user-based queries (access by username)
- **TTL**: Automatic cleanup of old metrics data

### Cost Optimization
- **Lambda**: Use appropriate memory settings, minimize execution time
- **DynamoDB**: On-demand pricing for variable workloads
- **CloudWatch**: Aggregate metrics, use appropriate retention periods
- **S3**: Lifecycle policies for old logs and artifacts
- **EC2**: Auto-shutdown policies reduce idle time costs by 50-80%