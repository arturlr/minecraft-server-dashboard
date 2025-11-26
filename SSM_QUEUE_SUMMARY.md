# SSM Command Queue System - Implementation Summary

## What Was Built

A generic, asynchronous system for executing SSM documents on EC2 instances.

## New Components

### 1. Lambda Layer: `ssmHelper`
**Location:** `layers/ssmHelper/`

Shared layer providing functions to queue SSM commands:
- `queue_ssm_command()` - Generic command queueing
- `queue_bootstrap_command()` - Bootstrap shortcut
- `queue_shell_script()` - Linux shell scripts
- `queue_powershell_script()` - Windows PowerShell scripts

### 2. Lambda Function: `ssmCommandProcessor`
**Location:** `lambdas/ssmCommandProcessor/`

Processes SSM commands from queue:
- 10 retry attempts with 30-second intervals
- Checks instance readiness before execution
- Handles any SSM document
- Comprehensive error handling

### 3. SQS Queues
- **SSMCommandQueue** - Main queue (15-min visibility, 24-hr retention)
- **SSMCommandDLQ** - Dead letter queue (14-day retention)

## Modified Components

### 1. `lambdas/eventResponse/index.py`
- Removed synchronous SSM calls with retries
- Now queues bootstrap commands asynchronously
- Added ssmHelper layer import

### 2. `cfn/templates/lambdas.yaml`
- Added SSMCommandQueue and SSMCommandDLQ
- Added SSMCommandProcessor Lambda
- Added SSMLayer (Lambda Layer)
- Updated EventResponse Lambda:
  - Added SSMLayer to layers
  - Removed SSM permissions (now uses SQS)
  - Added SQS SendMessage permission
  - Added SSM_COMMAND_QUEUE_URL environment variable

## Usage

### In Any Lambda Function

```python
# Import the layer
import sys
sys.path.insert(0, '/opt/python')
import ssmHelper

ssm_helper = ssmHelper.SSMHelper()

# Queue bootstrap command
result = ssm_helper.queue_bootstrap_command(
    instance_id='i-1234567890abcdef0'
)

# Queue shell script
result = ssmHelper.queue_shell_script(
    instance_id='i-1234567890abcdef0',
    commands=['systemctl restart minecraft'],
    metadata={'purpose': 'restart-service'}
)

# Queue any SSM document
result = ssmHelper.queue_ssm_command(
    instance_id='i-1234567890abcdef0',
    document_name='MyCustomDocument',
    parameters={'param': ['value']},
    metadata={'purpose': 'custom-task'}
)
```

## Benefits

✅ **Generic** - Works with any SSM document
✅ **Asynchronous** - No blocking, no Lambda timeouts
✅ **Reliable** - Automatic retries + dead letter queue
✅ **Scalable** - Queue handles bursts of commands
✅ **Reusable** - Lambda Layer shared across functions
✅ **Observable** - CloudWatch logs and metrics
✅ **Cost-effective** - ~$0.0006 per 1000 commands

## Deployment

```bash
# Build Lambda layers
cd layers/ssmHelper && make

# Deploy CloudFormation
cd cfn
sam build
sam deploy
```

## How It Works

```
Lambda (eventResponse, serverAction, etc.)
  ↓ calls ssmHelper.queue_bootstrap_command()
  ↓
SQS Queue (SSMCommandQueue)
  ↓ triggers
  ↓
Lambda (ssmCommandProcessor)
  ↓ checks instance readiness (10 attempts × 30s)
  ↓ sends SSM command when ready
  ↓
Success → Command executed
Failure → Dead Letter Queue (DLQ)
```

## Monitoring

**CloudWatch Logs:**
- `/aws/lambda/msd-dev-ssmCommandProcessor`

**Key Metrics:**
- SQS Queue Depth
- Lambda Duration
- Lambda Errors
- DLQ Message Count

**Recommended Alarm:**
```yaml
SSMCommandDLQAlarm:
  Threshold: 1 message in DLQ
  Action: Notify operations team
```

## Future Use Cases

This system can now handle:
- ✅ Bootstrap new instances
- ✅ Update Minecraft server versions
- ✅ Install/update CloudWatch agent
- ✅ Run maintenance scripts
- ✅ Apply security patches
- ✅ Configure monitoring
- ✅ Any custom SSM document

## Documentation

See `docs/ssm-command-queue-system.md` for complete documentation including:
- Architecture details
- Usage examples
- Troubleshooting guide
- Security considerations
- Cost analysis
