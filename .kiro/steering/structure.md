# Project Structure

## Root Level Organization
```
├── webapp/            # Vue.js frontend application
├── cfn/               # AWS SAM CloudFormation templates
├── lambdas/           # AWS Lambda function source code
├── layers/            # AWS Lambda layers for shared code
├── appsync/           # GraphQL schema and resolvers
├── scripts/           # EC2 bootstrap scripts (deployed to S3)
├── rust/              # Rust services (msd-metrics, msd-logs)
├── docs/              # Project documentation
├── images/            # Screenshots and diagrams
└── public/            # Static web assets
```

## Frontend Structure (`webapp/`)
```
webapp/
├── src/
│   ├── components/    # Reusable Vue components
│   ├── views/         # Page-level Vue components
│   ├── stores/        # Vuex/Pinia state management
│   ├── router/        # Vue Router configuration
│   ├── graphql/       # GraphQL queries, mutations, subscriptionscd 
│   ├── layouts/       # Layout components
│   └── assets/        # Static assets (CSS, images)
├── public/            # Public static files
├── .env               # Environment variables (VITE_ prefixed)
└── package.json       # Dependencies and scripts
```

### Key Frontend Components
- **Authentication Module**: User login/logout and session management
- **Server Dashboard**: Server metrics and status display with real-time action status
- **Server Control Panel**: Start/stop/restart functionality with async status tracking
- **Configuration Manager**: Server settings editor with validation feedback and smart warnings
  - Quick schedule presets (weekday evenings, weekends, business hours)
  - Visual schedule summary with day chips and runtime calculations
  - Smart validation warnings (timing conflicts, short durations, high thresholds)
  - Separate user management with dedicated query
- **ServerConfigDebug**: Debug view for configuration validation warnings/errors
- **User Management**: Server access control with separate data loading
- **Cost Monitor**: Usage costs and projections

## Backend Structure

