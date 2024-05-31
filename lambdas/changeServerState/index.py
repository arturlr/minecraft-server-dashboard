import boto3
import logging
import os
from base64 import b64encode
import helpers

logger = logging.getLogger()
logger.setLevel(logging.INFO)

appValue = os.getenv('TAG_APP_VALUE')
cognito_pool_id = os.getenv('COGNITO_USER_POOL_ID')

utl = helpers.Utils()
dyn = helpers.Dyn()
auth = helpers.Auth(cognito_pool_id)
ec2_client = boto3.client('ec2')

def handler(event, context):
    try:   
        instanceId = event["instanceId"]
        action = event["action"]
        if 'steps' in event:
            steps = event['steps']
        else:
            steps = 0

        instanceInfo = utl.list_server_by_id(instanceId)

        launchTime = instanceInfo["Reservations"]["Instances"][0]["LaunchTime"]            
        state = instanceInfo["Reservations"]["Instances"][0]["State"]["Name"]

        if action == "start":
            instanceStatus = utl.describe_instance_status(instanceId)
            IsInstanceReady = False
            if instanceStatus["initStatus"] == "ok":
                IsInstanceReady = True

            if (state == "stopped"):
                rsp = ec2_client.start_instances(
                    InstanceIds=[ instanceId ]
                )
                # check for Cognito Group for instanceId
                # add group if does not exit with the admin user                

            if steps > 5 :
                logger.error('max steps reached')
                return {'isSuccessful': False, 'err': 'Timeout', 'state': state, 'isInstanceReady': IsInstanceReady,}
            else:
                steps = steps + 1

            return { 
                        'isSuccessful': True, 
                        'action': action,
                        'instanceId': instanceId, 
                        'isInstanceReady': IsInstanceReady,
                        'launchTime': launchTime.strftime("%m/%d/%Y - %H:%M:%S"),
                        'state': state, 
                        'steps': steps
                    }

        elif action == "stop":
            if (state == "running"):
                rsp = ec2_client.stop_instances(
                    InstanceIds=[ instanceId ]
                )
            else:
                logger.error('Stop instance ' + instanceId + ' was not possible as the instance status was ' + state)

        elif action == "restart":
            if (state == "running"):
                rsp = ec2_client.reboot_instances(
                    InstanceIds=[ instanceId ]
                )
            else:
                logger.error('Restart instance ' + instanceId + ' was not possible as the instance status was ' + state)
        
        return { 
                 'isSuccessful': True, 
                 'action': action,
                 'instanceId': instanceId                
                }
            
    except Exception as e:
        logger.error('Something went wrong: ' + str(e))
        return {'isSuccessful': False, 'msg': str(e)}