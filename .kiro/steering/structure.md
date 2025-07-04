# Project Structure

## Root Level Organization
```
├── dashboard/          # Vue.js frontend application
├── cfn/               # AWS SAM CloudFormation templates
├── lambdas/           # AWS Lambda function source code
├── layers/            # AWS Lambda layers for shared code
├── appsync/           # GraphQL schema and resolvers
├── docs/              # Project documentation
├── images/            # Screenshots and diagrams
└── public/            # Static web assets
```

## Frontend Structure (`dashboard/`)
```
dashboard/
├── src/
│   ├── components/    # Reusable Vue components
│   ├── views/         # Page-level Vue components
│   ├── stores/        # Vuex/Pinia state management
│   ├── router/        # Vue Router configuration
│   ├── graphql/       # GraphQL queries, mutations, subscriptions
│   ├── layouts/       # Layout components
│   └── assets/        # Static assets (CSS, images)
├── public/            # Public static files
├── .env               # Environment variables (VITE_ prefixed)
└── package.json       # Dependencies and scripts
```

### Key Frontend Components
- **Authentication Module**: User login/logout and session management
- **Server Dashboard**: Server metrics and status display
- **Server Control Panel**: Start/stop/restart functionality
- **Configuration Manager**: Server settings editor
- **User Management**: Server access control
- **Cost Monitor**: Usage costs and projections

## Backend Structure

### Lambda Functions (`lambdas/`)
- **eventResponse/**: Processes EC2 state changes and metrics
- **getMonthlyCost/**: Retrieves AWS cost data from Cost Explorer API
- **listServers/**: Lists available Minecraft servers from EC2
- **serverAction/**: Handles server start/stop/restart operations via EC2 and SSM

### Lambda Layers (`layers/`)
- **authHelper/**: Cognito authentication utilities
- **dynHelper/**: DynamoDB operations helper
- **ec2Helper/**: EC2 instance management utilities
- **utilHelper/**: Common utility functions

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
- **DynamoDB Tables**: Data storage for server information
- **Cognito Resources**: User authentication and authorization
- **IAM Roles**: Permissions for various components
- **CloudWatch Resources**: Monitoring and metrics
- **S3 Bucket**: Frontend hosting
- **CloudFront Distribution**: Content delivery

## File Naming Conventions
- **Vue Components**: PascalCase (e.g., `ServerCard.vue`, `Header.vue`)
- **Python Files**: snake_case (e.g., `index.py`, `auth_helper.py`)
- **Lambda Functions**: camelCase directories (e.g., `listServers/`, `getMonthlyCost/`)
- **CloudFormation**: kebab-case for resources, PascalCase for types

## Key Configuration Files
- **dashboard/.env**: Frontend environment variables (VITE_ prefixed)
- **cfn/samconfig.toml**: SAM deployment parameters
- **appsync/schema.graphql**: GraphQL API schema
- **layers/*/requirements.txt**: Python dependencies for each layer
- **lambdas/*/requirements.txt**: Python dependencies for each function

### Environment Variables (dashboard/.env)
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