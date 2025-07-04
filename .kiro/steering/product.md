# Product Overview

The Minecraft Server Dashboard is a comprehensive web application that enables users to manage and monitor Minecraft servers hosted on AWS EC2 instances.

## Key Features
- **Server Management**: Start, stop, restart Minecraft servers on EC2 instances
- **Real-time Monitoring**: Live metrics for CPU, memory, network, and active players
- **Cost Tracking**: Monthly cost analysis and optimization recommendations
- **User Access Control**: Multi-user access with admin/user roles via Cognito
- **Automated Policies**: CPU-based and schedule-based auto-shutdown
- **Configuration Management**: Server settings and startup commands
- **Authentication**: Google OAuth integration via Amazon Cognito

## Target Users
- Minecraft server administrators
- Gaming communities managing shared servers
- Cost-conscious users wanting automated server management

## Architecture
Serverless web application with Vue.js frontend and AWS backend services (AppSync, Lambda, DynamoDB, Cognito, CloudFront).

## Core User Workflows
1. **Authentication**: Users log in via Google OAuth through Cognito
2. **Server Discovery**: List available Minecraft servers from EC2 instances
3. **Server Control**: Start/stop/restart servers with real-time status updates
4. **Monitoring**: View live performance metrics and player activity
5. **Cost Management**: Track monthly costs and configure auto-shutdown policies
6. **User Management**: Admins can grant access to specific servers for other users

## Business Value
- **Cost Optimization**: Automated shutdown policies reduce unnecessary EC2 costs
- **Operational Efficiency**: Centralized management of multiple Minecraft servers
- **User Experience**: Real-time updates and intuitive web interface
- **Security**: Proper authentication and authorization for server access