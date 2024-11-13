import boto3
import logging
import os
from base64 import b64encode
import ec2Helper
import utilHelper
import authHelper

logger = logging.getLogger()
logger.setLevel(logging.INFO)

appValue = os.getenv('TAG_APP_VALUE')
cognito_pool_id = os.getenv('COGNITO_USER_POOL_ID')

utl = utilHelper.Utils()
auth = authHelper.Auth(cognito_pool_id)
ec2_utils = ec2Helper.Ec2Utils()
ec2_client = boto3.client('ec2')

def handle_start(instanceId, state, steps, launchTime):
    instanceStatus = utl.describe_instance_status(instanceId)
    IsInstanceReady = instanceStatus["initStatus"] == "ok"

    if state == "stopped":
        ec2_client.start_instances(InstanceIds=[instanceId])
        # check for Cognito Group for instanceId
        # add group if does not exit with the admin user                

    if steps > 5:
        logger.error('max steps reached')
        return {
            'isSuccessful': False, 
            'err': 'Timeout', 
            'state': state, 
            'isInstanceReady': IsInstanceReady
        }
    
    return { 
        'isSuccessful': True, 
        'action': 'start',
        'instanceId': instanceId, 
        'isInstanceReady': IsInstanceReady,
        'launchTime': launchTime.strftime("%m/%d/%Y - %H:%M:%S"),
        'state': state, 
        'steps': steps + 1
    }

def handle_stop(instanceId, state):
    if state == "running":
        ec2_client.stop_instances(InstanceIds=[instanceId])
    else:
        logger.error(f'Stop instance {instanceId} not possible - current state: {state}')

def handle_restart(instanceId, state):
    if state == "running":
        ec2_client.reboot_instances(InstanceIds=[instanceId])
    else:
        logger.error(f'Restart instance {instanceId} not possible - current state: {state}')


def handler(event, context):
    try:   
        # Extract and validate required parameters
        instanceId = event.get("instanceId")
        action = event.get("action")
        if not instanceId or not action:
            raise ValueError("Missing required parameters: instanceId and action")
            
        steps = event.get('steps', 0)

        # Get instance details
        instance = ec2_utils.list_server_by_id(instanceId)
        if not instance.get('Instances'):
            raise ValueError(f"Instance {instanceId} not found")
            
        instance_info = instance['Instances'][0]

        launchTime = instance_info["LaunchTime"]            
        state = instance_info["State"]["Name"]

        # Define allowed actions
        actions = {
            "start": lambda: handle_start(instanceId, state, steps, launchTime),
            "stop": lambda: handle_stop(instanceId, state),
            "restart": lambda: handle_restart(instanceId, state)
        }

        # Execute requested action if valid
        if action not in actions:
            raise ValueError(f"Invalid action: {action}")
            
        result = actions[action]()
        if result:
            return result

        return { 
            'isSuccessful': True, 
            'action': action,
            'instanceId': instanceId                
        }
            
    except Exception as e:
        logger.error(f'Error processing request: {str(e)}')
        return {'isSuccessful': False, 'msg': str(e)}

