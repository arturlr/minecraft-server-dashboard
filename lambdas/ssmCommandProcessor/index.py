import boto3
import logging
import os
import json
import time
from datetime import datetime, timezone

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ssm = boto3.client('ssm')
ec2_client = boto3.client('ec2')

def check_instance_ready(instance_id):
    """
    Check if instance is ready to receive SSM commands.
    
    Args:
        instance_id (str): EC2 instance ID
        
    Returns:
        dict: {'ready': bool, 'reason': str}
    """
    try:
        response = ec2_client.describe_instance_status(InstanceIds=[instance_id])
        
        if not response['InstanceStatuses']:
            return {'ready': False, 'reason': 'No status information available'}
        
        status = response['InstanceStatuses'][0]
        instance_status = status['InstanceStatus']['Status']
        system_status = status['SystemStatus']['Status']
        
        if instance_status == 'ok' and system_status == 'ok':
            return {'ready': True, 'reason': 'Instance is ready'}
        else:
            return {
                'ready': False,
                'reason': f'Instance status: {instance_status}, System status: {system_status}'
            }
            
    except Exception as e:
        logger.error(f"Error checking instance status: {e}")
        return {'ready': False, 'reason': str(e)}


def send_ssm_command(instance_id, document_name, parameters, comment=None, timeout_seconds=3600):
    """
    Send SSM command to instance with retry logic.
    
    Args:
        instance_id (str): EC2 instance ID
        document_name (str): SSM document name
        parameters (dict): SSM document parameters
        comment (str): Optional comment for the command
        timeout_seconds (int): Command timeout in seconds
        
    Returns:
        dict: {'success': bool, 'commandId': str, 'message': str}
    """
    max_attempts = 10
    wait_time = 30  # seconds between attempts
    
    for attempt in range(1, max_attempts + 1):
        logger.info(f"Attempt {attempt}/{max_attempts} for instance {instance_id}")
        
        # Check if instance is ready
        ready_check = check_instance_ready(instance_id)
        
        if not ready_check['ready']:
            logger.info(f"Instance {instance_id} not ready: {ready_check['reason']}")
            
            if attempt < max_attempts:
                logger.info(f"Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
                continue
            else:
                return {
                    'success': False,
                    'commandId': None,
                    'message': f"Max attempts reached. Last reason: {ready_check['reason']}"
                }
        
        # Instance is ready, try to send command
        try:
            response = ssm.send_command(
                InstanceIds=[instance_id],
                DocumentName=document_name,
                Parameters=parameters,
                Comment=comment or f'SSM command for {instance_id}',
                TimeoutSeconds=timeout_seconds
            )
            
            command_id = response['Command']['CommandId']
            logger.info(f"SSM command sent successfully: CommandId={command_id}, Instance={instance_id}, Document={document_name}")
            
            return {
                'success': True,
                'commandId': command_id,
                'message': 'Command sent successfully'
            }
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error sending SSM command (attempt {attempt}): {error_msg}")
            
            # Check if it's a retryable error
            if 'InvalidInstanceId' in error_msg or 'not in a valid state' in error_msg:
                if attempt < max_attempts:
                    logger.info(f"Retryable error, waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue
                else:
                    return {
                        'success': False,
                        'commandId': None,
                        'message': f"Max attempts reached. Error: {error_msg}"
                    }
            else:
                # Non-retryable error
                return {
                    'success': False,
                    'commandId': None,
                    'message': f"Non-retryable error: {error_msg}"
                }
    
    return {
        'success': False,
        'commandId': None,
        'message': 'Unexpected end of retry loop'
    }


def handler(event, context):
    """
    Process SSM command requests from SQS queue.
    
    Expected message format:
    {
        "instanceId": "i-1234567890abcdef0",
        "documentName": "AWS-RunShellScript",
        "parameters": {
            "commands": ["echo 'Hello World'"]
        },
        "comment": "Optional comment",
        "timeoutSeconds": 3600,
        "metadata": {
            "purpose": "bootstrap",
            "requestedBy": "eventResponse",
            "timestamp": "2025-11-26T10:00:00Z"
        }
    }
    """
    logger.info(f"Processing {len(event['Records'])} SSM command request(s)")
    
    results = []
    
    for record in event['Records']:
        try:
            message = json.loads(record['body'])
            
            # Extract required fields
            instance_id = message.get('instanceId')
            document_name = message.get('documentName')
            parameters = message.get('parameters', {})
            
            # Extract optional fields
            comment = message.get('comment')
            timeout_seconds = message.get('timeoutSeconds', 3600)
            metadata = message.get('metadata', {})
            
            # Validate required fields
            if not instance_id or not document_name:
                logger.error(f"Missing required fields: instanceId={instance_id}, documentName={document_name}")
                results.append({
                    'success': False,
                    'instanceId': instance_id,
                    'message': 'Missing required fields'
                })
                continue
            
            logger.info(f"Processing SSM command: Instance={instance_id}, Document={document_name}, Metadata={metadata}")
            
            # Send SSM command with retry logic
            result = send_ssm_command(
                instance_id=instance_id,
                document_name=document_name,
                parameters=parameters,
                comment=comment,
                timeout_seconds=timeout_seconds
            )
            
            result['instanceId'] = instance_id
            result['documentName'] = document_name
            result['metadata'] = metadata
            results.append(result)
            
            if result['success']:
                logger.info(f"Successfully processed SSM command for {instance_id}: CommandId={result['commandId']}")
            else:
                logger.error(f"Failed to process SSM command for {instance_id}: {result['message']}")
                # Raise exception to trigger SQS retry or DLQ
                raise Exception(f"SSM command failed: {result['message']}")
                
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in message: {e}")
            results.append({
                'success': False,
                'message': f'Invalid JSON: {str(e)}'
            })
        except Exception as e:
            logger.error(f"Error processing record: {e}", exc_info=True)
            # Re-raise to trigger SQS retry
            raise
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': 'SSM command processing completed',
            'results': results,
            'processedCount': len(results),
            'successCount': sum(1 for r in results if r.get('success'))
        })
    }
