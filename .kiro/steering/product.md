# Product Overview

The Minecraft Server Dashboard is a comprehensive web application that enables users to manage and monitor Minecraft servers hosted on AWS EC2 instances.

## Key Features
- **Server Management**: Start, stop, restart Minecraft servers on EC2 instances with asynchronous processing
- **Real-time Monitoring**: Live metrics for CPU, memory, network, and active players
- **Log Streaming**: Real-time Minecraft server logs via HTTP API with JWT authentication
- **Action Status Tracking**: Real-time updates on server action progress (processing/completed/failed)
- **Cost Tracking**: Monthly cost analysis and optimization recommendations
- **User Access Control**: Multi-user access with admin/user roles via Cognito
- **Automated Policies**: CPU-based, connection-based, and schedule-based auto-shutdown with CloudWatch alarms
- **User-Based Auto-Shutdown**: Automatic shutdown when player connections fall below threshold for sustained period (prevents idle server costs)
- **Auto-Configuration**: Automatic default configuration for new servers (CPU-based shutdown, Minecraft commands)
- **Configuration Validation**: Real-time validation of server settings with warnings and errors
- **Configuration Management**: Server settings, startup commands, and scheduled operations
- **Authentication**: Google OAuth integration via Amazon Cognito
- **Systemd Integration**: Minecraft servers run as systemd services with auto-restart and proper logging

## Target Users
- Minecraft server administrators
- Gaming communities managing shared servers
- Cost-conscious users wanting automated server management

## Architecture
Serverless web application with Vue.js frontend and AWS backend services (AppSync, Lambda, DynamoDB, Cognito, CloudFront).

## Core User Workflows
1. **Authentication**: Users log in via Google OAuth through Cognito
2. **Server Discovery**: List available Minecraft servers from EC2 instances with automatic validation
3. **Auto-Configuration**: New servers automatically receive default shutdown and Minecraft configurations
4. **Server Control**: Start/stop/restart servers with asynchronous processing and real-time status updates
5. **Configuration Validation**: Real-time feedback on configuration issues with warnings and errors
6. **Monitoring**: View live performance metrics and player activity
7. **Cost Management**: Track monthly costs and configure auto-shutdown policies (CPU/connections/schedule)
8. **User-Based Auto-Shutdown**: Configure automatic shutdown when player count falls below threshold for sustained period
9. **Scheduled Operations**: Configure automatic server start/stop times using cron expressions
10. **User Management**: Admins can grant access to specific servers for other users

## Business Value
- **Cost Optimization**: Automated shutdown policies reduce unnecessary EC2 costs
- **Operational Efficiency**: Centralized management of multiple Minecraft servers
- **User Experience**: Real-time updates and intuitive web interface
- **Security**: Proper authentication and authorization for server access