### Lambda Functions (`lambdas/`)
- **ec2StateHandler/**: Processes EC2 state changes and metrics
- **ec2CostCalculator/**: Retrieves AWS cost data from Cost Explorer API
- **ec2Discovery/**: Lists available Minecraft servers from EC2 with tag validation and auto-configuration
- **ec2ActionValidator/**: Validates and queues server control actions (start/stop/restart/config) to SQS for asynchronous processing
- **ec2ActionWorker/**: Processes server control actions from SQS queue (start/stop/restart/config updates)
- **iamProfileManager/**: Handles IAM instance profile management synchronously (associate/disassociate profiles)
- **getServerLogs/**: Fetches Minecraft logs from msd-logs service with JWT authentication and authorization
- **ec2ActionWorker/**: Processes server control actions from SQS queue (start/stop/restart/config updates)
- **iamProfileManager/**: Handles IAM instance profile management synchronously (associate/disassociate profiles)

### Lambda Layers (`layers/`)
- **authHelper/**: Cognito authentication utilities
- **ddbHelper/**: DynamoDB operations helper
- **ec2Helper/**: EC2 instance management utilities
  - CloudWatch alarm management (CPU-based and user-based shutdown)
  - EventBridge rule management for scheduled operations
  - Cron expression validation and formatting (5-field to 6-field EventBridge format)
  - IAM instance profile operations
- **utilHelper/**: Common utility functions including authorization checks

### Infrastructure (`cfn/`)
```
cfn/
├── template.yaml      # Main SAM template (orchestrates nested stacks)
├── templates/         # Nested CloudFormation templates
│   ├── dynamodb.yaml  # DynamoDB tables for server data
│   ├── cognito.yaml   # Authentication resources
│   ├── ec2.yaml       # EC2 IAM roles and instance profiles
│   ├── ssm.yaml       # SSM documents for bootstrap automation
│   ├── lambdas.yaml   # Lambda functions and layers
│   └── web.yaml       # S3 and CloudFront resources
└── samconfig.toml     # SAM deployment configuration
```

### CloudFormation Stack Dependencies
The main template orchestrates nested stacks with the following dependency chain:

1. **DynamoDBStack** (Base) - Creates core data tables
2. **CognitoStack** (Base) - Creates authentication resources
3. **EC2Stack** (Depends on DynamoDB) - Creates IAM roles and instance profiles
4. **SSMStack** (Depends on DynamoDB) - Creates bootstrap SSM documents
5. **LambdasStack** (Depends on Cognito, DynamoDB, EC2, SSM) - Creates all Lambda functions, layers, AppSync API, and SQS queues

### CloudFormation to Code Mapping

#### Lambda Functions
Each Lambda function in `lambdas/` is defined in `cfn/templates/lambdas.yaml`:
- **Source Code**: `lambdas/{functionName}/index.py`
- **Dependencies**: `lambdas/{functionName}/requirements.txt`
- **CloudFormation**: `AWS::Serverless::Function` resource in lambdas.yaml
- **Deployment**: SAM packages and uploads to S3, then deploys via CloudFormation

#### Lambda Layers
Each layer in `layers/` is defined in `cfn/templates/lambdas.yaml`:
- **Source Code**: `layers/{layerName}/{layerName}.py`
- **Build Process**: `make` command in layer directory (creates python/ subdirectory)
- **CloudFormation**: `AWS::Serverless::LayerVersion` resource in lambdas.yaml
- **Usage**: Lambda functions reference layers via `Layers` property

#### AppSync API
- **Schema**: `appsync/schema.graphql` defines GraphQL types, queries, mutations, subscriptions
- **Resolvers**: `appsync/resolvers/*.js` contains JavaScript resolver logic
- **CloudFormation**: `AWS::AppSync::GraphQLApi` and related resources in lambdas.yaml
- **Data Sources**: Lambda functions are connected as AppSync data sources

#### Bootstrap Scripts
Scripts in `scripts/` are deployed to S3 and executed on EC2 instances:
- **Versioning**: `scripts/VERSION` file (semantic versioning)
- **Deployment**: CircleCI uploads to `s3://{SupportBucket}/scripts/{version}/`
- **CloudFormation**: SSM document in `cfn/templates/ssm.yaml` references script URLs
- **Execution**: Lambda functions trigger SSM Run Command to execute bootstrap
- **IAM**: EC2 instance profile (defined in ec2.yaml) grants S3 read access to scripts

### Key AWS Resources
- **AppSync API**: GraphQL API with resolvers and data sources
- **Lambda Functions**: Backend compute resources
- **SQS Queues**: Asynchronous server action processing (main queue + DLQ)
- **DynamoDB Tables**: Data storage for server information
- **Cognito Resources**: User authentication and authorization
- **IAM Roles**: Permissions for various components
- **CloudWatch Resources**: Monitoring, metrics, and alarms for auto-shutdown (CPU-based and user-based)
- **CloudWatch Custom Metrics**: UserCount metric for tracking active player connections
- **EventBridge Rules**: Scheduled server start/stop events
- **S3 Bucket**: Frontend hosting
- **CloudFront Distribution**: Content delivery
- **EC2 Bootstrap Scripts**: Installs port_count.sh and cron job for metric collection

## Bootstrap Scripts Structure (`scripts/`)

Bootstrap scripts are executed on EC2 instances during initial setup and configuration updates. They are versioned and deployed to S3.

### Script Execution Order
Scripts run sequentially in numerical order:
1. **00-bootstrap-helper.sh**: Common functions and utilities for all scripts
2. **03-setup-cloudwatch.sh**: Installs and configures CloudWatch agent
3. **05-setup-metrics.sh**: Deploys msd-metrics Rust binary for metric collection
4. **07-setup-log-server.sh**: Deploys msd-logs Rust binary for log streaming
5. **09-setup-minecraft-service.sh**: Configures Minecraft as systemd service
6. **10-update-bootstrap-status.sh**: Updates bootstrap status in DynamoDB

### Script Versioning and Deployment
- **Version File**: `scripts/VERSION` (semantic versioning: MAJOR.MINOR.PATCH)
- **S3 Paths**:
  - `s3://{SupportBucket}/scripts/v{VERSION}/` - Specific version
  - `s3://{SupportBucket}/scripts/latest/` - Latest version (default)
- **Version Pinning**: Servers can pin to specific versions via DynamoDB config
- **Rollback**: Change `scriptVersion` in server config and re-bootstrap

### Script to CloudFormation Flow
1. **CircleCI**: Uploads scripts to S3 support bucket with version prefix
2. **SSM Document** (cfn/templates/ssm.yaml): Defines bootstrap automation
3. **Lambda Trigger**: `ec2BootWorker` or `ssmCommandWorker` invokes SSM Run Command
4. **EC2 Execution**: SSM agent downloads and executes scripts from S3
5. **IAM Permissions**: EC2 instance profile grants S3 read access (defined in ec2.yaml)
6. **Status Update**: Final script updates DynamoDB with bootstrap status

### Rust Binaries Deployed by Scripts
- **msd-metrics** (`rust/msd-metrics/`): Collects CPU, memory, network, user metrics
- **msd-logs** (`rust/msd-logs/`): HTTP server for streaming Minecraft logs
- **Deployment**: Pre-built binaries uploaded to S3, downloaded by bootstrap scripts
- **Build Target**: `x86_64-unknown-linux-musl` (static binaries, no dependencies)

## File Naming Conventions
- **Vue Components**: PascalCase (e.g., `ServerCard.vue`, `Header.vue`)
- **Python Files**: snake_case (e.g., `index.py`, `auth_helper.py`)
- **Lambda Functions**: camelCase directories (e.g., `ec2Discovery/`, `ec2CostCalculator/`)
- **CloudFormation**: kebab-case for resources, PascalCase for types

## Key Configuration Files
- **webapp/.env**: Frontend environment variables (VITE_ prefixed)
- **cfn/samconfig.toml**: SAM deployment parameters
- **appsync/schema.graphql**: GraphQL API schema
- **layers/*/requirements.txt**: Python dependencies for each layer
- **lambdas/*/requirements.txt**: Python dependencies for each function
- **.circleci/config.yml**: CI/CD pipeline configuration
- **scripts/VERSION**: Bootstrap script version (semantic versioning)
- **create-env-from-cfn-stack.sh**: Helper script to generate .env from CloudFormation outputs

### Environment Variables (webapp/.env)
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

## Import Patterns
- **Frontend**: Use relative imports for local components, absolute for external libraries
- **Backend**: Import shared utilities from Lambda layers using layer names
- **GraphQL**: Organize queries, mutations, and subscriptions in separate files

## Environment-Specific Resources
- Use CloudFormation parameters for environment-specific values
- Prefix environment variables with `VITE_` for frontend Vite access
- Store sensitive configuration in AWS Systems Manager Parameter Store

## Rust Services Structure (`rust/`)

### msd-metrics (`rust/msd-metrics/`)
- **Purpose**: Collects and sends server metrics to CloudWatch
- **Metrics**: CPU usage, memory usage, network I/O, active user count
- **Execution**: Runs as systemd service, sends metrics every minute
- **Build**: `cargo build --release --target x86_64-unknown-linux-musl`
- **Deployment**: Binary uploaded to S3, installed by bootstrap script 05-setup-metrics.sh

### msd-logs (`rust/msd-logs/`)
- **Purpose**: HTTP server for streaming Minecraft server logs
- **Port**: 25566
- **Authentication**: JWT token validation (Bearer token)
- **Endpoints**:
  - `GET /logs?lines=N` - Stream logs (max 1000 lines)
  - `GET /health` - Health check endpoint
- **Log Source**: Reads from journalctl (systemd journal)
- **Build**: `cargo build --release --target x86_64-unknown-linux-musl`
- **Deployment**: Binary uploaded to S3, installed by bootstrap script 07-setup-log-server.sh
- **Systemd**: Runs as service with auto-restart

### msd-ecs-metrics (`rust/msd-ecs-metrics/`)
- **Purpose**: ECS-specific metrics collection (if using ECS deployment)
- **Status**: Alternative deployment option (not used in EC2-based architecture)

## Deployment Flow Summary

### CI/CD Pipeline (CircleCI)

The project uses CircleCI for automated deployments with separate dev and prod pipelines.

#### Pipeline Structure (`.circleci/config.yml`)
```
.circleci/
└── config.yml         # CircleCI pipeline configuration
```

#### Workflows
- **dev-pipeline**: Runs on all branches except `main`
  - Uses `dev-aws` context (dev AWS credentials)
  - Deploys to dev environment
- **prod-pipeline**: Runs only on `main` branch
  - Uses `prod-aws` context (prod AWS credentials)
  - Deploys to production environment

#### Job Sequence
Both pipelines follow the same job sequence:

1. **build-and-deploy-backend**
   - Docker image: `cimg/python:3.13`
   - Steps:
     - Checkout code
     - Setup AWS CLI and SAM CLI
     - Setup Rust toolchain (x86_64-unknown-linux-musl target)
     - Validate all CloudFormation templates (main + nested)
     - Build SAM application (Lambda functions and layers)
     - Deploy CloudFormation stacks with nested stack orchestration
     - Build Rust binaries (msd-metrics, msd-logs)
     - Upload Rust binaries to S3 support bucket
     - Upload bootstrap scripts to S3 (versioned and latest)
     - Upload CloudWatch agent config to S3
   - Caching: SAM build cache for faster builds

2. **build-and-deploy-frontend** (requires backend completion)
   - Docker image: `cimg/node:20.18`
   - Steps:
     - Checkout code
     - Setup AWS CLI
     - Generate `.env` file from CloudFormation stack outputs
     - Install npm dependencies
     - Build Vue.js frontend (Vite)
     - Upload dist/ to S3 frontend bucket
     - Invalidate CloudFront distribution
   - Caching: npm dependencies

#### Environment Variables (CircleCI Project Settings)
- **Dev Environment**:
  - `ARTIFACTS_BUCKET_DEV`: S3 bucket for scripts and binaries
  - `FRONTEND_BUCKET_DEV`: S3 bucket for frontend hosting
  - `CLOUDFRONT_DISTRIBUTION_DEV`: CloudFront distribution ID
- **Prod Environment**:
  - `ARTIFACTS_BUCKET_PROD`: S3 bucket for scripts and binaries
  - `FRONTEND_BUCKET_PROD`: S3 bucket for frontend hosting
  - `CLOUDFRONT_DISTRIBUTION_PROD`: CloudFront distribution ID

#### Deployment Artifacts
CircleCI uploads the following to S3:
- **Rust Binaries**: `msd-metrics`, `msd-logs` (root of support bucket)
- **Bootstrap Scripts**: 
  - `s3://{SupportBucket}/scripts/v{VERSION}/` (versioned)
  - `s3://{SupportBucket}/scripts/latest/` (always latest)
- **CloudWatch Config**: `amazon-cloudwatch-agent.json`
- **Frontend Build**: `webapp/dist/` → S3 frontend bucket

#### Stack Rollback Handling
The pipeline includes automatic handling for failed CloudFormation stacks:
- **UPDATE_ROLLBACK_FAILED**: Automatically continues rollback
- **ROLLBACK_COMPLETE**: Fails with manual intervention instructions
- **Monitoring**: Displays stack events during deployment

#### Environment Configuration Script
`create-env-from-cfn-stack.sh`: Generates `webapp/.env` from CloudFormation outputs
- Queries stack outputs (API endpoint, Cognito IDs, etc.)
- Creates `.env` file with `VITE_` prefixed variables
- Used by frontend build process

### Infrastructure Deployment
1. **Build**: `sam build` packages Lambda functions and layers
2. **Deploy**: `sam deploy` creates/updates CloudFormation stacks
3. **Order**: DynamoDB → Cognito → EC2 → SSM → Lambdas (nested stack dependencies)
4. **Outputs**: Stack exports values (API endpoints, resource ARNs) for cross-stack references

### Frontend Deployment
1. **Build**: `npm run build` in webapp/ creates production bundle
2. **Upload**: CircleCI uploads dist/ to S3 frontend bucket
3. **CDN**: CloudFront distribution serves frontend from S3
4. **Config**: Environment variables injected at build time (VITE_ prefix)

### Bootstrap Script Deployment
1. **Version**: Update `scripts/VERSION` file
2. **Upload**: CircleCI uploads scripts to S3 support bucket
3. **Paths**: Both versioned (`v{VERSION}/`) and `latest/` paths
4. **Trigger**: Lambda functions invoke SSM Run Command on EC2 instances
5. **Execution**: EC2 downloads and runs scripts, installs Rust binaries

### Lambda Layer Build Process
1. **Navigate**: `cd layers/{layerName}`
2. **Build**: `make` (installs dependencies to python/ subdirectory)
3. **Package**: SAM packages layer with dependencies
4. **Deploy**: CloudFormation creates LayerVersion resource
5. **Reference**: Lambda functions include layer ARN in configuration