# EC2 to EC2-Docker Migration Plan - Minecraft Server Dashboard

## Problem Statement
Migrate the current EC2-based Minecraft server hosting architecture to a Docker-containerized approach on EC2 instances to achieve operational simplicity through containerization while maintaining cost efficiency and existing functionality for server management, monitoring, auto-shutdown, and user access control.

## Core Architecture Principles

### EBS Volume as Server Identity
- **Primary Key**: EBS Volume ID (`vol-xxxxxxxxxxxxxxxxx`)
- **Server Names**: Changeable display labels
- **User Permissions**: Tied to EBS Volume ID (stable across renames)
- **Containers**: Ephemeral - attach to persistent EBS volumes

### Multi-Instance Support
- **Backend**: Multiple EC2 instances for scaling/availability
- **Frontend**: Transparent instance selection - users only see server names
- **Load Balancing**: Automatic instance selection for new servers

### Data Persistence
- **EBS Volumes**: Pre-provisioned, contain Minecraft world data
- **Container Lifecycle**: Ephemeral containers attach to persistent volumes
- **Volume Mapping**: Each server maps to specific EBS volume ID

## Requirements
- **Infrastructure**: Docker on EC2 instances for cost efficiency
- **Persistence**: EBS volumes attached via Docker volume plugins
- **Auto-shutdown**: Container stopping (instances remain running)
- **Images**: Custom Docker images with Minecraft + monitoring
- **Migration**: Big bang replacement of current EC2 system
- **User Experience**: Server names only - infrastructure is transparent
- **Data Migration**: Fresh start - users re-invite to new Docker servers

## Data Model

### CoreTable Schema (Reused)
**Server Records:**
```
PK: SERVER#{ebs_volume_id}     # e.g., "SERVER#vol-1234567890abcdef0"
SK: METADATA

Attributes:
- ebs_volume_id (String): Primary stable identifier
- server_name (String): User-friendly name (changeable)
- display_id (String): Generated display ID (changeable)
- ec2_instance_id (String): Current EC2 instance hosting the container
- docker_container_id (String): Current Docker container ID (ephemeral)
- status (String): CREATING | RUNNING | STOPPED | FAILED | DELETING
- created_at, updated_at, created_by
- server_config (Map): Container specs, Minecraft settings
```

**User Permissions (Stable):**
```
PK: USER#{user_id}
SK: SERVER#{ebs_volume_id}     # Permanent - survives server renames
```

**Status Queries (Using existing GSI):**
```
SK: STATUS#{status}            # e.g., "STATUS#RUNNING"
PK: SERVER#{ebs_volume_id}
```

## Implementation Tasks

### Task 1: Docker Infrastructure Foundation
**Objective**: Create multi-instance Docker infrastructure with EBS volume plugin support

**Sub-tasks:**
1.1. **Create Multi-Instance EC2 Infrastructure**
   - Launch multiple EC2 instances (t3.xlarge) for container hosting
   - Configure auto-scaling groups for dynamic scaling
   - Set up cross-AZ distribution for high availability
   - Create instance tagging and identification system

1.2. **Configure Docker Engine on EC2 Instances**
   - Install Docker Engine on all EC2 instances
   - Configure Docker daemon settings for production
   - Set up Docker logging and monitoring
   - Configure Docker security and resource limits

1.3. **Install and Configure EBS Volume Plugins**
   - Install REX-Ray or AWS EBS CSI driver on all instances
   - Configure volume plugin for automatic EBS attachment
   - Test EBS volume attachment/detachment across instances
   - Set up volume naming conventions and management

1.4. **Create IAM Roles and Policies**
   - Create EC2 instance role with EBS + Docker permissions
   - Add CloudWatch metrics and logs permissions
   - Configure SSM permissions for remote container management
   - Set up cross-instance communication permissions

1.5. **Implement Instance Selection Logic**
   - Create InstanceManager class for selection strategies
   - Implement capacity-based selection algorithm
   - Add round-robin distribution logic
   - Create instance health monitoring and failover

1.6. **Set Up Docker Compose Templates**
   - Create dynamic Docker Compose file generation
   - Configure container networking and port management
   - Set up environment variable injection
   - Create container lifecycle management scripts

**Deliverables:**
- Multiple EC2 instances with Docker Engine
- EBS volume plugin configuration
- IAM roles for Docker container management
- Instance selection logic for load balancing

### Task 2: Custom Minecraft Docker Images
**Objective**: Build containerized Minecraft server with monitoring and EBS volume support

