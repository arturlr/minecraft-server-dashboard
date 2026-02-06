### **Task Breakdown:**

Task 1: Update GraphQL Schema
- Remove bootstrap fields from ServerConfig type:
  - scriptVersion, isBootstrapComplete, bootstrapStage, bootstrapStatus, bootstrapError
- Add Docker fields to ServerConfig:
  - dockerImageTag: String
  - dockerComposeVersion: String
- Remove bootstrapServer mutation
- Add new mutations:
  - pullDockerImage(instanceId: String!, service: String): AWSJSON
  - restartDockerContainer(instanceId: String!, service: String!): AWSJSON
  - updateDockerCompose(instanceId: String!, version: String): AWSJSON
- Add ContainerStatus type with service health info
- Add containerStatus field to ServerInfo
- Update appsync/schema.graphql
- Demo: Schema validates, no breaking changes to existing queries

Task 2: Configure itzg/minecraft-server Image
- Use itzg/minecraft-server:latest from Docker Hub
- No custom Dockerfile needed
- Configure via environment variables in docker-compose.yml:
  - EULA=TRUE (auto-accept)
  - VERSION=LATEST (or specific version)
  - MEMORY=2G (configurable)
  - TYPE=VANILLA (or PAPER, FORGE, etc.)
  - ENABLE_RCON=true (for remote management)
  - LOG_TIMESTAMP=true (for better log parsing)
- VOLUME /data for world/config persistence
- Demo: Run with docker-compose, connect to server

Task 3: Create Dockerfile for msd-metrics
- Create docker/msd-metrics/Dockerfile
- Multi-stage: rust:alpine builder + alpine runtime
- Copy from rust/msd-metrics/
- Static binary (musl target)
- Environment: CLOUDWATCH_NAMESPACE, INSTANCE_ID, REGION
- Demo: Container sends metrics to CloudWatch

Task 4: Update msd-logs for File-Based Logging
- Modify rust/msd-logs/src/main.rs:
  - Replace journalctl reading with file tailing
  - Read from /logs/minecraft.log (shared volume)
  - Handle log rotation (detect file truncation)
  - Keep last N lines in memory buffer
- Create docker/msd-logs/Dockerfile
- Multi-stage: rust:alpine builder + alpine runtime
- Copy from rust/msd-logs/
- EXPOSE 25566
- VOLUME /logs (read-only mount)
- Demo: HTTP endpoint returns logs from shared volume

Task 5: Create docker-compose.yml
- Define 3 services: minecraft, msd-metrics, msd-logs
- minecraft service:
  - image: itzg/minecraft-server:latest
  - Environment: EULA, VERSION, MEMORY, TYPE, ENABLE_RCON, LOG_TIMESTAMP
  - Volumes: /mnt/minecraft-world:/data, minecraft-logs:/data/logs (read by msd-logs)
- Shared volume: minecraft-logs (minecraft writes, msd-logs reads)
- Persistent volume: /mnt/minecraft-world → /data
- Environment variables from .env file
- Logging driver: awslogs (CloudWatch Logs)
- Health checks for each service
- Restart policy: unless-stopped
- Resource limits: CPU/memory per service
- Secrets: JWT_SECRET from environment
- Demo: docker-compose up -d starts all services

Task 6: Update DynamoDB Schema
- Update ddbHelper.py:
  - Remove: scriptVersion, isBootstrapComplete, bootstrapStage, bootstrapStatus, bootstrapError
  - Add: dockerImageTag, dockerComposeVersion
- Update get_server_config() method
- Update put_server_config() method
- Demo: Config save/load works with new fields

Task 7: Create EC2 User Data Script
- Create support_tasks/ec2-docker-userdata.sh
- Install Docker + docker-compose v2
- Verify Docker installation (exit on failure)
- Create and format EBS volume:
  - Detect attached volume (e.g., /dev/xvdf)
  - Format as ext4 if not formatted
  - Mount to /mnt/minecraft-world
  - Add to /etc/fstab for persistence
- Download docker-compose.yml from S3 (retry on failure)
- Create .env with INSTANCE_ID, REGION, JWT_SECRET (from SSM Parameter Store)
- Install CloudWatch agent for container metrics
- Create systemd service (docker-update.service) that runs on every boot:
  - Pulls latest Docker images
  - Starts containers with docker-compose up -d
  - Ensures containers always use latest code
- Run docker-compose up -d for initial setup
- Verify all containers started (exit code check)
- Demo: Launch EC2, services auto-start, logs in CloudWatch

