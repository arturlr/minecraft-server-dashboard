# EC2 to ECS Migration Plan - Minecraft Server Dashboard

## Problem Statement
Migrate the current EC2-based Minecraft server hosting architecture to ECS (Elastic Container Service) to achieve operational simplicity through containerization while maintaining existing functionality for server management, monitoring, auto-shutdown, and user access control.

## Core Architecture Principles

### EBS Volume as Server Identity
- **Primary Key**: EBS Volume ID (`vol-xxxxxxxxxxxxxxxxx`)
- **Server Names**: Changeable display labels
- **User Permissions**: Tied to EBS Volume ID (stable across renames)
- **Containers**: Ephemeral - attach to persistent EBS volumes

### Multi-Cluster Support
- **Backend**: Multiple ECS clusters for scaling/availability
- **Frontend**: Transparent cluster selection - users only see server names
- **Load Balancing**: Automatic cluster selection for new servers

### Data Persistence
- **EBS Volumes**: Pre-provisioned, contain Minecraft world data
- **Container Lifecycle**: Ephemeral containers attach to persistent volumes
- **Volume Mapping**: Each server maps to specific EBS volume ID

## Requirements
- **Infrastructure**: ECS with EC2 launch type for infrastructure control
- **Persistence**: EBS volumes attached via Docker volume plugins
- **Auto-shutdown**: Task stopping (clusters remain running)
- **Images**: Custom Docker images with Minecraft + monitoring
- **Migration**: Big bang replacement of EC2 system
- **User Experience**: Server names only - infrastructure is transparent
- **Data Migration**: Fresh start - users re-invite to new ECS servers

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
- ecs_service_arn (String): Current ECS service ARN (ephemeral)
- ecs_cluster_name (String): Current ECS cluster name
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

### Task 1: ECS Infrastructure Foundation
**Objective**: Create multi-cluster ECS infrastructure with EBS volume plugin support

**Sub-tasks:**
1.1. **Create Multi-Cluster ECS Infrastructure**
   - Create primary ECS cluster (`minecraft-dashboard-cluster-1`)
   - Create secondary ECS cluster (`minecraft-dashboard-cluster-2`)
   - Configure auto-scaling groups for each cluster
   - Set up cross-AZ distribution for high availability

1.2. **Configure ECS-Optimized EC2 Instances**
   - Launch ECS-optimized AMI instances (t3.medium, t3.large)
   - Install Docker volume plugins (REX-Ray or AWS EBS CSI driver)
   - Configure ECS agent settings
   - Set up instance auto-scaling policies

1.3. **Create IAM Roles and Policies**
   - Create ECSTaskRole with CloudWatch + EBS permissions
   - Create ECSTaskExecutionRole with ECR + logs permissions
   - Create ECSInstanceRole with ECS agent + volume permissions
   - Attach policies and test permissions

1.4. **Implement Cluster Selection Logic**
   - Create ClusterManager class for selection strategies
   - Implement capacity-based selection algorithm
   - Add round-robin distribution logic
   - Create cluster health monitoring

1.5. **Configure Docker Volume Plugin**
   - Install and configure REX-Ray/EBS CSI driver on instances
   - Test EBS volume attachment/detachment
   - Set up volume naming conventions
   - Create volume management scripts

**Deliverables:**
- Multiple ECS clusters (primary + secondary for HA)
- ECS-optimized EC2 instances with Docker volume plugins
- IAM roles for ECS tasks/services/instances
- Cluster selection logic for load balancing

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

3.5. **Add Validation and Error Handling**
   - Validate EBS volume ID format (vol-xxxxxxxxxxxxxxxxx)
   - Check volume availability zone compatibility
   - Prevent duplicate volume mappings
   - Handle volume attachment failures

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

### Task 4: ECS Helper Layer
**Objective**: Replace ec2Helper with ecsHelper supporting multi-cluster operations

**Sub-tasks:**
4.1. **Create ECS Helper Layer Structure**
   - Set up Lambda layer directory structure
   - Create main EcsUtils class with cluster awareness
   - Build ClusterManager for multi-cluster operations
   - Set up requirements and build scripts

