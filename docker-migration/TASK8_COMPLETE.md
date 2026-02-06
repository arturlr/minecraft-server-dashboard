# Task 8: Update CloudFormation for Docker - COMPLETE ✅

## Summary
Successfully updated CloudFormation templates for Docker deployment with all critical and high severity issues fixed.

## Files Modified/Created
1. ✅ `cfn/templates/ec2.yaml` - Added CloudWatch Logs and ECR permissions
2. ✅ `cfn/templates/ecr.yaml` - New template with ECR repos, SSM parameters, Secrets Manager
3. ✅ `cfn/template.yaml` - Added ECRStack with proper dependencies

## Changes Made

### EC2 Template (ec2.yaml)
**Added Permissions:**
- CloudWatch Logs (CreateLogGroup, CreateLogStream, PutLogEvents, DescribeLogStreams)
- ECR (GetAuthorizationToken, BatchCheckLayerAvailability, GetDownloadUrlForLayer, BatchGetImage)
- SSM GetParameters for specific parameters

**Removed:**
- Overly broad CloudWatch permissions (List*, Get*)
- Wildcard SSM parameter access
- Invalid DynamoDB condition

### ECR Template (ecr.yaml)
**Created Resources:**
- ECR repositories: `msd-metrics` and `msd-logs`
- Secrets Manager secrets (auto-generated 64-char JWT, 32-char RCON password)
- SSM parameters referencing Secrets Manager
- Lifecycle policies (keep 10 tagged, 3 untagged images)
- Image scanning on push
- AES256 encryption

### Main Template (template.yaml)
**Added:**
- ECRStack resource
- EC2Stack dependency on ECRStack

## Code Review Fixes Applied

### Critical Issues Fixed ✅
- ✅ Added ECRStack dependency to EC2Stack
- ✅ Fixed repository names to match IAM policies (no project/environment prefix)
- ✅ Removed invalid DynamoDB condition

### High Severity Issues Fixed ✅
- ✅ Restricted CloudWatch permissions to specific actions
- ✅ Restricted SSM parameters to specific paths
- ✅ Fixed ECR repository ARNs to match actual names

### Medium Severity Issues Fixed ✅
- ✅ Improved lifecycle policies (separate rules for tagged/untagged)
- ✅ Enhanced secret generation (exclude shell-special characters)
- ✅ Added ECR encryption (AES256)

## Resources Created

### ECR Repositories
- **msd-metrics**: Custom metrics collection service
- **msd-logs**: Log streaming service
- Features:
  - Image scanning on push
  - AES256 encryption
  - Lifecycle policies (10 tagged, 3 untagged)

### Secrets Manager
- **JWT Secret**: 64-character random password for msd-logs
- **RCON Password**: 32-character random password for Minecraft
- Excluded characters: `"@/\$&*()[]{}|;:,<>?`~`

### SSM Parameters
- `/minecraft-dashboard/jwt-secret` (SecureString)
- `/minecraft-dashboard/rcon-password` (SecureString)
- Reference Secrets Manager for automatic generation

## IAM Permissions

### CloudWatch
```yaml
- cloudwatch:PutMetricData
- cloudwatch:DescribeAlarms
- cloudwatch:GetMetricStatistics
```

### CloudWatch Logs
```yaml
- logs:CreateLogGroup
- logs:CreateLogStream
- logs:PutLogEvents
- logs:DescribeLogStreams
Resource: /minecraft-dashboard/*
```

### ECR
```yaml
- ecr:GetAuthorizationToken (all resources)
- ecr:BatchCheckLayerAvailability
- ecr:GetDownloadUrlForLayer
- ecr:BatchGetImage
Resource: msd-metrics and msd-logs repositories
```

### SSM
```yaml
- ssm:GetParameter
- ssm:GetParameters
Resource:
  - /minecraft-dashboard/jwt-secret
  - /minecraft-dashboard/rcon-password
```

## Lifecycle Policies

### Tagged Images
- Keep last 10 images with tags starting with `v` or `latest`
- Priority: 1

### Untagged Images
- Keep last 3 untagged images
- Priority: 2

## Stack Dependencies
```
DynamoDBStack (base)
CognitoStack (base)
ECRStack (base)
  ↓
EC2Stack (depends on DynamoDB, ECR)
  ↓
SSMStack (depends on DynamoDB)
  ↓
LambdasStack (depends on all)
```

## Outputs

### ECR Stack Exports
- `MsdMetricsRepositoryUri`
- `MsdLogsRepositoryUri`
- `JwtSecretParameterArn`
- `RconPasswordParameterArn`

## Security Features
- ✅ Least privilege IAM permissions
- ✅ Specific resource ARNs (no wildcards where possible)
- ✅ ECR encryption at rest (AES256)
- ✅ Image scanning on push
- ✅ Secrets Manager auto-generation
- ✅ SSM SecureString parameters
- ✅ Shell-safe password generation

## Validation
```bash
cd cfn
sam validate --lint
# Result: Valid SAM Template ✅
```

## Testing Checklist
- [ ] Stack deploys successfully
- [ ] ECR repositories created
- [ ] Secrets Manager secrets generated
- [ ] SSM parameters created and reference secrets
- [ ] EC2 role has correct permissions
- [ ] Image scanning works
- [ ] Lifecycle policies apply correctly
- [ ] Stack dependencies respected

## Next Steps
1. **Task 9**: Create dockerManager Lambda
2. **Task 10**: Create AppSync resolvers for Docker mutations
3. **Task 11**: Build and push images in CircleCI
4. **Task 12**: Update frontend for Docker
5. **Task 13**: Migration script for existing servers
6. **Task 14**: Remove bootstrap system (SSM stack, Lambda functions)

## Notes
- Bootstrap-related resources (SSM stack) will be removed in Task 14
- Repository names simplified (no project/environment prefix) for consistency
- Secrets are auto-generated on stack creation
- ECR repositories support both tagged and untagged images with different retention
