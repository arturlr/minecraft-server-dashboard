# Task 7: Create EC2 User Data Script - COMPLETE ✅

## Summary
Successfully created EC2 user data script for Docker setup with all critical and high severity security issues fixed.

## File Created
✅ `support_tasks/ec2-docker-userdata.sh` - Idempotent, secure Docker setup script

## Key Features

### Installation Steps
1. Install Docker and Docker Compose v2
2. Setup and mount EBS volume (UUID-based)
3. Download docker-compose.yml from S3
4. Create .env file with secrets from SSM
5. Install CloudWatch agent
6. Login to ECR
7. Pull and start Docker containers
8. Verify services are running

### Security Improvements
- ✅ Secure secret handling (temporary files with 600 permissions)
- ✅ Separate secure log for sensitive operations
- ✅ No secrets in process list or main logs
- ✅ Restrictive directory permissions (750/700/600)
- ✅ UUID-based EBS mounting (stable across reboots)
- ✅ Secrets created with secure permissions before writing

### Idempotency
- ✅ Checks if Docker already installed
- ✅ Checks if Docker Compose already installed
- ✅ Checks if EBS volume already mounted
- ✅ Checks if containers already running
- ✅ Safe to run multiple times

### Error Handling
- ✅ Removed `set -e` (continues on errors)
- ✅ Error logging function
- ✅ Return codes for each function
- ✅ Retry logic for Docker image pulls
- ✅ Exponential backoff for EBS device wait

### Code Review Fixes Applied

#### Critical Issues Fixed ✅
- ✅ Removed `set -e` for better error handling
- ✅ Secure secret handling with temporary files
- ✅ UUID-based fstab entries (not device paths)
- ✅ Secrets written to files with secure permissions first
- ✅ ECR password via temporary file

#### High Severity Issues Fixed ✅
- ✅ Configurable Docker Compose version
- ✅ Extended EBS wait time (5 minutes with exponential backoff)
- ✅ UUID-based mounting prevents device name changes
- ✅ Idempotency checks for all operations
- ✅ Separate secure log for sensitive operations

#### Medium Severity Issues Fixed ✅
- ✅ Proper health check with 60-second wait
- ✅ HTTP health endpoint verification
- ✅ Restrictive directory permissions
- ✅ YAML validation after download

## Script Structure

### Logging
- **Main Log**: `/var/log/minecraft-docker-setup.log` (general operations)
- **Secure Log**: `/var/log/minecraft-docker-setup-secure.log` (sensitive operations)

### Functions
1. `install_docker()` - Idempotent Docker installation
2. `install_docker_compose()` - Idempotent Compose installation
3. `setup_ebs_volume()` - UUID-based EBS setup
4. `download_docker_compose()` - S3 download with validation
5. `create_env_file()` - Secure secret retrieval and file creation
6. `install_cloudwatch_agent()` - CloudWatch agent setup
7. `ecr_login()` - Secure ECR authentication
8. `start_containers()` - Idempotent container startup
9. `verify_services()` - Health checks and verification

### Environment Variables (from CloudFormation)
- `INSTANCE_ID` - EC2 instance ID
- `AWS_REGION` - AWS region
- `SUPPORT_BUCKET` - S3 bucket for docker-compose.yml
- `ECR_REGISTRY` - ECR registry URL
- `IMAGE_TAG` - Docker image tag (default: latest)
- `EBS_DEVICE` - EBS device path (default: /dev/xvdf)
- `DOCKER_COMPOSE_VERSION` - Compose version (default: 2.24.5)

### SSM Parameters Required
- `/minecraft-dashboard/jwt-secret` - JWT secret for msd-logs
- `/minecraft-dashboard/rcon-password` - RCON password for Minecraft

## Security Features

### Secret Management
```bash
# Create temp file with secure permissions
TEMP=$(mktemp -p /opt/minecraft-dashboard/secrets)
chmod 600 "$TEMP"

# Get secret from SSM
aws ssm get-parameter --with-decryption > "$TEMP" 2>>"$SECURE_LOG"

# Create target file with secure permissions
touch /path/to/secret.txt
chmod 600 /path/to/secret.txt

# Copy and cleanup
cat "$TEMP" > /path/to/secret.txt
rm -f "$TEMP"
```

### UUID-Based Mounting
```bash
# Get UUID instead of device path
UUID=$(blkid -s UUID -o value "$EBS_DEVICE")

# Add to fstab with UUID
echo "UUID=$UUID $MOUNT_POINT ext4 defaults,nofail 0 2" >> /etc/fstab
```

### Exponential Backoff
```bash
MAX_WAIT=300
WAIT=0
SLEEP=2
while [ ! -e "$EBS_DEVICE" ] && [ $WAIT -lt $MAX_WAIT ]; do
    sleep $SLEEP
    WAIT=$((WAIT + SLEEP))
    [ $SLEEP -lt 16 ] && SLEEP=$((SLEEP * 2))
done
```

## Testing Checklist
- [ ] Script runs successfully on fresh EC2 instance
- [ ] Script is idempotent (can run multiple times)
- [ ] Docker and Docker Compose installed
- [ ] EBS volume mounted with UUID
- [ ] Secrets retrieved from SSM
- [ ] ECR login successful
- [ ] Containers start and become healthy
- [ ] Health checks pass
- [ ] Logs written to correct locations
- [ ] No secrets in main log file

## Known Limitations

### Not Implemented
- CloudFormation signal helper (for stack completion)
- Rollback mechanism on failure
- Resource validation (CPU, memory, disk space)
- Network retry logic for all operations

### Edge Cases Handled
- ✅ Docker already installed
- ✅ EBS volume already mounted
- ✅ Containers already running
- ✅ Device name changes (UUID-based)
- ✅ Slow EBS attachment (5-minute wait)

### Edge Cases Not Handled
- ⚠️ Corrupted filesystem (no fsck)
- ⚠️ Insufficient disk space
- ⚠️ Network connectivity issues during downloads
- ⚠️ ECR registry unavailable
- ⚠️ S3 bucket access denied

## Next Steps
1. **Task 8**: Update CloudFormation for Docker (EC2 template, ECR repos, SSM parameters)
2. **Task 9**: Create dockerManager Lambda
3. **Task 10**: Create AppSync resolvers
4. **Task 11**: Build and push images in CircleCI
5. **Task 12**: Update frontend
6. **Task 13**: Migration script
7. **Task 14**: Remove bootstrap system