4.2. **Implement Core ECS Operations**
   - Create `create_minecraft_service()` with EBS volume support
   - Build `start_server()` using desired count updates
   - Implement `stop_server()` preserving EBS volumes
   - Add `restart_server()` with force deployment

4.3. **Build Task Definition Management**
   - Create task definition templates with EBS volume configuration
   - Implement task definition versioning and updates
   - Add environment variable injection (EBS_VOLUME_ID, SERVER_ID)
   - Configure resource allocation (CPU, memory)

4.4. **Implement Multi-Cluster Management**
   - Build cluster selection algorithms (capacity-based, round-robin)
   - Add cluster health monitoring and failover
   - Implement cross-cluster service discovery
   - Create cluster load balancing logic

4.5. **Add Service Discovery and Tagging**
   - Implement ECS service tagging with EBS volume IDs
   - Build service lookup by EBS volume ID
   - Add service health checking and monitoring
   - Create service status tracking

4.6. **Build Server Rename and Management**
   - Implement `rename_server()` updating display fields only
   - Add server deletion preserving EBS volumes
   - Create server status updates and tracking
   - Build error handling for ECS-specific issues

**Deliverables:**
- Multi-cluster ECS operations class
- Task definition templates with EBS volume attachment
- Cluster selection and management logic
- Service discovery across clusters

### Task 5: Server Action Processing
**Objective**: Update ec2ActionWorker for ECS operations with EBS volume IDs

**Sub-tasks:**
5.1. **Update Action Processing Logic**
   - Modify `ec2ActionWorker` to use EBS volume IDs
   - Replace EC2 operations with ECS service operations
   - Update action routing and parameter handling
   - Maintain backward compatibility during transition

5.2. **Implement ECS Service Operations**
   - Update start operation: get EBS volume, create task, set desired_count = 1
   - Update stop operation: set desired_count = 0, preserve EBS volume
   - Update restart operation: force deployment with same EBS volume
   - Add create operation: create EBS volume first, then service

5.3. **Update SQS Message Processing**
   - Modify SQS message format for EBS volume IDs
   - Update message parsing and validation
   - Add ECS-specific error handling and retries
   - Maintain existing queue structure and DLQ

5.4. **Implement Status Tracking**
   - Update status tracking to use EBS volume IDs
   - Modify GraphQL subscription updates
   - Update audit logging with EBS volume references
   - Add ECS-specific status states

5.5. **Add Error Handling and Recovery**
   - Handle ECS service not found scenarios
   - Add task placement failure recovery
   - Implement EBS volume attachment error handling
   - Create timeout handling for long-running operations

5.6. **Update Action Validation**
   - Validate EBS volume ID format and existence
   - Check ECS cluster capacity before operations
   - Validate user permissions with EBS volume IDs
   - Add pre-flight checks for ECS operations

**Deliverables:**
- ECS-based action processing (start/stop/restart/create/delete)
- SQS integration maintained
- Status tracking with EBS volume IDs
- Error handling for ECS-specific issues

### Task 6: Server Discovery and Listing
**Objective**: Update ec2Discovery for multi-cluster ECS discovery with EBS volume mapping

**Sub-tasks:**
6.1. **Update User Permission Resolution**
   - Modify user permission queries to use EBS volume IDs
   - Update permission validation logic
   - Add EBS volume ID to user membership resolution
   - Maintain admin/user role functionality

6.2. **Implement Multi-Cluster Server Discovery**
   - Build cross-cluster ECS service discovery
   - Add cluster-aware service lookup
   - Implement parallel cluster querying for performance
   - Create unified server list aggregation

6.3. **Build Server Info Transformation**
   - Transform EBS volume mappings to server info objects
   - Add server name and display ID handling
   - Include cluster information for internal use
   - Map ECS service status to server states

6.4. **Update Auto-Configuration System**
   - Adapt auto-configuration for ECS services
   - Update default configuration templates
   - Add ECS-specific validation rules
   - Create container-specific default settings

6.5. **Implement Server Validation**
   - Check ECS service health instead of EC2 instance status
   - Validate task definition configuration
   - Verify EBS volume attachment status
   - Add container health check validation

6.6. **Add Performance Optimization**
   - Implement caching for frequently accessed server info
   - Add batch operations for multiple server queries
   - Optimize cross-cluster discovery performance
   - Create efficient server filtering and sorting

