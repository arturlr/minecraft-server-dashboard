import boto3
import json
import logging
import os
from datetime import datetime, timezone

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class SSMHelper:
    def __init__(self,queue_url, bootstrap_doc_name):
        """Initialize SSM Helper with SQS client and configuration."""
        logger.info(f"------- SSMHelper Class Initialization {queue_url} {bootstrap_doc_name}")
        self.sqs = boto3.client('sqs')

        queue_url = queue_url or os.getenv('SSM_COMMAND_QUEUE_URL')
        bootstrap_doc_name = bootstrap_doc_name or os.getenv('BOOTSTRAP_SSM_DOC_NAME')
        if not queue_url or not bootstrap_doc_name:
            raise ValueError("Required environment variables missing or empty")

        self.queue_url = queue_url
        self.bootstrap_doc_name = bootstrap_doc_name
    
    def get_bootstrap_script(self, support_bucket, script_version, run_command, project_name, env_name):
        """Generate inline bootstrap script for AWS-RunShellScript."""
        return f"""#!/bin/bash
set +e

SCRIPT_VERSION="{script_version}"
REGION=$(curl -s http://169.254.169.254/latest/meta-data/placement/region)
INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)

echo "=== Bootstrap Script Version: $SCRIPT_VERSION ==="
echo "=== Instance: $INSTANCE_ID ==="
echo "[$(date)] Starting package installation"

# Update and install packages
apt-get update
apt-get install -y jq zip unzip net-tools wget screen openjdk-21-jre-headless

# Install AWS CLI
if ! command -v aws >/dev/null 2>&1; then
    mkdir -p /usr/share/collectd
    touch /usr/share/collectd/types.db
    curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
    unzip awscliv2.zip
    ./aws/install
    rm -rf aws awscliv2.zip
fi

echo "[$(date)] Packages installed"

# Download helper functions
aws s3 cp s3://{support_bucket}/scripts/$SCRIPT_VERSION/00-bootstrap-helper.sh /tmp/bootstrap-helper.sh --region $REGION
chmod +x /tmp/bootstrap-helper.sh
source /tmp/bootstrap-helper.sh {project_name} {env_name}

CRITICAL_FAILURE=0

# Setup Metrics
echo "=== Setting up Metrics ==="
aws s3 cp s3://{support_bucket}/scripts/$SCRIPT_VERSION/05-setup-metrics.sh /tmp/setup-metrics.sh --region $REGION
chmod +x /tmp/setup-metrics.sh
run_stage "metrics" /tmp/setup-metrics.sh {support_bucket} || echo "⚠ Metrics setup failed"

# Setup Log Server
echo "=== Setting up Log Server ==="
aws s3 cp s3://{support_bucket}/scripts/$SCRIPT_VERSION/07-setup-log-server.sh /tmp/setup-log-server.sh --region $REGION
chmod +x /tmp/setup-log-server.sh
run_stage "logs" /tmp/setup-log-server.sh {support_bucket} || echo "⚠ Log server setup failed"

# Setup Minecraft Service (CRITICAL)
echo "=== Setting up Minecraft Service ==="
aws s3 cp s3://{support_bucket}/scripts/$SCRIPT_VERSION/09-setup-minecraft-service.sh /tmp/setup-minecraft-service.sh --region $REGION
chmod +x /tmp/setup-minecraft-service.sh
if ! run_stage "minecraft" /tmp/setup-minecraft-service.sh "{run_command}"; then
    echo "✗ Minecraft setup failed - CRITICAL"
    CRITICAL_FAILURE=1
fi

# Update Status
aws s3 cp s3://{support_bucket}/scripts/$SCRIPT_VERSION/10-update-bootstrap-status.sh /tmp/update-bootstrap-status.sh --region $REGION
chmod +x /tmp/update-bootstrap-status.sh

if [ $CRITICAL_FAILURE -eq 0 ]; then
    /tmp/update-bootstrap-status.sh {project_name} {env_name}
    update_bootstrap_stage "complete" "completed"
    echo "=== Bootstrap completed successfully ==="
    exit 0
else
    update_bootstrap_stage "complete" "failed" "Critical stage failed"
    echo "=== Bootstrap FAILED ==="
    exit 1
fi
"""
    
    def queue_ssm_command(self, instance_id, document_name, parameters, comment=None, timeout_seconds=3600, metadata=None):
        """
        Queue an SSM command for asynchronous execution.
        
        Args:
            instance_id (str): EC2 instance ID
            document_name (str): SSM document name
            parameters (dict): SSM document parameters
            comment (str): Optional comment
            timeout_seconds (int): Command timeout
            metadata (dict): Optional metadata for tracking
            
        Returns:
            dict: {'success': bool, 'messageId': str, 'message': str}
        """
        if not self.queue_url:
            logger.error("SSM_COMMAND_QUEUE_URL environment variable not set")
            return {
                'success': False,
                'messageId': None,
                'message': 'Queue URL not configured'
            }
        
        try:
            message_body = {
                'instanceId': instance_id,
                'documentName': document_name,
                'parameters': parameters,
                'comment': comment,
                'timeoutSeconds': timeout_seconds,
                'metadata': metadata or {}
            }
            
            # Add timestamp to metadata
            message_body['metadata']['queuedAt'] = datetime.now(timezone.utc).isoformat()
            
            response = self.sqs.send_message(
                QueueUrl=self.queue_url,
                MessageBody=json.dumps(message_body)
            )
            
            message_id = response['MessageId']
            logger.info(f"Queued SSM command for {instance_id}: Document={document_name}, MessageId={message_id}")
            
            return {
                'success': True,
                'messageId': message_id,
                'message': 'Command queued successfully'
            }
            
        except Exception as e:
            logger.error(f"Error queueing SSM command: {e}", exc_info=True)
            return {
                'success': False,
                'messageId': None,
                'message': str(e)
            }

    def queue_bootstrap_command(self, instance_id, run_command, script_version='latest'):
        """
        Queue bootstrap SSM command for an instance.
        
        Args:
            instance_id (str): EC2 instance ID
            run_command (str): Minecraft server run command
            script_version (str): Version of bootstrap scripts to use (default: latest)
            
        Returns:
            dict: Result from queue_ssm_command
        """
        if not self.bootstrap_doc_name:
            logger.error("BOOTSTRAP_SSM_DOC_NAME environment variable not set")
            return {
                'success': False,
                'messageId': None,
                'message': 'Bootstrap document name not configured'
            }
        
        return self.queue_ssm_command(
            instance_id=instance_id,
            document_name=self.bootstrap_doc_name,
            parameters={
                'runCommand': [run_command],
                'scriptVersion': [script_version]
            },
            comment=f'Bootstrap server {instance_id} with scripts {script_version}',
            timeout_seconds=3600,
            metadata={
                'purpose': 'bootstrap',
                'requestedBy': 'system',
                'scriptVersion': script_version
            }
        )

    def queue_shell_script(self, instance_id, commands, working_directory=None, timeout_seconds=3600, metadata=None):
        """
        Queue a shell script execution via AWS-RunShellScript document.
        
        Args:
            instance_id (str): EC2 instance ID
            commands (list): List of shell commands to execute
            working_directory (str): Optional working directory
            timeout_seconds (int): Command timeout
            metadata (dict): Optional metadata
            
        Returns:
            dict: Result from queue_ssm_command
        """
        parameters = {'commands': commands}
        
        if working_directory:
            parameters['workingDirectory'] = [working_directory]
        
        return self.queue_ssm_command(
            instance_id=instance_id,
            document_name='AWS-RunShellScript',
            parameters=parameters,
            comment=f'Shell script execution for {instance_id}',
            timeout_seconds=timeout_seconds,
            metadata=metadata or {'purpose': 'shell-script'}
        )