**Sub-tasks:**
2.1. **Create Base Dockerfile**
   - Set up OpenJDK 17 slim base image
   - Install system dependencies (curl, wget)
   - Configure working directory structure
   - Set up non-root user for security

2.2. **Integrate Rust Monitoring Application**
   - Copy compiled Rust monitoring binary
   - Add monitoring configuration files
   - Configure environment variables for monitoring
   - Set up monitoring startup scripts

2.3. **Configure Minecraft Server Setup**
   - Copy Minecraft server JAR file
   - Create server startup scripts
   - Configure server.properties template
   - Set up world data volume mount point

2.4. **Implement EBS Volume Integration**
   - Configure volume mount at `/minecraft/world`
   - Add EBS volume ID environment variable handling
   - Create volume attachment validation scripts
   - Test volume persistence across container restarts

2.5. **Add Health Checks and Monitoring**
   - Implement container health check endpoint
   - Configure Minecraft server connectivity checks
   - Add logging configuration
   - Set up graceful shutdown handling

2.6. **Build and Push to ECR**
   - Create ECR repository (`minecraft-dashboard/minecraft-server`)
   - Set up build pipeline with versioning
   - Enable vulnerability scanning
   - Create image tagging strategy (latest, v1.0, java17-{version})

**Deliverables:**
- Dockerfile with Java runtime + Rust monitoring app
- ECR repository with versioned images
- EBS volume attachment configuration
- Container health checks

### Task 3: EBS Volume to Server Mapping
**Objective**: Implement EBS-volume-ID-based server identification using CoreTable

**Sub-tasks:**
3.1. **Design CoreTable Schema Extensions**
   - Define server mapping record structure
   - Plan EBS volume ID as primary key format
   - Design status tracking with existing GSI
   - Create user permission mapping strategy

3.2. **Implement EBS Volume Management**
   - Create EBS volume creation functions
   - Add volume validation and format checking
   - Implement volume existence verification
   - Set up volume tagging for identification

3.3. **Build Server Mapping Helper Functions**
   - Create `ServerMappingHelper` class
   - Implement CRUD operations for server mappings
   - Add server creation workflow
   - Build server lookup and resolution functions

3.4. **Implement Server Rename Functionality**
   - Create rename function preserving EBS volume ID
   - Update display fields only (server_name, display_id)
   - Maintain user permissions stability
   - Add validation for name conflicts

3.5. **Add Instance Assignment Logic**
   - Implement instance selection for new servers
   - Add instance capacity tracking
   - Create instance failover handling
   - Build instance health monitoring

3.6. **Create Server Lifecycle Management**
   - Implement server creation flow
   - Add server deletion with volume preservation
   - Create status tracking and updates
   - Build server listing and filtering

**Deliverables:**
- Server creation flow: Create EBS → Map to server → Return volume ID
- Helper functions for EBS volume operations
- Validation for volume existence and format
- Server rename functionality (preserves volume ID)

### Task 4: Docker Helper Layer
**Objective**: Replace ec2Helper with dockerHelper supporting multi-instance operations

**Sub-tasks:**
4.1. **Create Docker Helper Layer Structure**
   - Set up Lambda layer directory structure
   - Create main DockerUtils class with instance awareness
   - Build InstanceManager for multi-instance operations
   - Set up requirements and build scripts

4.2. **Implement Core Docker Operations**
   - Create `create_minecraft_container()` with EBS volume support
   - Build `start_container()` using Docker Compose
   - Implement `stop_container()` preserving EBS volumes
   - Add `restart_container()` with container replacement

4.3. **Build Docker Compose Management**
   - Create dynamic Docker Compose file generation
   - Implement container configuration templates
   - Add environment variable injection (EBS_VOLUME_ID, SERVER_ID)
   - Configure resource allocation (CPU, memory limits)

4.4. **Implement Multi-Instance Management**
   - Build instance selection algorithms (capacity-based, round-robin)
   - Add instance health monitoring and failover
   - Implement cross-instance container discovery
   - Create instance load balancing logic

4.5. **Add Container Discovery and Management**
   - Implement Docker container tagging with EBS volume IDs
   - Build container lookup by EBS volume ID
   - Add container health checking and monitoring
   - Create container status tracking

4.6. **Build Server Rename and Management**
   - Implement `rename_server()` updating display fields only
   - Add server deletion preserving EBS volumes
   - Create server status updates and tracking
   - Build error handling for Docker-specific issues

