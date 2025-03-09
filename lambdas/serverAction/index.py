import boto3
import logging
import os
import json
import time
import authHelper
import ec2Helper
import utilHelper

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ec2_client = boto3.client('ec2')

appValue = os.getenv('TAG_APP_VALUE')
ec2_instance_profile_name = os.getenv('EC2_INSTANCE_PROFILE_NAME')
ec2_instance_profile_arn = os.getenv('EC2_INSTANCE_PROFILE_ARN')
config_server_lambda_name = os.getenv('CONFIG_SERVER_LAMBDA_NAME')
cognito_pool_id = os.getenv('COGNITO_USER_POOL_ID')

auth = authHelper.Auth(cognito_pool_id)
ec2_utils = ec2Helper.Ec2Utils()
utl = utilHelper.Utils()

class IamProfile:
    def __init__(self, instance_id):
        self.ec2_client = boto3.client('ec2')
        self.instance_id = instance_id
        self.association_id = None

    def manage_iam_profile(self):
        iam_profile = ec2_utils.describe_iam_profile(self.instance_id, "associated")

        if iam_profile and iam_profile['Arn'] == ec2_instance_profile_arn:
            logger.info(f"Instance IAM Profile is already valid: {iam_profile['Arn']}")
            return True
        elif iam_profile:
            logger.info(f"Instance IAM Profile is invalid: {iam_profile['Arn']}")
            self.association_id = iam_profile['AssociationId']
            rsp = self.disassociate_iam_profile()
            if not rsp:
                return False

        logger.info("Attaching IAM role to the Minecraft Instance")
        return self.attach_iam_profile()

    # This method handles disassociating an IAM instance profile from an EC2 instance
    # Parameters:
    #   association_id: The ID of the IAM instance profile association to remove
    def disassociate_iam_profile(self):
        logger.info(f"Disassociating IAM profile: {self.association_id}")
        # Call EC2 API to remove the profile association
        self.ec2_client.disassociate_iam_instance_profile(AssociationId=self.association_id)

        # Helper function that checks if profile is fully disassociated
        # Returns True if profile is confirmed disassociated, False otherwise
        def check_disassociated_status():
            return ec2_utils.describe_iam_profile(self.instance_id, "disassociated", self.association_id) is not None

        # Retry checking disassociation status for up to 30 times with 5 second delays
        # Return False if profile is not disassociated after all retries
        if not utl.retry_operation(check_disassociated_status, max_retries=30, delay=5):
            logger.warning("Profile timeout during disassociating")
            return False

        # Profile was successfully disassociated
        return True
    
    def attach_iam_profile(self):
        # This method attaches an IAM instance profile to an EC2 instance
        # The profile name and ARN are specified in environment variables
        logger.info(f"Attaching IAM profile: {ec2_instance_profile_name}")
        
        # Call EC2 API to associate the IAM profile with the instance
        response = self.ec2_client.associate_iam_instance_profile(
            IamInstanceProfile={"Name": ec2_instance_profile_name},
            InstanceId=self.instance_id
        )

        # Define helper function to check if profile is properly attached
        def check_associated_status():
            # Get current IAM profile info for the instance
            iam_profile = ec2_utils.describe_iam_profile(self.instance_id, "associated")
            # Verify profile ARN matches expected ARN
            return iam_profile and iam_profile['Arn'] == ec2_instance_profile_arn

        # Retry checking profile association status for up to 30 times with 5 second delays
        # Return False if profile is not attached after all retries
        if not utl.retry_operation(check_associated_status, max_retries=30, delay=5):
            logger.warning("Profile timeout during association")
            return False

        # Profile was successfully attached
        return True

