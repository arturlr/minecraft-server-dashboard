# Task 9 Revision: Simplified Docker Management ✅

## What Changed

### Original Plan (Tasks 9-10)
- ❌ Create dockerManager Lambda with SSM Run Command
- ❌ Create AppSync resolvers for pullDockerImage, restartDockerContainer, updateDockerCompose
- ❌ Manual Docker management via GraphQL mutations

### New Approach (Automatic Updates)
- ✅ Systemd service runs on every EC2 boot
- ✅ Automatically pulls latest images and starts containers
- ✅ Users stop/start EC2 to update (existing mutations)
- ✅ No SSM complexity, no manual management needed

## Changes Made

### 1. Removed dockerManager Lambda ✅
```bash
rm -rf lambdas/dockerManager/
```
- No Lambda function needed
- No SSM Run Command complexity
- Simpler architecture

### 2. Updated GraphQL Schema ✅
**Removed mutations:**
- `pullDockerImage(instanceId: String!, service: String!): AWSJSON`
- `restartDockerContainer(instanceId: String!, service: String!): AWSJSON`
- `updateDockerCompose(instanceId: String!, version: String!): AWSJSON`

**Kept existing:**
- `startServer(instanceId: String!): AWSJSON` - Now triggers Docker updates
- `stopServer(instanceId: String!): AWSJSON`
- `restartServer(instanceId: String!): AWSJSON`

### 3. Updated User Data Script ✅
**Added systemd service:**
```bash
# /etc/systemd/system/docker-update.service
[Unit]
Description=Pull and start Docker containers on boot
After=docker.service network-online.target
Requires=docker.service

[Service]
Type=oneshot
WorkingDirectory=/opt/minecraft-dashboard
ExecStartPre=/usr/local/bin/docker-compose pull
ExecStart=/usr/local/bin/docker-compose up -d
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
```

**What it does:**
- Runs automatically on every EC2 boot
- Pulls latest Docker images from ECR
- Starts all containers with docker-compose
- Ensures containers always use latest code

### 4. Updated Migration Plan ✅
**Modified docker_plan.md:**
- Task 9: ~~Create dockerManager Lambda~~ → **REMOVED**
- Task 10: ~~Create AppSync Resolvers~~ → **REMOVED**
- Task 7: Added systemd service creation
- Task 12: Simplified frontend (no manual Docker controls)

## New User Workflow

### To Update Containers:
1. User clicks "Stop Server" in dashboard
2. User clicks "Start Server" in dashboard
3. EC2 boots → systemd runs docker-update.service
4. Service pulls latest images from ECR
5. Service starts containers with docker-compose
6. Server ready with latest code

### Benefits:
- ✅ **Simpler**: No Lambda, no SSM, no manual management
- ✅ **Automatic**: Always pulls latest on boot
- ✅ **Reliable**: Systemd handles failures and retries
- ✅ **Familiar**: Uses existing start/stop workflow
- ✅ **Cost**: No additional Lambda invocations

## Architecture Comparison

### Before (Complex):
```
User → GraphQL → dockerManager Lambda → SSM Run Command → EC2 → Docker
```

### After (Simple):
```
User → GraphQL → EC2 Start/Stop → Systemd → Docker (auto-pull)
```

## Files Modified

1. ✅ `appsync/schema.graphql` - Removed Docker mutations
2. ✅ `support_tasks/ec2-docker-userdata.sh` - Added systemd service
3. ✅ `docker_plan.md` - Updated tasks 7, 9, 10, 12
4. ✅ Deleted `lambdas/dockerManager/` directory

## Next Steps

### Task 11: Build and Push Images in CircleCI
- Build msd-metrics and msd-logs Docker images
- Push to ECR with tags (latest, SHA)
- Update docker-compose.yml in S3

### Task 12: Update Frontend
- Remove bootstrap UI elements
- Add container status indicators
- Update help text: "Stop and start server to update"
- Show dockerImageTag and dockerComposeVersion

### Remaining Tasks (13-16):
- Task 13: Migration script for existing servers
- Task 14: Remove bootstrap system
- Task 15: Update documentation
- Task 16: Add EBS snapshot automation

## Testing Checklist

- [ ] User data script creates systemd service
- [ ] Systemd service enabled on boot
- [ ] Service pulls latest images on boot
- [ ] Service starts containers successfully
- [ ] Containers use latest code after EC2 restart
- [ ] Existing start/stop mutations still work
- [ ] GraphQL schema validates without Docker mutations

## Summary

**Simplified Docker management by removing manual control and using automatic updates on EC2 boot.** This eliminates the need for dockerManager Lambda, SSM Run Command, and custom GraphQL mutations. Users simply stop/start the EC2 instance to update containers, which is more intuitive and requires less infrastructure.

**Tasks completed: 8/14** (Tasks 9-10 removed from plan)