**Deliverables:**
- Multi-instance Docker operations class
- Docker Compose templates with EBS volume attachment
- Instance selection and management logic
- Container discovery across instances

### Task 5: Server Action Processing
**Objective**: Update ec2ActionWorker for Docker operations with EBS volume IDs

**Sub-tasks:**
5.1. **Update Action Processing Logic**
   - Modify `ec2ActionWorker` to use EBS volume IDs
   - Replace EC2 operations with Docker container operations
   - Update action routing and parameter handling
   - Maintain backward compatibility during transition

5.2. **Implement Docker Container Operations**
   - Update start operation: get EBS volume, create container, start via Docker Compose
   - Update stop operation: stop container, preserve EBS volume
   - Update restart operation: restart container with same EBS volume
   - Add create operation: create EBS volume first, then container

5.3. **Update SQS Message Processing**
   - Modify SQS message format for EBS volume IDs
   - Update message parsing and validation
   - Add Docker-specific error handling and retries
   - Maintain existing queue structure and DLQ

5.4. **Implement Status Tracking**
   - Update status tracking to use EBS volume IDs
   - Modify GraphQL subscription updates
   - Update audit logging with EBS volume references
   - Add Docker-specific status states

5.5. **Add Error Handling and Recovery**
   - Handle Docker container not found scenarios
   - Add container creation failure recovery
   - Implement EBS volume attachment error handling
   - Create timeout handling for long-running operations

5.6. **Update Action Validation**
   - Validate EBS volume ID format and existence
   - Check EC2 instance capacity before operations
   - Validate user permissions with EBS volume IDs
   - Add pre-flight checks for Docker operations

**Deliverables:**
- Docker-based action processing (start/stop/restart/create/delete)
- SQS integration maintained
- Status tracking with EBS volume IDs
- Error handling for Docker-specific issues

### Task 6: Server Discovery and Listing
**Objective**: Update ec2Discovery for multi-instance Docker discovery with EBS volume mapping

**Sub-tasks:**
6.1. **Update User Permission Resolution**
   - Modify user permission queries to use EBS volume IDs
   - Update permission validation logic
   - Add EBS volume ID to user membership resolution
   - Maintain admin/user role functionality

6.2. **Implement Multi-Instance Server Discovery**
   - Build cross-instance Docker container discovery
   - Add instance-aware container lookup
   - Implement parallel instance querying for performance
   - Create unified server list aggregation

6.3. **Build Server Info Transformation**
   - Transform EBS volume mappings to server info objects
   - Add server name and display ID handling
   - Include instance information for internal use
   - Map Docker container status to server states

6.4. **Update Auto-Configuration System**
   - Adapt auto-configuration for Docker containers
   - Update default configuration templates
   - Add Docker-specific validation rules
   - Create container-specific default settings

6.5. **Implement Server Validation**
   - Check Docker container health instead of EC2 instance status
   - Validate container configuration
   - Verify EBS volume attachment status
   - Add container health check validation

6.6. **Add Performance Optimization**
   - Implement caching for frequently accessed server info
   - Add batch operations for multiple server queries
   - Optimize cross-instance discovery performance
   - Create efficient server filtering and sorting

**Deliverables:**
- Cross-instance server discovery
- EBS volume ID to server info transformation
- User permission validation with volume IDs
- Auto-configuration for Docker containers

### Task 7: Docker-based Monitoring Integration
**Objective**: Containerized monitoring with multi-instance CloudWatch metrics

**Sub-tasks:**
7.1. **Adapt Rust Monitoring for Containers**
   - Update Rust app to use EBS volume ID as primary identifier
   - Add instance ID detection from EC2 metadata
   - Configure container-specific metric collection
   - Update CloudWatch dimension handling

7.2. **Configure CloudWatch Metrics**
   - Set up new namespace: `MinecraftDashboard/Docker`
   - Configure dimensions: `EBSVolumeId`, `InstanceId`
   - Update metric names for Docker environment
   - Add container-specific metrics (ContainerHealth)

7.3. **Update Metric Collection Lambda**
   - Modify `ec2StateHandler` Lambda for Docker metrics
   - Update metric parsing for new dimensions
   - Add EBS volume ID extraction from metrics
   - Update GraphQL subscription publishing

7.4. **Implement Real-time Monitoring**
   - Update real-time metric subscriptions
   - Add container health monitoring
   - Implement Docker container state change handling
   - Create container restart detection

