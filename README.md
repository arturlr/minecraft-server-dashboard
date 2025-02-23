# Minecraft Server Dashboard

A comprehensive web application for managing and monitoring Minecraft servers on AWS, featuring real-time metrics, server control, and user management.

The Minecraft Server Dashboard is a powerful tool designed to simplify the management and monitoring of Minecraft servers hosted on Amazon Web Services (AWS). This application provides a user-friendly interface for server administrators and players alike, offering real-time metrics, server control capabilities, and user management features.

Key features of the Minecraft Server Dashboard include:
- Real-time server metrics (CPU, memory, network usage, and active players)
- Server start, stop, and restart functionality
- User invitation and management system
- Cost tracking and optimization recommendations
- Integration with AWS services (EC2, CloudWatch, AppSync, Cognito)
- Responsive web interface built with Vue.js

## Repository Structure

The repository is organized into several key directories:

- `amplify/`: Contains Amplify backend configuration and API definitions
- `appsync/`: Includes AppSync resolvers and GraphQL schema
- `cfn/`: Houses CloudFormation templates for infrastructure deployment
- `dashboard/`: Contains the Vue.js frontend application
- `lambdas/`: Includes Lambda functions for various server operations
- `layers/`: Contains shared code layers used by Lambda functions

Key Files:
- `amplify.yml`: Amplify build and deployment configuration
- `appconfig.sh`: Script for setting up application configuration
- `cfn/template.yaml`: Main CloudFormation template for the application stack
- `dashboard/src/main.js`: Entry point for the Vue.js application
- `lambdas/configServer/index.py`: Lambda function for server configuration

Important integration points:
- GraphQL API (`appsync/schema.graphql`): Defines the API structure for client-server communication
- Cognito User Pool: Handles user authentication and authorization
- AppSync Resolvers: Connect GraphQL operations to Lambda functions and DynamoDB

## Usage Instructions

### Installation

Prerequisites:
- Node.js (v14 or later)
- AWS CLI (configured with appropriate credentials)
- Amplify CLI (v5 or later)

Steps:
1. Clone the repository:
   ```
   git clone <repository-url>
   cd minecraft-server-dashboard
   ```
2. Install dependencies:
   ```
   npm install
   ```
3. Initialize Amplify:
   ```
   amplify init
   ```
4. Deploy the backend:
   ```
   amplify push
   ```
5. Configure the application:
   ```
   ./appconfig.sh
   ```

### Getting Started

1. Start the development server:
   ```
   npm run serve
   ```
2. Open a web browser and navigate to `http://localhost:8080`
3. Log in using your Cognito credentials or sign up for a new account

### Configuration Options

- Environment variables can be set in the `.env` file in the `dashboard/` directory
- AWS resource configurations can be adjusted in the CloudFormation templates (`cfn/templates/`)

### Common Use Cases

1. Starting a Minecraft server:
   - Log in to the dashboard
   - Click on the "Start Server" button for the desired server instance
   - Wait for the server to initialize (progress can be monitored in real-time)

2. Inviting a new user:
   - Navigate to the server management page
   - Click on "Invite User"
   - Enter the user's email address and submit
   - The user will receive an invitation email with further instructions

3. Monitoring server performance:
   - View real-time metrics on the server dashboard
   - Check CPU usage, memory utilization, network traffic, and active player count
   - Set up custom CloudWatch alarms for specific metrics

### Testing & Quality

To run the test suite:
```
npm run test
```

### Troubleshooting

Common Issue: Server fails to start
1. Check the CloudWatch logs for the specific EC2 instance
2. Verify that the instance has the correct IAM role attached
3. Ensure that the necessary security group rules are in place

Debugging:
- Enable verbose logging in Lambda functions by setting the `LOG_LEVEL` environment variable to `DEBUG`
- Check CloudWatch Logs for each Lambda function and EC2 instance
- Use AWS X-Ray for tracing requests through the application

Performance Optimization:
- Monitor Lambda function duration and memory usage in CloudWatch
- Adjust Lambda function memory allocation as needed
- Consider using provisioned concurrency for frequently invoked functions

## Data Flow

The Minecraft Server Dashboard application follows a serverless architecture with the following data flow:

1. User interacts with the Vue.js frontend application
2. Frontend makes GraphQL API calls to AWS AppSync
3. AppSync resolvers invoke Lambda functions or interact directly with DynamoDB
4. Lambda functions perform operations on EC2 instances, CloudWatch metrics, and other AWS services
5. Real-time updates are pushed to the frontend via AppSync subscriptions

```
[User] <-> [Vue.js Frontend] <-> [AppSync API] <-> [Lambda Functions] <-> [AWS Services (EC2, CloudWatch, etc.)]
                                      ^
                                      |
                                [DynamoDB Tables]
```

Note: The application uses AWS Cognito for user authentication and authorization throughout the entire flow.

## Deployment

Prerequisites:
- AWS Account with appropriate permissions
- AWS CLI configured with admin credentials
- Amplify CLI installed and configured

Deployment Steps:
1. Clone the repository and navigate to the project root
2. Run `amplify init` to initialize the Amplify project
3. Run `amplify push` to deploy the backend resources
4. Execute `./appconfig.sh` to configure the application
5. Navigate to the `dashboard/` directory and run `npm run build`
6. Deploy the frontend build to the S3 bucket created by CloudFormation

## Infrastructure

The Minecraft Server Dashboard uses the following key AWS resources:

Lambda:
- `configServer`: Configures and initializes Minecraft servers on EC2 instances
- `eventResponse`: Handles EC2 instance state changes and updates server metrics
- `getMonthlyCost`: Retrieves monthly cost data for servers
- `listServers`: Lists EC2 instances based on user permissions
- `serverAction`: Performs various server actions (start, stop, restart, etc.)

DynamoDB:
- `ServersTable`: Stores server configuration and state information
- `LogAuditTable`: Stores audit logs for server actions

AppSync:
- GraphQL API with resolvers for server management operations

Cognito:
- User Pool for authentication and authorization
- Identity Pool for AWS service access

EC2:
- Instances for running Minecraft servers

CloudWatch:
- Alarms for monitoring server performance
- Logs for Lambda functions and EC2 instances

S3:
- `WebAppBucket`: Hosts the frontend application files
- `SupportBucket`: Stores configuration and support files

CloudFront:
- Distribution for serving the frontend application