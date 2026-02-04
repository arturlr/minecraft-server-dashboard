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

