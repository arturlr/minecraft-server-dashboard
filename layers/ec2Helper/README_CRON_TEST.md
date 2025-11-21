# Cron Job Installation Test

## Overview

This test suite verifies that the `port_count.sh` cron job is correctly installed and configured on EC2 instances during bootstrap.

## Test File

`test_cron_job_installation.py`

## Requirements Validated

- **Requirement 2.5**: WHEN the metric collection script runs THEN the System SHALL execute every minute via cron
- **Requirement 6.5**: WHEN the cron job already exists THEN the System SHALL not create duplicate entries

## Tests Included

### 1. Test Cron Job Exists
Verifies that a cron job for `/usr/local/port_count.sh` is present in the crontab.

### 2. Test Cron Job Runs Every Minute
Verifies that the cron job is configured with the correct schedule expression to run every minute (`*/1 * * * *`).

### 3. Test No Duplicate Cron Jobs
Verifies that only one cron job entry exists for `port_count.sh`, ensuring the bootstrap script's idempotency works correctly.

### 4. Test Output Redirection
Verifies that the cron job redirects output to `/dev/null` to prevent filling up the mail spool with cron emails.

## How to Run

### On an EC2 Instance (After Bootstrap)

1. SSH into your EC2 instance that has been bootstrapped with the Minecraft Dashboard
2. Copy the test file to the instance:
   ```bash
   scp layers/ec2Helper/test_cron_job_installation.py ec2-user@<instance-ip>:~/
   ```

3. Run the test:
   ```bash
   python3 test_cron_job_installation.py
   ```

### Expected Output (Success)

```
======================================================================
Cron Job Installation Tests
Testing Requirements: 2.5, 6.5
======================================================================
Test 1: Verifying cron job exists...
  ✅ PASS: Cron job for port_count.sh found

Test 2: Verifying cron job runs every minute...
  ✅ PASS: Cron job configured to run every minute
     Cron expression: */1 * * * * /usr/local/port_count.sh >/dev/null 2>&1

Test 3: Verifying no duplicate cron jobs...
  ✅ PASS: Exactly one cron job found (no duplicates)

Test 4: Verifying output redirection...
  ✅ PASS: Output is redirected to prevent cron emails

======================================================================
Test Summary: 4/4 tests passed
======================================================================
✅ All tests passed!
```

## Manual Verification

You can also manually verify the cron job installation:

### Check if cron job exists:
```bash
crontab -l | grep port_count.sh
```

Expected output:
```
*/1 * * * * /usr/local/port_count.sh >/dev/null 2>&1
```

### Check if script exists and is executable:
```bash
ls -la /usr/local/port_count.sh
```

Expected output:
```
-rwxr-xr-x 1 root root 256 Nov 20 10:30 /usr/local/port_count.sh
```

### View the script contents:
```bash
cat /usr/local/port_count.sh
```

Expected output:
```bash
#!/bin/bash
INSTANCE_ID="i-1234567890abcdef0"
PORT_COUNT=$(netstat -an | grep ESTABLISHED | grep ':25565' | wc -l)
REGION="us-west-2"
aws cloudwatch put-metric-data --metric-name UserCount --dimensions InstanceId=$INSTANCE_ID --namespace 'MinecraftDashboard' --value $PORT_COUNT --region $REGION
```

### Check cron logs (if available):
```bash
# On systems with systemd
sudo journalctl -u cron | grep port_count

# Or check syslog
sudo grep CRON /var/log/syslog | grep port_count
```

## Bootstrap Script Reference

The cron job is installed by the CloudFormation template at `cfn/templates/ec2.yaml` in the `BootstrapSSMDoc` resource:

```yaml
- action: aws:runShellScript
  name: Cron
  inputs:
    runCommand:
      - '#!/bin/bash'
      - !Sub |
        if [ ! -f /usr/local/port_count.sh ]; then
          # Get instance metadata
          INSTANCE_ID=$(ec2metadata --instance-id)
          REGION=${AWS::Region}
          # Create the script file
          echo "#!/bin/bash" > /usr/local/port_count.sh
          echo "INSTANCE_ID=\"$INSTANCE_ID\"" >> /usr/local/port_count.sh
          echo "PORT_COUNT=\$(netstat -an | grep ESTABLISHED | grep ':25565' | wc -l)" >> /usr/local/port_count.sh
          echo "REGION=\"$REGION\"" >> /usr/local/port_count.sh
          echo "aws cloudwatch put-metric-data --metric-name UserCount --dimensions InstanceId=\$INSTANCE_ID --namespace 'MinecraftDashboard' --value \$PORT_COUNT --region \$REGION" >> /usr/local/port_count.sh
          # Make the script executable
          chmod +x /usr/local/port_count.sh
          # Schedule the script to run every minute
          (sudo crontab -l 2>/dev/null; echo "*/1 * * * * /usr/local/port_count.sh >/dev/null 2>&1") | crontab -         
        fi  
      - sudo crontab -l
```

## Troubleshooting

### Test fails with "Could not read crontab"
- **Cause**: Running on a system without a crontab or without proper permissions
- **Solution**: Run the test on an EC2 instance that has been bootstrapped with the Minecraft Dashboard

### Test fails with "No cron job found"
- **Cause**: The bootstrap script hasn't run or failed to install the cron job
- **Solution**: 
  1. Check if the instance was bootstrapped correctly
  2. Review CloudFormation stack events for errors
  3. Check SSM command execution history in AWS Console

### Test fails with "Duplicate cron jobs found"
- **Cause**: The bootstrap script ran multiple times without proper idempotency check
- **Solution**: 
  1. Remove duplicate entries: `crontab -e` and delete duplicates
  2. Verify the bootstrap script has the `if [ ! -f /usr/local/port_count.sh ]` check

## Integration with CI/CD

This test can be integrated into a CI/CD pipeline that provisions test EC2 instances:

1. Deploy CloudFormation stack with EC2 instance
2. Wait for bootstrap to complete
3. SSH into instance and run test
4. Collect test results
5. Tear down test infrastructure

Example using AWS Systems Manager:

```bash
# Run test via SSM
aws ssm send-command \
  --instance-ids "i-1234567890abcdef0" \
  --document-name "AWS-RunShellScript" \
  --parameters 'commands=["python3 /path/to/test_cron_job_installation.py"]' \
  --region us-west-2
```