7.5. **Add Container Health Checks**
   - Implement Docker container health monitoring
   - Add container exit code tracking
   - Create volume mount health verification
   - Build network connectivity monitoring

7.6. **Update Monitoring Dashboard**
   - Modify frontend to display Docker-specific metrics
   - Add instance information to monitoring views
   - Update metric visualization for containers
   - Create Docker container status indicators

**Deliverables:**
- Rust monitoring app adapted for containers
- CloudWatch metrics with EBS volume ID + instance dimensions
- Real-time metric collection and GraphQL subscriptions
- Container health monitoring

### Task 8: Auto-shutdown Mechanisms
**Objective**: Migrate CloudWatch alarms and scheduled operations to Docker

**Sub-tasks:**
8.1. **Update CloudWatch Alarm Configuration**
   - Migrate CPU-based alarms to use Docker metrics
   - Update alarm dimensions to use EBS volume ID + instance
   - Configure alarm actions for Docker container stopping
   - Test alarm triggering and recovery

8.2. **Implement Docker Container Shutdown Logic**
   - Create Lambda function for Docker container shutdown
   - Implement container stop via Docker Compose
   - Add graceful shutdown with player notifications
   - Handle container stop and EBS volume preservation

8.3. **Update User-based Auto-shutdown**
   - Migrate player count monitoring to container metrics
   - Update ActivePlayers metric collection from containers
   - Configure user-based shutdown alarms
   - Add edge case handling (players joining during shutdown)

8.4. **Migrate Scheduled Operations**
   - Update EventBridge rules to use EBS volume IDs
   - Modify scheduled start/stop Lambda functions
   - Update rule targets for Docker operations
   - Test scheduled operations with Docker containers

8.5. **Implement Shutdown Validation**
   - Add pre-shutdown validation checks
   - Verify no active players before shutdown
   - Check for ongoing operations or maintenance
   - Create shutdown confirmation and logging

8.6. **Add Recovery and Failover**
   - Implement automatic restart on container failures
   - Add instance failover for shutdown operations
   - Create monitoring for shutdown success/failure
   - Build alerting for failed shutdown attempts

**Deliverables:**
- Docker container monitoring with CloudWatch alarms
- CPU/user-based shutdown via container stop
- Scheduled operations with EBS volume ID references
- EventBridge rules for Docker containers

### Task 9: Configuration Management
**Objective**: Docker container configuration with EBS volume management

**Sub-tasks:**
9.1. **Update Server Configuration System**
   - Modify server config to work with Docker containers
   - Update configuration validation for container environments
   - Add Docker-specific configuration options
   - Maintain backward compatibility during migration

9.2. **Implement Container Configuration Management**
   - Create container configuration update workflows
   - Implement container recreation for config changes
   - Add configuration change detection
   - Build container rollback capabilities

9.3. **Handle EBS Volume Configuration**
   - Implement EBS volume resize handling (requires container restart)
   - Add volume type and performance configuration
   - Create volume backup and snapshot management
   - Build volume migration between availability zones

9.4. **Update Resource Management**
   - Adapt resource allocation for Docker containers
   - Update CPU and memory limit handling
   - Add container-specific resource constraints
   - Implement resource validation and testing

9.5. **Implement Configuration Validation**
   - Add Docker-specific configuration validation
   - Check container resource limits
   - Validate container image availability
   - Verify EBS volume compatibility

9.6. **Build Configuration Deployment**
   - Create configuration deployment workflows
   - Implement rolling updates for configuration changes
   - Add configuration change monitoring
   - Build rollback procedures for failed deployments

**Deliverables:**
- Container configuration updates for changes
- EBS volume resize handling (requires container restart)
- Resource management for Docker containers
- Configuration validation for Docker-specific settings

### Task 10: User Access Control Migration
**Objective**: Migrate user permissions to EBS volume ID-based system

**Sub-tasks:**
10.1. **Plan Permission Migration Strategy**
   - Design fresh start approach for user permissions
   - Plan user communication and re-invitation process
   - Create migration timeline and rollback procedures
   - Document permission mapping changes

10.2. **Clear Existing Permissions**
   - Clear all existing EC2-based server memberships
   - Preserve user accounts and admin roles
   - Log permission reset actions for audit
   - Create backup of existing permissions for reference

10.3. **Update Authorization System**
   - Modify authorization checks to use EBS volume IDs
   - Update permission validation logic
   - Add EBS volume ID to permission queries
   - Test authorization with new identifier system