**Deliverables:**
- Cross-cluster server discovery
- EBS volume ID to server info transformation
- User permission validation with volume IDs
- Auto-configuration for ECS services

### Task 7: ECS-based Monitoring Integration
**Objective**: Containerized monitoring with multi-cluster CloudWatch metrics

**Sub-tasks:**
7.1. **Adapt Rust Monitoring for Containers**
   - Update Rust app to use EBS volume ID as primary identifier
   - Add cluster name detection from ECS metadata
   - Configure container-specific metric collection
   - Update CloudWatch dimension handling

7.2. **Configure CloudWatch Metrics**
   - Set up new namespace: `MinecraftDashboard/ECS`
   - Configure dimensions: `EBSVolumeId`, `ClusterName`
   - Update metric names for ECS environment
   - Add container-specific metrics (ContainerHealth)

7.3. **Update Metric Collection Lambda**
   - Modify `ec2StateHandler` Lambda for ECS metrics
   - Update metric parsing for new dimensions
   - Add EBS volume ID extraction from metrics
   - Update GraphQL subscription publishing

7.4. **Implement Real-time Monitoring**
   - Update real-time metric subscriptions
   - Add container health monitoring
   - Implement ECS task state change handling
   - Create container restart detection

7.5. **Add Container Health Checks**
   - Implement ECS task health monitoring
   - Add container exit code tracking
   - Create volume mount health verification
   - Build network connectivity monitoring

7.6. **Update Monitoring Dashboard**
   - Modify frontend to display ECS-specific metrics
   - Add cluster information to monitoring views
   - Update metric visualization for containers
   - Create ECS service status indicators

**Deliverables:**
- Rust monitoring app adapted for containers
- CloudWatch metrics with EBS volume ID + cluster dimensions
- Real-time metric collection and GraphQL subscriptions
- Container health monitoring

### Task 8: Auto-shutdown Mechanisms
**Objective**: Migrate CloudWatch alarms and scheduled operations to ECS

**Sub-tasks:**
8.1. **Update CloudWatch Alarm Configuration**
   - Migrate CPU-based alarms to use ECS metrics
   - Update alarm dimensions to use EBS volume ID + cluster
   - Configure alarm actions for ECS service scaling
   - Test alarm triggering and recovery

8.2. **Implement ECS Service Shutdown Logic**
   - Create Lambda function for ECS service shutdown
   - Implement desired count updates (set to 0)
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
   - Update rule targets for ECS operations
   - Test scheduled operations with ECS services

8.5. **Implement Shutdown Validation**
   - Add pre-shutdown validation checks
   - Verify no active players before shutdown
   - Check for ongoing operations or maintenance
   - Create shutdown confirmation and logging

8.6. **Add Recovery and Failover**
   - Implement automatic restart on container failures
   - Add cluster failover for shutdown operations
   - Create monitoring for shutdown success/failure
   - Build alerting for failed shutdown attempts

**Deliverables:**
- ECS task monitoring with CloudWatch alarms
- CPU/user-based shutdown via desired count updates
- Scheduled operations with EBS volume ID references
- EventBridge rules for ECS services

### Task 9: Configuration Management
**Objective**: ECS task definition configuration with EBS volume management

**Sub-tasks:**
9.1. **Update Server Configuration System**
   - Modify server config to work with ECS task definitions
   - Update configuration validation for container environments
   - Add ECS-specific configuration options
   - Maintain backward compatibility during migration

9.2. **Implement Task Definition Management**
   - Create task definition update workflows
   - Implement task definition versioning
   - Add configuration change detection
   - Build task definition rollback capabilities

9.3. **Handle EBS Volume Configuration**
   - Implement EBS volume resize handling (requires stop/start)
   - Add volume type and performance configuration
   - Create volume backup and snapshot management
   - Build volume migration between availability zones

9.4. **Update IAM Role Management**
   - Adapt IAM role management for ECS tasks
   - Update task role and execution role handling
   - Add container-specific permissions
   - Implement role validation and testing

9.5. **Implement Configuration Validation**
   - Add ECS-specific configuration validation
   - Check task definition resource limits
   - Validate container image availability
   - Verify EBS volume compatibility

