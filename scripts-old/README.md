# Bootstrap Scripts

This directory contains the bootstrap scripts for setting up Minecraft servers on EC2 instances.

## Versioning

Scripts are versioned using semantic versioning (MAJOR.MINOR.PATCH) in the `VERSION` file.

### Version Format
- **MAJOR**: Breaking changes that require manual intervention
- **MINOR**: New features or significant improvements
- **PATCH**: Bug fixes and minor improvements

### Deployment

Scripts are uploaded to S3 with version prefixes:
- `s3://{bucket}/scripts/v{VERSION}/` - Specific version (e.g., v1.0.0)
- `s3://{bucket}/scripts/latest/` - Always points to the most recent version

### Usage

By default, servers use `latest` scripts. To pin a server to a specific version:

1. Update the server config in DynamoDB:
   ```json
   {
     "id": "i-1234567890abcdef0",
     "scriptVersion": "v1.0.0"
   }
   ```

2. Re-bootstrap the server to apply the specific version

### Rollback

To rollback to a previous version:
1. Set `scriptVersion` in server config to the desired version
2. Trigger a re-bootstrap

### Version History

- **1.0.0** (2026-02-04): Initial versioned release
  - Package installation with multi-distro support
  - CloudWatch agent setup
  - Metrics collection (msd-metrics)
  - Log streaming (msd-logs)
  - Minecraft service with systemd
  - Bootstrap status tracking
