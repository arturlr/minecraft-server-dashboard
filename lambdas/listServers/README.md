# ListServers Lambda Function

This Lambda function lists Minecraft servers with enhanced tag validation functionality.

## Features

### Core Functionality
- Lists EC2 instances based on user permissions (admin or group-based access)
- Retrieves instance details including type, status, and resource information
- Calculates monthly running time and costs

### Tag Validation & Auto-Configuration (New)
The function now includes parallel tag validation and automatic configuration for servers without shutdown settings:

#### Auto-Configuration Features
1. **Default Shutdown Configuration**
   - Automatically applies CPU-based shutdown when no method is configured
   - Default settings: 5% CPU threshold, 30-minute evaluation period
   - Creates CloudWatch alarm for automatic shutdown
   - Sets alarm type to `CPUUtilization`

2. **Default Minecraft Server Configuration**
   - Applies default run command: `java -Xmx2G -Xms1G -jar server.jar nogui`
   - Sets default working directory: `/home/minecraft/server`
   - Only applied when missing from existing configuration

#### Validation Checks
1. **Shutdown Method Configuration**
   - Validates that a shutdown method is configured
   - Supports: `Schedule`, `CPUUtilization`, `Connections`
   - Auto-configures CPU-based shutdown if missing

2. **Schedule-Based Validation**
   - Ensures stop schedule expression is present when method is `Schedule`
   - Warns if start schedule is missing (manual start required)
   - Validates cron expression format

3. **Metric-Based Validation**
   - Validates alarm threshold > 0 for CPU/Connection monitoring
   - Validates evaluation period > 0
   - Ensures proper numeric types

4. **Minecraft Server Configuration**
   - Checks for run command configuration
   - Validates working directory setting
   - Auto-configures defaults if missing

#### Validation Results
Each server now includes:
- `configStatus`: `complete`, `incomplete`, `invalid`, `auto-configured`, `configuration-failed`, or `error`
- `configValid`: Boolean indicating if configuration is valid
- `configWarnings`: Array of warning messages
- `configErrors`: Array of error messages
- `autoConfigured`: Boolean indicating if default configuration was applied

## Response Format

### Fully Configured Server
```json
{
  "id": "i-1234567890abcdef0",
  "name": "My Minecraft Server",
  "userEmail": "user@example.com",
  "type": "t3.medium",
  "state": "running",
  "vCpus": 2,
  "memSize": 4096,
  "diskSize": 20,
  "publicIp": "1.2.3.4",
  "initStatus": "ok",
  "iamStatus": "ok",
  "launchTime": "01/15/2025 - 10:30:00",
  "runningMinutes": 1440,
  "configStatus": "complete",
  "configValid": true,
  "configWarnings": [],
  "configErrors": [],
  "autoConfigured": false
}
```

### Auto-Configured Server
```json
{
  "id": "i-0987654321fedcba0",
  "name": "New Minecraft Server",
  "configStatus": "auto-configured",
  "configValid": true,
  "configWarnings": [
    "Default shutdown configuration applied: CPU-based (5% threshold, 30min evaluation)",
    "Default Minecraft server configuration applied: run command, working directory"
  ],
  "configErrors": [],
  "autoConfigured": true
}
```

### Server with Configuration Issues
```json
{
  "id": "i-abcdef1234567890",
  "name": "Problematic Server",
  "configStatus": "invalid",
  "configValid": false,
  "configWarnings": [],
  "configErrors": [
    "Invalid alarm threshold: 0.0. Must be greater than 0",
    "Invalid evaluation period: 0. Must be greater than 0"
  ],
  "autoConfigured": false
}
```

## Performance

- Uses ThreadPoolExecutor with up to 10 concurrent threads
- Parallel processing of:
  - Instance type information
  - Instance status checks
  - Tag validation (new)
- Optimized for handling multiple instances efficiently

## Dependencies

- `authHelper`: Authentication and authorization
- `ec2Helper`: EC2 operations and tag management
- `utilHelper`: Utility functions
- `boto3`: AWS SDK
- `concurrent.futures`: Parallel processing

## Environment Variables

- `TAG_APP_VALUE`: Application tag value for filtering instances
- `COGNITO_USER_POOL_ID`: Cognito User Pool ID for authentication
- `EC2_INSTANCE_PROFILE_ARN`: Expected IAM instance profile ARN

## Error Handling

- Graceful handling of missing tags with default values
- Comprehensive error logging for debugging
- Fallback to error status when validation fails
- Non-blocking validation (doesn't prevent server listing)