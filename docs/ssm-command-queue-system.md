# Generic SSM Command Queue System

## Overview

A generic, asynchronous system for executing SSM documents on EC2 instances with automatic retries and error handling.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Any Lambda (eventResponse, serverAction, etc.)             │
│ - Calls ssmHelper.queue_ssm_command()                      │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ SQS Queue: SSMCommandQueue                                  │
│ - Buffers commands                                          │
│ - Visibility timeout: 15 minutes                            │
│ - Max retries: 3                                            │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ Lambda: SSMCommandProcessor                                 │
│ - Checks instance readiness (10 attempts, 30s intervals)   │
│ - Sends SSM command when ready                              │
│ - Updates status in logs                                    │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ├─ Success → Command executed
                     │
                     └─ Failure → Dead Letter Queue (DLQ)
```

## Components

### 1. SQS Queues

**Main Queue: `SSMCommandQueue`**
- Visibility timeout: 900 seconds (15 minutes)
- Message retention: 24 hours
- Max receive count: 3 (then moves to DLQ)

**Dead Letter Queue: `SSMCommandDLQ`**
- Message retention: 14 days
- For manual investigation of failed commands

### 2. Lambda: SSMCommandProcessor

**Timeout:** 900 seconds (15 minutes)
**Retry Logic:** 10 attempts with 30-second intervals
**Batch Size:** 1 (processes one command at a time)

**Features:**
- Checks instance status before sending command
- Waits for SSM agent to be ready
- Handles transient errors with retries
- Logs detailed execution information

### 3. Lambda Layer: ssmHelper

A shared Lambda Layer (`layers/ssmHelper/`) that provides the `SSMHelper` class for queueing SSM commands:

```python
import ssmHelper

# Initialize the helper
ssm_helper = ssmHelper.SSMHelper()

# Generic SSM command
ssm_helper.queue_ssm_command(
    instance_id='i-1234567890abcdef0',
    document_name='MyCustomDocument',
    parameters={'param1': ['value1']},
    comment='My custom command',
    timeout_seconds=3600,
    metadata={'purpose': 'custom-task'}
)

# Bootstrap command
ssm_helper.queue_bootstrap_command(
    instance_id='i-1234567890abcdef0'
)

# Shell script
ssm_helper.queue_shell_script(
    instance_id='i-1234567890abcdef0',
    commands=[
        'echo "Hello World"',
        'systemctl restart myservice'
    ],
    working_directory='/opt/myapp',
    metadata={'purpose': 'restart-service'}
)

# PowerShell script (Windows)
ssm_helper.queue_powershell_script(
    instance_id='i-1234567890abcdef0',
    commands=[
        'Write-Host "Hello World"',
        'Restart-Service MyService'
    ],
    metadata={'purpose': 'restart-service'}
)
```

## Message Format

```json
{
  "instanceId": "i-1234567890abcdef0",
  "documentName": "AWS-RunShellScript",
  "parameters": {
    "commands": ["echo 'Hello World'"],
    "workingDirectory": ["/opt/myapp"]
  },
  "comment": "Optional comment",
  "timeoutSeconds": 3600,
  "metadata": {
    "purpose": "custom-task",
    "requestedBy": "eventResponse",
    "queuedAt": "2025-11-26T10:00:00Z"
  }
}
```

## Usage Examples

### Example 1: Bootstrap New Instance

```python
# In eventResponse Lambda
import ssmHelper

ssm_helper = ssmHelper.SSMHelper()

def bootstrap_server(instance_id):
    config = dyn.get_server_config(instance_id)
    
    if not config.get('isBootstrapComplete'):
        result = ssm_helper.queue_bootstrap_command(
            instance_id=instance_id
        )
        
        if result['success']:
            logger.info(f"Bootstrap queued: {result['messageId']}")
```

### Example 2: Update Minecraft Server

```python
import ssmHelper

ssm_helper = ssmHelper.SSMHelper()

# Queue command to update Minecraft server
ssm_helper.queue_shell_script(
    instance_id='i-1234567890abcdef0',
    commands=[
        'cd /home/ec2-user/minecraft',
        'wget https://example.com/server.jar -O server.jar',
        'systemctl restart minecraft'
    ],
    working_directory='/home/ec2-user/minecraft',
    metadata={
        'purpose': 'update-minecraft',
        'version': '1.20.4',
        'requestedBy': 'admin'
    }
)
```

### Example 3: Install CloudWatch Agent

```python
import ssmHelper

ssm_helper = ssmHelper.SSMHelper()

# Queue command to install CloudWatch agent
ssm_helper.queue_ssm_command(
    instance_id='i-1234567890abcdef0',
    document_name='AWS-ConfigureAWSPackage',
    parameters={
        'action': ['Install'],
        'name': ['AmazonCloudWatchAgent']
    },
    comment='Install CloudWatch Agent',
    metadata={'purpose': 'monitoring-setup'}
)
```

### Example 4: Run Custom SSM Document

```python
import ssmHelper

ssm_helper = ssmHelper.SSMHelper()

