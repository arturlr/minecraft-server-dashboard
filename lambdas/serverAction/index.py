import boto3
import logging
import os
import json
import time
import authHelper
import ec2Helper
import utilHelper
import botocore.exceptions

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ec2_client = boto3.client('ec2')

appValue = os.getenv('TAG_APP_VALUE')
ec2_instance_profile_name = os.getenv('EC2_INSTANCE_PROFILE_NAME')
ec2_instance_profile_arn = os.getenv('EC2_INSTANCE_PROFILE_ARN')
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
        try:
            iam_profile = ec2_utils.describe_iam_profile(self.instance_id, "associated")

            if iam_profile and iam_profile['Arn'] == ec2_instance_profile_arn:
                logger.info("Instance IAM Profile is already valid: %s", iam_profile['Arn'])
                return True
            elif iam_profile:
                logger.info("Instance IAM Profile is invalid: %s", iam_profile['Arn'])
                self.association_id = iam_profile['AssociationId']
                rsp = self.disassociate_iam_profile()
                if not rsp:
                    return False
        except Exception as e:
            # If we can't describe the profile, log it but continue with attachment
            logger.warning("Error describing IAM profile: %s. Will attempt to attach profile anyway.", str(e))
            # If the error is about an invalid association ID, we can continue

        logger.info("Attaching IAM role to the Minecraft Instance")
        return self.attach_iam_profile()

    # This method handles disassociating an IAM instance profile from an EC2 instance
    # Parameters:
    #   association_id: The ID of the IAM instance profile association to remove
    def disassociate_iam_profile(self):
        logger.info("Disassociating IAM profile: %s", self.association_id)
        try:
            # Call EC2 API to remove the profile association
            self.ec2_client.disassociate_iam_instance_profile(AssociationId=self.association_id)
        except botocore.exceptions.ClientError as e:
            if "InvalidAssociationID.NotFound" in str(e):
                # Handle the case where the association ID doesn't exist
                logger.warning("Association ID not found: %s. This is not an error, continuing...", self.association_id)
                # Return True to continue with attaching the profile
                return True
            else:
                logger.error("Error disassociating IAM profile: %s", str(e))
                return False
        except Exception as e:
            logger.error("Error disassociating IAM profile: %s", str(e))
            return False

        # Helper function that checks if profile is fully disassociated
        # Returns True if profile is confirmed disassociated, False otherwise
        def check_disassociated_status():
            try:
                return ec2_utils.describe_iam_profile(self.instance_id, "disassociated", self.association_id) is not None
            except Exception as e:
                # If we get an error checking the status, assume it's disassociated
                logger.warning("Error checking disassociation status: %s. Assuming profile is disassociated.", str(e))
                return True

        # Retry checking disassociation status for up to 30 times with 5 second delays
        # Return False if profile is not disassociated after all retries
        if not utl.retry_operation(check_disassociated_status, max_retries=30, delay=5):
            logger.warning("Profile timeout during disassociating")
            # Even if we time out, we'll try to attach the new profile anyway
            return True

        # Profile was successfully disassociated
        return True
    
    def attach_iam_profile(self):
        # This method attaches an IAM instance profile to an EC2 instance
        # The profile name and ARN are specified in environment variables
        logger.info("Attaching IAM profile: %s", ec2_instance_profile_name)
        
        try:
            # Call EC2 API to associate the IAM profile with the instance
            response = self.ec2_client.associate_iam_instance_profile(
                IamInstanceProfile={"Name": ec2_instance_profile_name},
                InstanceId=self.instance_id
            )
        except botocore.exceptions.ClientError as e:
            error_msg = str(e)
            # Check if this is an unauthorized operation
            if "UnauthorizedOperation" in error_msg:
                logger.error("Unauthorized operation when attaching IAM profile: %s", error_msg)
                return {"status": "error", "message": error_msg, "code": "UnauthorizedOperation"}
            else:
                logger.error("Error attaching IAM profile: %s", error_msg)
                return False
        except Exception as e:
            logger.error("Error attaching IAM profile: %s", str(e))
            return False

        # Define helper function to check if profile is properly attached
        def check_associated_status():
            try:
                # Get current IAM profile info for the instance
                iam_profile = ec2_utils.describe_iam_profile(self.instance_id, "associated")
                # Verify profile ARN matches expected ARN
                return iam_profile and iam_profile['Arn'] == ec2_instance_profile_arn
            except Exception as e:
                logger.warning("Error checking association status: %s", str(e))
                return False

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
    
    cognito_groups = event["identity"].get("groups", [])
    user_email = user_attributes["email"]
    
    # Use the centralized authorization check from utilHelper
    is_authorized, auth_reason = utl.check_user_authorization(
        cognito_groups, 
        instance_id, 
        user_email, 
        ec2_utils
    )
    
    if is_authorized:
        if auth_reason == "admin_group":
            logger.info("Authorized server action for admin user %s on instance %s", user_email, instance_id)
        elif auth_reason == "instance_group":
            logger.info("Authorized server action for group member %s on instance %s", user_email, instance_id)
        elif auth_reason == "instance_owner":
            logger.info("Authorized server action as owner for email %s on instance %s", user_email, instance_id)
    
    return is_authorized

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
        logger.warning("Group %s does not exit. Creating one.", instance_id)
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
    logger.info("Action: %s InstanceId: %s", action, instance_id)
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

def handle_get_server_users(instance_id):
    """Helper function to handle get server users action"""
    try:
        # Get the list of users for the given instance_id
        users = auth.list_users_for_group(instance_id)
        return users
    
    except Exception as e:
        logger.error("Error retrieving users for instance %s: %s", instance_id, str(e))
        return utl.response(500, {"error": f"Failed to retrieve users: {str(e)}"})    

