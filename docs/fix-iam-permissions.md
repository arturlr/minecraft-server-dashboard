# Fix IAM Permissions Issue

## Problem
When clicking the "Fix It" button in the dashboard, users encounter this error:
```
"Unauthorized operation", "details": "An error occurred (UnauthorizedOperation) when calling the AssociateIamInstanceProfile operation: You are not authorized to perform this operation. User: arn:aws:sts::514046899996:assumed-role/minecraft-dashboard-LambdasStack-1-ec2ActionValidatorRole-D2hJONZM5VDk/minecraftdashboard-dev-ec2ActionValidator is not authorized to perform: iam:PassRole on resource: arn:aws:iam::514046899996:role/minecraft-dashboard-EC2St-Ec2MinecraftDashboardInst-ifAAojd183zw because no identity-based policy allows the iam:PassRole
```

## Root Cause
The ec2ActionValidator Lambda function needs `iam:PassRole` permission on the EC2 instance role to associate IAM instance profiles with EC2 instances. When you associate an instance profile with an EC2 instance, AWS internally needs to "pass" the role contained within that instance profile to the EC2 service.

## Solution
Updated the ec2ActionValidator Lambda's IAM policy to include the correct `iam:PassRole` permission:

### Before (Incorrect)
```yaml
- Effect: Allow
  Action:
    - iam:PassRole
  Resource: 
    - Fn::ImportValue: !Sub "${ProjectName}-${EnvironmentName}-IAMEC2InstanceProfileArn"
```

### After (Correct)
```yaml
- Effect: Allow
  Action:
    - iam:PassRole
  Resource: 
    - Fn::ImportValue: !Sub "${ProjectName}-${EnvironmentName}-IAMEC2RoleArn"
```

## Files Modified
1. `cfn/templates/lambdas.yaml` - Updated ec2ActionValidator Lambda IAM policy
2. `cfn/templates/ec2.yaml` - Added export for EC2 role ARN

## Deployment Steps
1. Navigate to the `cfn` directory
2. Run `sam build`
3. Run `sam deploy`
4. Test the "Fix It" button in the dashboard

## Verification
After deployment, the "Fix It" button should work without authorization errors. The button will:
1. Check if the instance has the correct IAM instance profile
2. If not, disassociate any existing incorrect profile
3. Associate the correct IAM instance profile
4. Verify the association was successful

## Technical Details
- **IAM PassRole**: Required when one AWS service needs to assume a role on behalf of another service
- **Instance Profile vs Role**: Instance profiles are containers for IAM roles used by EC2 instances
- **Permission Scope**: The permission is scoped to only the specific EC2 instance role used by Minecraft servers

## Security Considerations
The `iam:PassRole` permission is limited to:
- Only the specific EC2 instance role created for Minecraft servers
- Only instances tagged with the correct App value
- Only authorized users (admins or instance owners)

This maintains the principle of least privilege while enabling the required functionality.