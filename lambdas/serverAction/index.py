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
sqs_client = boto3.client('sqs')

appValue = os.getenv('TAG_APP_VALUE')
ec2_instance_profile_name = os.getenv('EC2_INSTANCE_PROFILE_NAME')
ec2_instance_profile_arn = os.getenv('EC2_INSTANCE_PROFILE_ARN')
cognito_pool_id = os.getenv('COGNITO_USER_POOL_ID')
server_action_queue_url = os.getenv('SERVER_ACTION_QUEUE_URL')

auth = authHelper.Auth(cognito_pool_id)
ec2_utils = ec2Helper.Ec2Utils()
utl = utilHelper.Utils()

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

def send_to_queue(action, instance_id, arguments=None, user_email=None):
    """Send action to SQS queue for async processing"""
    if not server_action_queue_url:
        logger.warning("No queue URL configured, processing synchronously")
        return action_process_sync(action, instance_id, arguments)
    
    message = {
        'action': action,
        'instanceId': instance_id,
        'arguments': arguments,
        'userEmail': user_email,
        'timestamp': int(time.time())
    }
    
    try:
        sqs_client.send_message(
            QueueUrl=server_action_queue_url,
            MessageBody=json.dumps(message)
        )
        logger.info(f"Queued action {action} for instance {instance_id}")
        return utl.response(202, {"msg": f"{action.capitalize()} request queued for processing"})
    except Exception as e:
        logger.error(f"Failed to queue action: {e}")
        return utl.response(500, {"err": "Failed to queue action"})

def action_process_sync(action, instance_id, arguments=None):
    """Synchronous processing for read-only operations"""
    logger.info("Action: %s InstanceId: %s", action, instance_id)
    action = action.lower().strip()

    # Only handle read-only operations synchronously
    if action == "getserverconfig":
        return handle_get_server_config(instance_id)
    elif action == "getserverusers":
        return handle_get_server_users(instance_id)
    else:
        # All other actions should be queued
        return send_to_queue(action, instance_id, arguments)

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
    return instance_tags

def handle_local_invocation(event, context):
    # Handle local invocations here
    return action_process_sync(event["action"], event["instanceId"])

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

    # Field name determines the action to perform
    field_name = event["info"]["fieldName"]
    logger.info("Received field name: %s", field_name)
    
    # Read-only operations processed immediately
    if field_name.lower() in ["getserverconfig", "getserverusers"]:
        return action_process_sync(field_name, instance_id, input)
    
    # Queue all other operations
    return send_to_queue(field_name, instance_id, input, user_attributes["email"])