def handle_get_server_config(instance_id):
    """Helper function to handle get server config action"""
    
    instance_tags = ec2_utils.get_instance_attributes_from_tags(instance_id)

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
                logger.info('Starting instance %s', instance_id)
            else:
                logger.warning('Start instance %s not possible - current state: %s', instance_id, state)

        # Handle stop action        
        elif action == "stop":
            if state == "running":
                ec2_client.stop_instances(InstanceIds=[instance_id])
                logger.info('Stopping instance %s', instance_id)
            else:
                logger.warning('Stop instance %s not possible - current state: %s', instance_id, state)

        # Handle restart action
        elif action == "restart":
            if state == "running":
                ec2_client.reboot_instances(InstanceIds=[instance_id])
                logger.info('Restarting instance %s', instance_id)
            else:
                logger.warning('Restart instance %s not possible - current state: %s', instance_id, state)            

        return utl.response(200, f"{action.capitalize()} command submitted")
    
    except Exception as e:
        logger.error("Error performing %s action on instance %s: %s", action, instance_id, str(e))
        return utl.response(500, {"error": f"Failed to {action} instance: {str(e)}"})
    
def handle_fix_role(instance_id):
    """Helper function to handle IAM role fixes"""
    iam_profile = IamProfile(instance_id)
    resp = iam_profile.manage_iam_profile()
    logger.info("IAM role attachment response: %s", resp)
    
    # Check if the response is a dictionary with error information
    if isinstance(resp, dict) and resp.get("status") == "error":
        if resp.get("code") == "UnauthorizedOperation":
            # Return a specific error for unauthorized operations
            return utl.response(403, {
                "err": "Unauthorized operation", 
                "details": resp.get("message", "You do not have permission to attach IAM roles")
            })
    
    if resp is True:
        return utl.response(200, {"msg": "Successfully attached IAM role to the Minecraft Instance"})
    
    logger.error("Attaching IAM role failed")
    return utl.response(500, {"err": "Attaching IAM role failed"})

def handle_update_server_config(instance_id, arguments):
    """Helper function to handle config updates"""
    if not arguments:
        logger.error("Missing arguments for config update")
        return utl.response(400, {"err": "Missing required arguments"})
    
    response = ec2_utils.set_instance_attributes_to_tags(arguments)

    logger.info("Config update response: %s", response)
        
    if response.get('shutdownMethod') == 'Schedule':
        stop_schedule = response.get('stopScheduleExpression')
        if not stop_schedule:
            logger.error("Missing schedule expression")
            return utl.response(400, {"err": "Missing stop schedule expression"})
        
        try:
            # Delete existing alarm
            ec2_utils.remove_alarm(instance_id)
            # Configure event for scheduled shutdown
            ec2_utils.configure_shutdown_event(instance_id, stop_schedule)
            
            # Configure start schedule if provided
            start_schedule = response.get('startScheduleExpression')
            if start_schedule:
                logger.info("Configuring start schedule: %s", start_schedule)
                ec2_utils.configure_start_event(instance_id, start_schedule)
            else:
                # Remove existing start event if no start schedule is provided
                ec2_utils.remove_start_event(instance_id)
                
        except ValueError as ve:
            logger.error("Invalid schedule expression: %s", str(ve))
            return utl.response(400, {"err": f"Invalid schedule expression: {str(ve)}"})
        except Exception as e:
            logger.error("Error configuring schedule: %s", str(e))
            return utl.response(500, {"err": f"Failed to configure schedule: {str(e)}"})
    else:
        if response.get('alarmEvaluationPeriod') is None or response.get('alarmThreshold') is None or response.get('shutdownMethod') is None:
            logger.error("Missing alarmEvaluationPeriod or alarmThreshold")
            return utl.response(400, {"err": "Missing alarmEvaluationPeriod or alarmThreshold"})
        # Delete existing events
        ec2_utils.remove_shutdown_event(instance_id)
        ec2_utils.remove_start_event(instance_id)
        # Set instance tags and create alarm
        ec2_utils.update_alarm(instance_id, response.get('shutdownMethod'), response.get('alarmThreshold'), response.get('alarmEvaluationPeriod'))
    
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
        logger.error("Error processing request: %s", e)
        return utl.response(401,{"err": str(e) })

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
            'stopScheduleExpression': input_args.get('stopScheduleExpression', ''),
            'startScheduleExpression': input_args.get('startScheduleExpression', ''),
            'alarmType': input_args.get('alarmType', ''),
            'alarmThreshold': input_args.get('alarmThreshold', ''),
            'alarmEvaluationPeriod': input_args.get('alarmEvaluationPeriod', ''),
            'runCommand': input_args.get('runCommand', ''),
            'workDir': input_args.get('workDir', '')
        }
    
    logger.info("Received instanceId: %s", instance_id)

    is_authorized = check_authorization(event, instance_id, user_attributes)

    if not is_authorized:
        resp = {"err": "User not authorized"}
        logger.error("%s is not authorized", user_attributes["email"])
        return utl.response(401, resp)

    # MOVE THIS FUNCTION TO CONFIG SERVER    
    # group_check = check_and_create_group(instance_id,user_attributes["username"])    
    # if not group_check:        
    #     logger.error("Group creation failed")        

    # Calling action_process function to process the action with the mutation name
    field_name = event["info"]["fieldName"]
    logger.info("Received field name: %s", field_name)
    return action_process(field_name,instance_id,input)
    