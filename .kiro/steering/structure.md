# Project Structure

## Root Level Organization
```
├── webapp/            # Vue.js frontend application
├── cfn/               # AWS SAM CloudFormation templates
├── lambdas/           # AWS Lambda function source code
├── layers/            # AWS Lambda layers for shared code
├── appsync/           # GraphQL schema and resolvers
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
├── template.yaml      # Main SAM template
├── templates/         # Nested CloudFormation templates
│   ├── appsync.yaml   # GraphQL API resources
│   ├── cognito.yaml   # Authentication resources
│   ├── ec2.yaml       # EC2 and networking resources
│   ├── lambdas.yaml   # Lambda functions and layers
│   └── web.yaml       # S3 and CloudFront resources
└── samconfig.toml     # SAM deployment configuration
```

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