# Queue custom document execution
ssm_helper.queue_ssm_command(
    instance_id='i-1234567890abcdef0',
    document_name='MyCompany-CustomSetup',
    parameters={
        'Environment': ['production'],
        'Version': ['2.0.1']
    },
    comment='Custom setup for production',
    timeout_seconds=7200,  # 2 hours
    metadata={
        'purpose': 'custom-setup',
        'environment': 'production'
    }
)
```

## Monitoring

### CloudWatch Logs

**SSMCommandProcessor Logs:**
```
/aws/lambda/msd-dev-ssmCommandProcessor
```

**Key Log Messages:**
- `"Processing SSM command request(s)"` - Command received
- `"Instance ready"` - Instance passed readiness check
- `"SSM command sent successfully"` - Command executed
- `"Max attempts reached"` - Failed after all retries

### CloudWatch Metrics

Monitor these metrics:
- **SQS Queue Depth** - Number of pending commands
- **Lambda Duration** - Processing time
- **Lambda Errors** - Failed executions
- **DLQ Messages** - Commands that failed permanently

### Alarms (Recommended)

```yaml
SSMCommandDLQAlarm:
  Type: AWS::CloudWatch::Alarm
  Properties:
    AlarmName: SSMCommandDLQ-HasMessages
    MetricName: ApproximateNumberOfMessagesVisible
    Namespace: AWS/SQS
    Statistic: Average
    Period: 300
    EvaluationPeriods: 1
    Threshold: 1
    ComparisonOperator: GreaterThanOrEqualToThreshold
    Dimensions:
      - Name: QueueName
        Value: !GetAtt SSMCommandDLQ.QueueName
```

## Troubleshooting

### Command Stuck in Queue

**Symptoms:** Messages visible in queue but not processing

**Possible Causes:**
1. Lambda function has errors
2. Instance not ready (still initializing)
3. SSM agent not running on instance

**Resolution:**
```bash
# Check Lambda logs
aws logs tail /aws/lambda/msd-dev-ssmCommandProcessor --follow

# Check queue attributes
aws sqs get-queue-attributes \
  --queue-url <QUEUE_URL> \
  --attribute-names All

# Check instance SSM status
aws ssm describe-instance-information \
  --filters "Key=InstanceIds,Values=i-1234567890abcdef0"
```

### Commands in DLQ

**Symptoms:** Messages in dead letter queue

**Possible Causes:**
1. Instance never became ready (terminated, stopped)
2. SSM document doesn't exist
3. Permission issues

**Resolution:**
```bash
# View DLQ messages
aws sqs receive-message \
  --queue-url <DLQ_URL> \
  --max-number-of-messages 10

# Manually retry a message
aws sqs send-message \
  --queue-url <MAIN_QUEUE_URL> \
  --message-body '<message_body_from_dlq>'
```

### Instance Not Ready

**Symptoms:** Logs show "Instance not ready" repeatedly

**Possible Causes:**
1. Instance still booting
2. SSM agent not installed
3. IAM role missing

**Resolution:**
```bash
# Check instance status
aws ec2 describe-instance-status \
  --instance-ids i-1234567890abcdef0

# Check SSM agent status
aws ssm describe-instance-information \
  --filters "Key=InstanceIds,Values=i-1234567890abcdef0"

# Check IAM instance profile
aws ec2 describe-instances \
  --instance-ids i-1234567890abcdef0 \
  --query 'Reservations[0].Instances[0].IamInstanceProfile'
```

## Best Practices

1. **Use Metadata** - Always include metadata for tracking and debugging
2. **Set Appropriate Timeouts** - Match timeout to expected execution time
3. **Monitor DLQ** - Set up alarms for messages in DLQ
4. **Test Documents** - Test SSM documents manually before queueing
5. **Idempotent Commands** - Design commands to be safely retried
6. **Log Context** - Include instance ID and purpose in all logs

## Security

### IAM Permissions

**SSMCommandProcessor Lambda needs:**
```yaml
- ssm:SendCommand
- ssm:GetCommandInvocation
- ssm:ListCommandInvocations
- ec2:DescribeInstanceStatus
```

**Calling Lambdas need:**
```yaml
- sqs:SendMessage (on SSMCommandQueue)
```

**EC2 Instances need:**
```yaml
- ssm:UpdateInstanceInformation
- ssm:ListAssociations
- ssm:ListInstanceAssociations
- s3:GetObject (for SSM documents in S3)
```

### Document Permissions

SSM documents can be:
- **AWS-managed** - Available to all accounts
- **Account-owned** - Restricted to your account
- **Shared** - Shared across accounts

Ensure Lambda has permission to execute the specific document.

## Cost Optimization

- **SQS:** ~$0.40 per million requests
- **Lambda:** ~$0.20 per million requests (128MB, 1s avg)
- **SSM:** No additional charge for SendCommand

**Estimated monthly cost for 1000 commands:**
- SQS: $0.0004
- Lambda: $0.0002
- **Total: ~$0.0006/month**

Very cost-effective for asynchronous command execution!

## Future Enhancements

1. **Status Tracking** - Store command status in DynamoDB
2. **Web UI** - View pending/completed commands
3. **Command History** - Track all executed commands
4. **Approval Workflow** - Require approval for certain commands
5. **Scheduled Commands** - Execute commands at specific times
6. **Command Templates** - Pre-defined command templates
7. **Bulk Operations** - Execute same command on multiple instances