def check_authorization(event, instance_id, user_attributes):
    """
    Check if user is authorized to perform actions on instance
    Args:
        event: Lambda event object containing identity info
        instance_id: EC2 instance ID
        user_attributes: Dict containing user info including email
    Returns:
        bool: True if authorized, False if not
    """
    
    cognitoGroups = event["identity"].get("groups") 
    if cognitoGroups:       
        for group in cognitoGroups:
            if (group == instance_id):   
                logger.info("Authorized server action for email %s on instance %s", user_attributes["email"], instance_id) 
                return True                   

    server_admin_email = ""
    server_info = ec2_utils.list_server_by_id(instance_id)
    instance = server_info['Instances'][0]

    # Extract tags from the instance
    tags = instance.get('Tags', [])
    
    for tag in tags:
        if tag['Key'] == 'Owner':
            server_admin_email = tag['Value']

    if server_admin_email == user_attributes["email"]: 
        logger.info("Authorized server action as owner for email %s on instance %s", user_attributes["email"], instance_id)
        return True
        
    return False

def check_and_create_group(instance_id, user_name):
    """
    Check if Cognito group exists and create it if not
    Args:
        instance_id: EC2 instance ID to use as group name
    Returns:
        bool: True if group exists/created successfully, False if creation failed
    """
    cogGrp = auth.group_exists(instance_id)
    if not cogGrp:
        # Create Group
        logger.warning(f"Group {instance_id} does not exit. Creating one.")
        crtGrp = auth.create_group(instance_id)
        if crtGrp:
            # adding current user to the group
            logger.info("Group created. Now adding user to it.")
            resp = auth.add_user_to_group(instance_id,user_name)
            return resp
        else:
            logger.error("Group creation failed")
            return False
        
    return True

def action_process(action, instance_id, arguments=None):
    """
    Process different actions for a server instance
    
    Args:
        action (str): The action to perform (start/stop/restart etc)
        instance_id (str): The EC2 instance ID
        arguments (dict, optional): Additional arguments for config actions
        
    Returns:
        dict: Response containing status code and message
    """
    logger.info(f"Action: {action} InstanceId: {instance_id}")
    action = action.lower().strip()

    # Map of valid actions to their handlers
    action_handlers = {
        "startserver": lambda: handle_server_action("start", instance_id),
        "restartserver": lambda: handle_server_action("restart", instance_id), 
        "stopserver": lambda: handle_server_action("stop", instance_id),
        "fixserverrole": lambda: handle_fix_role(instance_id),
        "getserverconfig": lambda: handle_get_server_config(instance_id),
        "putserverconfig": lambda: handle_update_server_config(instance_id, arguments),
        "updateserverconfig": lambda: handle_update_server_config(instance_id, arguments)
    }

    # Get the handler for the requested action
    handler = action_handlers.get(action)
    if not handler:
        return utl.response(400, {"err": f"Invalid action: {action}"})

    return handler()

def handle_get_server_config(instance_id):
    """Helper function to handle get server config action"""
    
    instance_tags = ec2_utils.get_instance_attributes_from_tags(instance_id)

    instance_tags['groupMembers'] = auth.list_users_for_group(instance_id)

    # Return the tag dictionary
    return instance_tags

def handle_server_action(action, instance_id):
    try:
        instance = ec2_utils.list_server_by_id(instance_id)
        if not instance.get('Instances'):
            raise ValueError(f"Instance {instance_id} not found")
            
        instance_info = instance['Instances'][0]         
        state = instance_info["State"]["Name"]

        # Handle start action
        if action == "start":
            if state == "stopped":
                ec2_client.start_instances(InstanceIds=[instance_id])
                logger.info(f'Starting instance {instance_id}')
            else:
                logger.warning(f'Start instance {instance_id} not possible - current state: {state}')

        # Handle stop action        
        elif action == "stop":
            if state == "running":
                ec2_client.stop_instances(InstanceIds=[instance_id])
                logger.info(f'Stopping instance {instance_id}')
            else:
                logger.warning(f'Stop instance {instance_id} not possible - current state: {state}')

        # Handle restart action
        elif action == "restart":
            if state == "running":
                ec2_client.reboot_instances(InstanceIds=[instance_id])
                logger.info(f'Restarting instance {instance_id}')
            else:
                logger.warning(f'Restart instance {instance_id} not possible - current state: {state}')                    

        return utl.response(200, f"{action.capitalize()} command submitted")
    
    except Exception as e:
        logger.error(f"Error performing {action} action on instance {instance_id}: {str(e)}")
        return utl.response(500, {"error": f"Failed to {action} instance: {str(e)}"})
    
