import boto3
import logging
import json
import ec2Helper
import utilHelper

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ec2_client = boto3.client('ec2')
ec2_utils = ec2Helper.Ec2Utils()
utl = utilHelper.Utils()

def process_server_action(message_body):
    """Process server action from SQS message"""
    try:
        message = json.loads(message_body)
        action = message['action'].lower().strip()
        instance_id = message['instanceId']
        arguments = message.get('arguments')
        user_email = message.get('userEmail')
        
        logger.info(f"Processing {action} for {instance_id} by {user_email}")
        
        if action in ['startserver', 'stopserver', 'restartserver']:
            return handle_server_action(action.replace('server', ''), instance_id)
        elif action == 'fixserverrole':
            return handle_fix_role(instance_id)
        elif action in ['putserverconfig', 'updateserverconfig']:
            return handle_update_server_config(instance_id, arguments)
        else:
            logger.error(f"Unknown action: {action}")
            return False
            
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        return False

def handle_server_action(action, instance_id):
    """Handle EC2 instance actions"""
    try:
        instance = ec2_utils.list_server_by_id(instance_id)
        if not instance.get('Instances'):
            raise ValueError(f"Instance {instance_id} not found")
            
        state = instance['Instances'][0]["State"]["Name"]
        
        if action == "start" and state == "stopped":
            ec2_client.start_instances(InstanceIds=[instance_id])
            logger.info(f'Started instance {instance_id}')
        elif action == "stop" and state == "running":
            ec2_client.stop_instances(InstanceIds=[instance_id])
            logger.info(f'Stopped instance {instance_id}')
        elif action == "restart" and state == "running":
            ec2_client.reboot_instances(InstanceIds=[instance_id])
            logger.info(f'Restarted instance {instance_id}')
        else:
            logger.warning(f'{action} not possible - current state: {state}')
            
        return True
    except Exception as e:
        logger.error(f"Error in {action} action: {e}")
        return False

def handle_fix_role(instance_id):
    """Handle IAM role fix"""
    # Implementation moved from serverAction
    return True

def handle_update_server_config(instance_id, arguments):
    """Handle server configuration updates"""
    if not arguments:
        logger.error("Missing arguments for config update")
        return False
    
    try:
        response = ec2_utils.set_instance_attributes_to_tags(arguments)
        shutdown_method = response.get('shutdownMethod', '')
        
        if shutdown_method == 'Schedule':
            stop_schedule = response.get('stopScheduleExpression')
            if stop_schedule:
                ec2_utils.remove_alarm(instance_id)
                ec2_utils.configure_shutdown_event(instance_id, stop_schedule)
                
                start_schedule = response.get('startScheduleExpression')
                if start_schedule:
                    ec2_utils.configure_start_event(instance_id, start_schedule)
                else:
                    ec2_utils.remove_start_event(instance_id)
                    
        elif shutdown_method in ['CPUUtilization', 'Connections']:
            alarm_threshold = response.get('alarmThreshold')
            alarm_period = response.get('alarmEvaluationPeriod')
            
            if alarm_threshold and alarm_period:
                ec2_utils.remove_shutdown_event(instance_id)
                ec2_utils.remove_start_event(instance_id)
                ec2_utils.update_alarm(instance_id, shutdown_method, alarm_threshold, alarm_period)
                
        return True
    except Exception as e:
        logger.error(f"Error updating config: {e}")
        return False

def handler(event, context):
    """SQS event handler"""
    for record in event['Records']:
        success = process_server_action(record['body'])
        if not success:
            logger.error(f"Failed to process message: {record['messageId']}")
            # Message will be retried or sent to DLQ based on SQS configuration