import boto3
import logging
import os
import json
import ssmHelper
import ddbHelper
import utilHelper

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ssm = boto3.client('ssm')
core_dyn = ddbHelper.CoreTableDyn()

def handler(event, context):
    """
    Bootstrap a server by sending SSM command directly.
    Triggered by GraphQL mutation.
    """
    try:
        logger.info(f"Bootstrap request: {json.dumps(event)}")
        
        # Extract instance ID
        instance_id = event.get('arguments', {}).get('instanceId')
        if not instance_id:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Missing instanceId'})
            }
        
        # Check authorization
        identity = event.get('identity', {})
        username = identity.get('username')
        
        if not utilHelper.is_authorized(username, instance_id):
            logger.warning(f"Unauthorized bootstrap attempt by {username} for {instance_id}")
            return {
                'statusCode': 403,
                'body': json.dumps({'error': 'Unauthorized'})
            }
        
        # Get server config
        config = core_dyn.get_server_config(instance_id)
        if not config:
            return {
                'statusCode': 404,
                'body': json.dumps({'error': 'Server config not found'})
            }
        
        run_command = config.get('runCommand', 'java -Xmx1024M -Xms1024M -jar server.jar nogui')
        script_version = config.get('scriptVersion', 'latest')
        
        # Get environment variables
        support_bucket = os.getenv('SUPPORT_BUCKET')
        project_name = os.getenv('APP_NAME')
        env_name = os.getenv('ENVIRONMENT_NAME')
        
        if not all([support_bucket, project_name, env_name]):
            logger.error("Missing required environment variables")
            return {
                'statusCode': 500,
                'body': json.dumps({'error': 'Server configuration error'})
            }
        
        # Generate bootstrap script
        ssm_helper = ssmHelper.SSMHelper()
        bootstrap_script = ssm_helper.get_bootstrap_script(
            support_bucket=support_bucket,
            script_version=script_version,
            run_command=run_command,
            project_name=project_name,
            env_name=env_name
        )
        
        # Send SSM command directly
        response = ssm.send_command(
            InstanceIds=[instance_id],
            DocumentName='AWS-RunShellScript',
            Parameters={'commands': [bootstrap_script]},
            Comment=f'Bootstrap {instance_id}',
            TimeoutSeconds=3600
        )
        
        command_id = response['Command']['CommandId']
        logger.info(f"Bootstrap command sent: {command_id}")
        
        # Update bootstrap status
        core_dyn.update_server_info(instance_id, {
            'bootstrapStatus': 'in_progress',
            'lastBootstrapCommandId': command_id
        })
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Bootstrap started',
                'commandId': command_id
            })
        }
        
    except Exception as e:
        logger.error(f"Bootstrap error: {e}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