Task 8: Update CloudFormation for Docker
- Modify cfn/templates/ec2.yaml:
  - Add EBS volume resource (20GB for world data)
  - Attach volume to instance (/dev/xvdf)
  - Update user data to use docker script
  - Add Docker Hub pull permissions (no ECR needed for itzg image)
  - Add ECR pull permissions for msd-metrics and msd-logs only
  - Add CloudWatch Logs permissions (logs:CreateLogGroup, logs:PutLogEvents)
  - Add SSM Parameter Store read permission (for JWT_SECRET)
  - Remove bootstrap-related permissions
  - Add security group rule: port 25566 (msd-logs) from Lambda security group only
- Create cfn/templates/ecr.yaml:
  - msd-metrics repository (only)
  - msd-logs repository (only)
  - Lifecycle policies (keep last 10 images)
- Create SSM Parameter: /minecraft-dashboard/jwt-secret (SecureString)
- Remove cfn/templates/ssm.yaml (no longer needed)
- Update main template dependencies
- Demo: Deploy stack, EC2 launches with containers, EBS persists

Task 9: ~~Create dockerManager Lambda~~ **REMOVED**
- **Reason**: No need for manual Docker management via SSM
- **Alternative**: Systemd service automatically pulls and updates containers on every EC2 boot
- **User workflow**: Stop/Start EC2 instance to update containers (uses existing start/stop mutations)
- **Benefits**: Simpler architecture, no SSM complexity, automatic updates

Task 10: ~~Create AppSync Resolvers~~ **REMOVED**
- **Reason**: No dockerManager Lambda needed
- **GraphQL changes**: Removed pullDockerImage, restartDockerContainer, updateDockerCompose mutations
- **Alternative**: Users use existing startServer/stopServer mutations to trigger updates

Task 11: Build and Push Images in CircleCI
- Update .circleci/config.yml:
  - Add Docker build job with docker layer caching
  - Build 2 images only: msd-metrics and msd-logs (minecraft uses itzg/minecraft-server from Docker Hub)
  - Tag with ${CIRCLE_SHA1} and latest
  - Push to ECR (separate repos for dev/prod)
  - Update docker-compose.yml in S3 with new tags
- Add ECR login step
- Cache Docker layers between builds
- Estimated build time: 5-8 minutes (reduced from 8-12)
- Demo: Git push builds and pushes images

Task 12: Update Frontend for Docker
- Remove "Bootstrap Server" button
- Remove Docker management UI (no manual pull/restart needed)
- Add container status indicators (running/stopped/unhealthy)
- Update ServerSettings.vue to show Docker fields (dockerImageTag, dockerComposeVersion)
- Remove bootstrap-related UI elements
- Update help text: "Stop and start the server to update containers"
- Demo: Full UI workflow shows container status

Task 13: Migration Script for Existing Servers
- Create support_tasks/migrate-to-docker.sh
- **Pre-migration checks**:
  - Verify server is stopped
  - Check disk space (need 2x world size)
  - Backup world data to S3 (timestamped)
- Stop systemd services (minecraft, msd-metrics, msd-logs)
- Install Docker + docker-compose v2
- Create and mount EBS volume
- Copy world data to /mnt/minecraft-world
- Pull Docker images
- Start containers
- **Verification**:
  - Wait for health checks to pass
  - Verify Minecraft port 25565 responding
  - Check CloudWatch metrics arriving
  - Test msd-logs endpoint
- Update DynamoDB (remove bootstrap fields, add Docker fields)
- **Rollback plan**: Keep systemd services disabled but intact for 7 days
- Demo: Migrate one server successfully with rollback option

Task 14: Remove Bootstrap System
- Delete scripts/ directory
- Delete lambdas/bootstrapServer/
- Remove SSM-related CloudFormation resources
- Clean up S3 bootstrap scripts
- Remove ssmHelper layer (or simplify)
- Update documentation
- Demo: Clean deployment without bootstrap

Task 15: Update Documentation
- Update tech.md:
  - Replace bootstrap architecture with Docker architecture
  - Document container structure and volumes
  - Update deployment flow (ECR push → EC2 pull)
  - Document CloudWatch Logs integration
- Update structure.md:
  - Add docker/ directory structure
  - Remove scripts/ directory
  - Update deployment artifacts section
- Create docs/docker-migration.md:
  - Migration process overview
  - Pre-migration checklist
  - Rollback procedures
  - Troubleshooting guide
- Update README.md with Docker setup instructions
- Demo: Documentation reflects new architecture

Task 16: Add EBS Snapshot Automation
- Create cfn/templates/backup.yaml:
  - EventBridge rule (daily at 3 AM UTC)
  - Lambda function to create EBS snapshots
  - Retention policy (keep last 7 snapshots)
  - Tag snapshots with server name and date
- Add SNS notification on snapshot failure
- Demo: Snapshots created automatically, old ones deleted
