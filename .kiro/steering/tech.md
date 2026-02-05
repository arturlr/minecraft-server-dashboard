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
- **Configuration Management**: AWS Systems Manager (SSM) for bootstrap automation
- **Storage**: Amazon S3 for bootstrap scripts, Rust binaries, and frontend hosting

## Rust Services
- **msd-metrics**: Collects and sends server metrics (CPU, memory, network, active users) to CloudWatch
  - Runs as systemd service with 60-second intervals
  - Deployed via bootstrap script 05-setup-metrics.sh
  - Static binary built with musl target (no runtime dependencies)
- **msd-logs**: HTTP server that streams Minecraft logs via journalctl with JWT authentication
  - Listens on port 25566
  - Validates JWT token format (Bearer token)
  - Provides GET /logs?lines=N endpoint (max 1000 lines)
  - Provides GET /health endpoint for monitoring
  - Runs as systemd service with auto-restart
  - Deployed via bootstrap script 07-setup-log-server.sh
  - Reads logs from systemd journal (minecraft.service)

## Development Tools
- **Package Manager**: npm (frontend), pip (Python dependencies)
- **Module System**: ES modules (frontend), Python modules (backend)
- **Environment**: Node.js with Vite dev server
- **Rust Toolchain**: 1.70+ with musl target for static binaries
- **Build Tools**: AWS SAM CLI for infrastructure, Make for Lambda layers
- **CI/CD**: CircleCI for automated deployments
  - Separate dev and prod pipelines
  - Automated CloudFormation stack deployment
  - Rust binary compilation and S3 upload
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

### Bootstrap Script Deployment
```bash
# Update version
echo "1.0.1" > scripts/VERSION

# Scripts are deployed via CircleCI to S3:
# s3://{SupportBucket}/scripts/v1.0.1/
# s3://{SupportBucket}/scripts/latest/

# Manual upload (if needed)
aws s3 sync scripts/ s3://{SupportBucket}/scripts/latest/ --exclude ".git*"
```

### EC2 Bootstrap Execution
```bash
# Triggered by Lambda (ec2BootWorker or ssmCommandWorker)
# Executes SSM Run Command on EC2 instance
# Downloads and runs scripts from S3 in order:
# 00-bootstrap-helper.sh → 03-setup-cloudwatch.sh → 
# 05-setup-metrics.sh → 07-setup-log-server.sh → 
# 09-setup-minecraft-service.sh → 10-update-bootstrap-status.sh
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

### EC2 Bootstrap Architecture
- **Pattern**: Automated server configuration via SSM Run Command
- **Components**:
  - **S3 Support Bucket**: Stores versioned bootstrap scripts and Rust binaries
  - **SSM Document** (cfn/templates/ssm.yaml): Defines bootstrap automation workflow
  - **Lambda Triggers**: `ec2BootWorker` or `ssmCommandWorker` invoke SSM Run Command
  - **EC2 IAM Profile**: Grants permissions for S3 access, CloudWatch, DynamoDB, SSM
  - **Bootstrap Scripts**: Execute sequentially to configure server
- **Script Execution Flow**:
  1. **00-bootstrap-helper.sh**: Loads common functions and utilities
  2. **03-setup-cloudwatch.sh**: Installs CloudWatch agent, configures metrics/logs
  3. **05-setup-metrics.sh**: Downloads and installs msd-metrics binary, creates systemd service
  4. **07-setup-log-server.sh**: Downloads and installs msd-logs binary, creates systemd service
  5. **09-setup-minecraft-service.sh**: Configures Minecraft as systemd service with auto-restart
  6. **10-update-bootstrap-status.sh**: Updates DynamoDB with bootstrap completion status
- **Versioning**: Scripts use semantic versioning, servers can pin to specific versions
- **Rollback**: Change `scriptVersion` in DynamoDB config and re-trigger bootstrap
- **Benefits**: Consistent server configuration, automated updates, version control

### CloudFormation Nested Stack Pattern
- **Pattern**: Modular infrastructure with nested CloudFormation stacks
- **Main Template**: `cfn/template.yaml` orchestrates all nested stacks
- **Nested Stacks**:
  - **DynamoDBStack**: Core data tables (base dependency)
  - **CognitoStack**: Authentication resources (base dependency)
  - **EC2Stack**: IAM roles and instance profiles (depends on DynamoDB)
  - **SSMStack**: Bootstrap automation documents (depends on DynamoDB)
  - **LambdasStack**: Functions, layers, AppSync API, SQS (depends on all others)
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

### Bootstrap and Configuration Update Flow
1. **Trigger**: New server detected or configuration change requested
2. **Lambda**: `ec2BootWorker` or `ssmCommandWorker` invoked
3. **SSM Run Command**: Lambda invokes SSM document on target EC2 instance
4. **Script Download**: EC2 downloads bootstrap scripts from S3 (versioned or latest)
5. **Sequential Execution**: Scripts run in order (00 → 03 → 05 → 07 → 09 → 10)
6. **Service Installation**: CloudWatch agent, msd-metrics, msd-logs, Minecraft service
7. **Status Update**: Final script updates DynamoDB with bootstrap status
8. **Verification**: Lambda polls for completion, updates AppSync

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

### Bootstrap Script Testing
```bash
# Test scripts locally on EC2 instance
sudo su -
cd /tmp
aws s3 sync s3://{SupportBucket}/scripts/latest/ ./scripts/
chmod +x scripts/*.sh
./scripts/00-bootstrap-helper.sh

# Check systemd services
systemctl status msd-metrics
systemctl status msd-logs
systemctl status minecraft
journalctl -u minecraft -f

# Verify CloudWatch agent
/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
  -a fetch-config -m ec2 -s -c file:/opt/aws/amazon-cloudwatch-agent/etc/config.json
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