10.4. **Update GraphQL Resolvers**
   - Modify all server-related GraphQL resolvers
   - Update server ID handling in mutations and queries
   - Add EBS volume ID validation in resolvers
   - Update error handling for Docker-specific scenarios

10.5. **Implement User Invitation System**
   - Create new user invitation system for Docker servers
   - Update invitation emails and notifications
   - Add EBS volume ID validation in invitations
   - Build invitation acceptance workflows

10.6. **Test Access Control System**
   - Test user permissions with EBS volume IDs
   - Validate admin and user role functionality
   - Test server access across different instances
   - Verify permission stability across server renames

**Deliverables:**
- Permission reset strategy (fresh start)
- Authorization checks with EBS volume IDs
- GraphQL resolver updates
- User invitation system for Docker servers

### Task 11: Frontend Integration and Testing
**Objective**: Update frontend for EBS volume ID-based operations and complete testing

**Sub-tasks:**
11.1. **Update GraphQL Operations**
   - Update all GraphQL queries to handle EBS volume IDs
   - Modify mutations to use EBS volume IDs internally
   - Update subscriptions for Docker-based real-time updates
   - Add error handling for Docker-specific responses

11.2. **Update Frontend Server Management**
   - Modify server display to show server names/display IDs
   - Update server operations to use EBS volume IDs internally
   - Add instance information display (for admin users)
   - Update server creation workflows

11.3. **Implement Docker-specific Error Handling**
   - Add error handling for Docker container not found
   - Handle container creation failure scenarios
   - Add container startup timeout handling
   - Create user-friendly error messages for Docker issues

11.4. **Update Real-time Features**
   - Modify real-time metrics display for containerized monitoring
   - Update server status indicators for Docker containers
   - Add container health status display
   - Update action status tracking for Docker operations

11.5. **Perform Integration Testing**
   - Test complete server lifecycle (create, start, stop, delete)
   - Validate user permissions with EBS volume IDs
   - Test multi-instance operations transparency
   - Verify real-time updates and monitoring

11.6. **Conduct Performance Testing**
   - Load test Docker container operations
   - Measure container startup times vs current EC2
   - Test concurrent server operations
   - Monitor resource utilization and costs

11.7. **End-to-End System Testing**
   - Test complete user workflows from frontend to Docker
   - Validate data persistence across container restarts
   - Test auto-shutdown and scheduled operations
   - Verify monitoring and alerting functionality

**Deliverables:**
- GraphQL queries/mutations updated for EBS volume IDs
- Error handling for Docker-specific scenarios
- End-to-end testing of complete Docker system
- Performance monitoring and optimization

## Success Criteria

### Technical
- [ ] All servers identified by EBS volume IDs
- [ ] Multi-instance Docker deployment operational
- [ ] Container startup time < 1 minute
- [ ] EBS volume attachment working reliably
- [ ] Real-time monitoring functional

### User Experience
- [ ] Server names changeable without breaking permissions
- [ ] Transparent instance management (users unaware)
- [ ] Same GraphQL API interface maintained
- [ ] Performance equivalent or better than current EC2

### Operational
- [ ] Auto-shutdown policies working with Docker
- [ ] Scheduled operations functional
- [ ] Cost optimization maintained (67% less than ECS)
- [ ] Monitoring and alerting operational

## Migration Timeline
1. **Weeks 1-2**: Tasks 1-3 (Infrastructure + Images + Mapping)
2. **Weeks 3-4**: Tasks 4-6 (Docker Helper + Actions + Discovery)
3. **Weeks 5-6**: Tasks 7-9 (Monitoring + Auto-shutdown + Config)
4. **Weeks 7-8**: Tasks 10-11 (Permissions + Frontend + Testing)

## Cost Benefits
- **67% cheaper than ECS**: $16.78/month vs $22.70/month per server
- **Better resource utilization**: 8 servers per t3.xlarge instance
- **Operational simplicity**: Containerized deployments with Docker Compose
- **Scalability**: Easy horizontal scaling by adding EC2 instances

## Risk Mitigation
- **EBS Volume Attachment**: Extensive testing of Docker volume plugins
- **Container Startup**: Optimize image size and startup scripts
- **Data Loss**: Comprehensive backup strategy for EBS volumes
- **Performance**: Load testing with multiple concurrent containers
- **Instance Failures**: Multi-instance deployment with automatic failover
- **Rollback**: Maintain current EC2 infrastructure until Docker fully validated