9.6. **Build Configuration Deployment**
   - Create configuration deployment workflows
   - Implement rolling updates for configuration changes
   - Add configuration change monitoring
   - Build rollback procedures for failed deployments

**Deliverables:**
- Task definition updates for configuration changes
- EBS volume resize handling (requires stop/start)
- IAM role management for ECS tasks
- Configuration validation for ECS-specific settings

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
   - Update error handling for ECS-specific scenarios

10.5. **Implement User Invitation System**
   - Create new user invitation system for ECS servers
   - Update invitation emails and notifications
   - Add EBS volume ID validation in invitations
   - Build invitation acceptance workflows

10.6. **Test Access Control System**
   - Test user permissions with EBS volume IDs
   - Validate admin and user role functionality
   - Test server access across different clusters
   - Verify permission stability across server renames

**Deliverables:**
- Permission reset strategy (fresh start)
- Authorization checks with EBS volume IDs
- GraphQL resolver updates
- User invitation system for ECS servers

### Task 11: Frontend Integration and Testing
**Objective**: Update frontend for EBS volume ID-based operations and complete testing

**Sub-tasks:**
11.1. **Update GraphQL Operations**
   - Update all GraphQL queries to handle EBS volume IDs
   - Modify mutations to use EBS volume IDs internally
   - Update subscriptions for ECS-based real-time updates
   - Add error handling for ECS-specific responses

11.2. **Update Frontend Server Management**
   - Modify server display to show server names/display IDs
   - Update server operations to use EBS volume IDs internally
   - Add cluster information display (for admin users)
   - Update server creation workflows

11.3. **Implement ECS-specific Error Handling**
   - Add error handling for ECS service not found
   - Handle task placement failure scenarios
   - Add container startup timeout handling
   - Create user-friendly error messages for ECS issues

11.4. **Update Real-time Features**
   - Modify real-time metrics display for containerized monitoring
   - Update server status indicators for ECS services
   - Add container health status display
   - Update action status tracking for ECS operations

11.5. **Perform Integration Testing**
   - Test complete server lifecycle (create, start, stop, delete)
   - Validate user permissions with EBS volume IDs
   - Test multi-cluster operations transparency
   - Verify real-time updates and monitoring

11.6. **Conduct Performance Testing**
   - Load test ECS service operations
   - Measure container startup times vs EC2
   - Test concurrent server operations
   - Monitor resource utilization and costs

11.7. **End-to-End System Testing**
   - Test complete user workflows from frontend to ECS
   - Validate data persistence across container restarts
   - Test auto-shutdown and scheduled operations
   - Verify monitoring and alerting functionality

**Deliverables:**
- GraphQL queries/mutations updated for EBS volume IDs
- Error handling for ECS-specific scenarios
- End-to-end testing of complete ECS system
- Performance monitoring and optimization

## Success Criteria

### Technical
- [ ] All servers identified by EBS volume IDs
- [ ] Multi-cluster ECS deployment operational
- [ ] Container startup time < 2 minutes
- [ ] EBS volume attachment working reliably
- [ ] Real-time monitoring functional

### User Experience
- [ ] Server names changeable without breaking permissions
- [ ] Transparent cluster management (users unaware)
- [ ] Same GraphQL API interface maintained
- [ ] Performance equivalent or better than EC2

### Operational
- [ ] Auto-shutdown policies working with ECS
- [ ] Scheduled operations functional
- [ ] Cost optimization maintained
- [ ] Monitoring and alerting operational

## Migration Timeline
1. **Weeks 1-2**: Tasks 1-3 (Infrastructure + Images + Mapping)
2. **Weeks 3-4**: Tasks 4-6 (ECS Helper + Actions + Discovery)
3. **Weeks 5-6**: Tasks 7-9 (Monitoring + Auto-shutdown + Config)
4. **Weeks 7-8**: Tasks 10-11 (Permissions + Frontend + Testing)

## Risk Mitigation
- **EBS Volume Attachment**: Extensive testing of Docker volume plugins
- **Container Startup**: Optimize image size and startup scripts
- **Data Loss**: Comprehensive backup strategy for EBS volumes
- **Performance**: Load testing with multiple concurrent containers
- **Rollback**: Maintain EC2 infrastructure until ECS fully validated