def handle_fix_role(instance_id):
    """Helper function to handle IAM role fixes"""
    iam_profile = IamProfile(instance_id)
    resp = iam_profile.manage_iam_profile()
    logger.info(f"IAM role attachment response: {resp}")
    
    if resp:
        return utl.response(200, {"msg": "Successfully attached IAM role to the Minecraft Instance"})
    
    logger.error("Attaching IAM role failed")
    return utl.response(500, {"err": "Attaching IAM role failed"})

def handle_update_server_config(instance_id, arguments):
    """Helper function to handle config updates"""
    if not arguments:
        logger.error("Missing arguments for config update")
        return utl.response(400, {"err": "Missing required arguments"})
            
    response = ec2_utils.set_instance_attributes_to_tags(arguments)
    utl.update_alarm(instance_id)
    return response                

def handle_local_invocation(event, context):
    # Handle local invocations here
    return action_process(event["action"], event["instanceId"])

def handler(event, context):
    try:
        if 'request' in event:
            if 'headers' in event['request']:
                if 'authorization' in event['request']['headers']:
                    # Get JWT token from header
                    token = event['request']['headers']['authorization']
                else:
                    logger.error("No Authorization header found")
                    return utl.response(401,{"err": "No Authorization header found" })
            else:
                logger.error("No headers found in request")
                return utl.response(401,{"err": "No headers found in request" })
        else:
            # Local invocation
            return handle_local_invocation(event, context)            
            #logger.error("No request found in event")
            #return utl.response(401,{"err": "No request found in event" })

    except Exception as e:
        logger.error(f"Error processing request: {e}")
        return utl.response(401,{"err": e })

    # Get user info
    user_attributes = auth.process_token(token)    

    # Check if claims are valid
    if user_attributes is None:
        logger.error("Invalid Token")
        return "Invalid Token"

    if not event.get("arguments"):
        logger.error("No arguments found in the event")
        return {"error": "No arguments found in the event"}

    # Extract instance_id from arguments
    instance_id = (event["arguments"].get("instanceId") or 
                  event["arguments"].get("id") or
                  event["arguments"].get("input", {}).get("id"))

    if not instance_id:
        logger.error("Instance id is not present in the event") 
        return {"error": "Instance id is not present in the event"}

    # Extract input arguments if present
    input = None
    if input_args := event["arguments"].get("input"):
        input = {
            'id': instance_id,
            'shutdownMethod': input_args.get('shutdownMethod', ''),
            'scheduleExpression': input_args.get('scheduleExpression', ''),
            'alarmType': input_args.get('alarmType', ''),
            'alarmThreshold': input_args.get('alarmThreshold', ''),
            'alarmEvaluationPeriod': input_args.get('alarmEvaluationPeriod', ''),
            'runCommand': input_args.get('runCommand', ''),
            'workDir': input_args.get('workDir', '')
        }
    
    logger.info(f"Received instanceId: {instance_id}")

    is_authorized = check_authorization(event, instance_id, user_attributes)

    if not is_authorized:
        resp = {"err": "User not authorized"}
        logger.error(user_attributes["email"] + " is not authorized")
        return utl.response(401, resp)
        
    group_check = check_and_create_group(instance_id,user_attributes["username"])     
    if not group_check:        
        logger.error("Group creation failed")          

    # Calling action_process function to process the action with the mutation name
    field_name = event["info"]["fieldName"]
    logger.info(f"Received field name: {field_name}")
    return action_process(field_name,instance_id,input)
    