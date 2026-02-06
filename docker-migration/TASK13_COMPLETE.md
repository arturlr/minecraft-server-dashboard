# Task 13: Migration Script - COMPLETE ✅

## Summary
Created migration script to convert existing bootstrap-based servers to Docker.

## File Created
- `support_tasks/migrate-to-docker.sh`

## Usage
```bash
# Migrate
sudo SUPPORT_BUCKET=my-bucket ECR_REGISTRY=123456.dkr.ecr.us-west-2.amazonaws.com bash migrate-to-docker.sh

# Rollback
sudo bash migrate-to-docker.sh --rollback

# Cleanup old services
sudo bash migrate-to-docker.sh --cleanup
```

## Migration Steps
1. Validate inputs (bucket, ECR, instance ID format)
2. Pre-checks (root, data exists, server stopped, disk space, ports, AWS creds)
3. Backup world data to S3 (timestamped)
4. Stop and disable systemd services (kept for rollback)
5. Install Docker + Docker Compose
6. Download docker-compose.yml (with retry)
7. Fetch secrets atomically from SSM
8. Copy world data with rsync
9. Create systemd boot service
10. ECR login, pull images, start containers
11. Verify (containers running, ports, health checks)

## Code Review Fixes Applied
- ✅ Input validation (bucket, ECR registry, instance ID regex)
- ✅ Atomic secret writes (mktemp + mv)
- ✅ Cleanup trap for temp files
- ✅ Retry logic for S3 downloads (3 attempts)
- ✅ Port availability checks (25565, 25566)
- ✅ AWS credential verification
- ✅ Symlink-safe path resolution (realpath)
- ✅ 3x disk space safety margin
- ✅ Log file permissions (640)
- ✅ Flags handled before main logic

## Progress: 11/14 tasks complete
