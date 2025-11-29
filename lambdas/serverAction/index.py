import boto3
import logging
import os
import json
import time
import authHelper
import ec2Helper
import utilHelper
import ddbHelper

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
    
    logger.info(f"Authorization check: user={user_email}, instance={instance_id}, groups={cognito_groups}")
    
    # Use the centralized authorization check from utilHelper
    try:
        is_authorized, auth_reason = utl.check_user_authorization(
            cognito_groups, 
            instance_id, 
            user_email, 
            ec2_utils
        )
        
        if is_authorized:
            if auth_reason == "admin_group":
                logger.info(f"Authorization SUCCESS: Admin user {user_email} authorized for instance {instance_id}")
            elif auth_reason == "instance_group":
                logger.info(f"Authorization SUCCESS: Group member {user_email} authorized for instance {instance_id}")
            elif auth_reason == "instance_owner":
                logger.info(f"Authorization SUCCESS: Owner {user_email} authorized for instance {instance_id}")
        else:
            logger.warning(f"Authorization DENIED: User {user_email} not authorized for instance {instance_id}")
        
        return is_authorized
        
    except Exception as e:
        logger.error(f"Authorization check FAILED with exception: user={user_email}, instance={instance_id}, error={str(e)}", exc_info=True)
        raise

def send_status_to_appsync(action, instance_id, status, message=None, user_email=None):
    """
    Log action status for monitoring and debugging.
    Note: Status updates are not persisted to DynamoDB.
    Future: Could broadcast via subscription for real-time UI updates.
    
    Args:
        action: Action being performed
        instance_id: EC2 instance ID
        status: Status of the action (PROCESSING, COMPLETED, FAILED)
        message: Optional status message
        user_email: Email of user who initiated the action
        
    Returns:
        bool: Always returns True (logging only)
    """
    logger.info(f"Action status: action={action}, instance={instance_id}, status={status}, user={user_email}, message={message}")
    
    return True
            
def validate_queue_message(action, instance_id, arguments=None, user_email=None):
    """
    Validate message before sending to queue
    
    Args:
        action: Action to perform (required)
        instance_id: EC2 instance ID (required)
        arguments: Optional arguments for the action
        user_email: Email of user initiating the action (optional)
        
    Returns:
        tuple: (is_valid, error_message)
    """
    # Validate required fields
    if not action or not isinstance(action, str) or not action.strip():
        return False, "Action is required and must be a non-empty string"
    
    if not instance_id or not isinstance(instance_id, str) or not instance_id.strip():
        return False, "Instance ID is required and must be a non-empty string"
    
    # Validate action is one of the allowed types
    allowed_actions = [
        'start', 'stop', 'restart',
        'startServer', 'stopServer', 'restartServer',
        'putServerConfig', 'putserverconfig',
        'updateServerConfig', 'updateserverconfig'
    ]
    if action.lower() not in [a.lower() for a in allowed_actions]:
        return False, f"Invalid action: {action}. Must be one of {allowed_actions}"
    
    # Validate optional fields if provided
    if arguments is not None and not isinstance(arguments, dict):
        return False, "Arguments must be a dictionary if provided"
    
    if user_email is not None and (not isinstance(user_email, str) or not user_email.strip()):
        return False, "User email must be a non-empty string if provided"
    
    return True, None

def send_to_queue(action, instance_id, arguments=None, user_email=None):
    """
    Send action to SQS queue for async processing and send initial PROCESSING status to AppSync
    
    Args:
        action: Action to perform (start, stop, restart, etc.)
        instance_id: EC2 instance ID
        arguments: Optional arguments for the action
        user_email: Email of user initiating the action
        
    Returns:
        dict: Response with 202 status if successful, 400 for validation errors, 500 if failed
    """
    logger.info(f"Queue operation initiated: action={action}, instance={instance_id}, user={user_email}")
    
    if not server_action_queue_url:
        logger.error(f"Queue operation FAILED: No queue URL configured for action={action}, instance={instance_id}")
        return utl.response(500, {"err": "Queue not configured"})
    
    # Validate message before sending
    is_valid, error_message = validate_queue_message(action, instance_id, arguments, user_email)
    if not is_valid:
        logger.error(f"Queue operation FAILED: Message validation failed for action={action}, instance={instance_id}, error={error_message}")
        return utl.response(400, {"err": error_message})
    
    # Build message with all required fields
    message = {
        'action': action,
        'instanceId': instance_id,
        'timestamp': int(time.time())
    }
    
    # Include optional fields only if provided
    if arguments is not None:
        message['arguments'] = arguments
    
    if user_email is not None:
        message['userEmail'] = user_email
    
    logger.info(f"Queue operation: Sending message to SQS - action={action}, instance={instance_id}, queue={server_action_queue_url}")
    
    try:
        # Send message to SQS queue
        response = sqs_client.send_message(
            QueueUrl=server_action_queue_url,
            MessageBody=json.dumps(message)
        )
        message_id = response.get('MessageId', 'unknown')
        logger.info(f"Queue operation SUCCESS: Message sent to SQS - action={action}, instance={instance_id}, messageId={message_id}")
        
        # Send initial PROCESSING status to AppSync
        logger.info(f"Sending initial PROCESSING status to AppSync: action={action}, instance={instance_id}")
        status_sent = send_status_to_appsync(
            action=action,
            instance_id=instance_id,
            status="PROCESSING",
            message=f"{action.capitalize()} request queued for processing",
            user_email=user_email
        )
        
        if status_sent:
            logger.info(f"Initial status update SUCCESS: action={action}, instance={instance_id}")
        else:
            logger.warning(f"Initial status update FAILED: action={action}, instance={instance_id}")
        
        return utl.response(202, {"msg": f"{action.capitalize()} request queued for processing"})
    except Exception as e:
        logger.error(f"Queue operation FAILED with exception: action={action}, instance={instance_id}, error={str(e)}", exc_info=True)
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

def handle_add_user_to_server(instance_id, user_email):
    """
    Helper function to add a user to a server's Cognito group
    
    Args:
        instance_id: EC2 instance ID (used as Cognito group name)
        user_email: Email address of the user to add
        
    Returns:
        dict: Success response or error response with appropriate status code
    """
    try:
        logger.info(f"Adding user to server: email={user_email}, instance={instance_id}")
        
        # Step 1: Find user by email in Cognito
        user_info = auth.find_user_by_email(user_email)
        
        if user_info is None:
            logger.warning(f"User not found in Cognito: email={user_email}")
            return utl.response(404, {
                "error": "USER_NOT_FOUND",
                "message": f"No user found with email {user_email}. The user must log in to the dashboard at least once before they can be added to a server."
            })
        
        username = user_info['username']
        logger.info(f"User found in Cognito: email={user_email}, username={username}")
        
        # Step 2: Check if group exists, create if it doesn't
        if not auth.group_exists(instance_id):
            logger.info(f"Group does not exist, creating: group={instance_id}")
            if not auth.create_group(instance_id):
                logger.error(f"Failed to create group: group={instance_id}")
                return utl.response(500, {
                    "error": "GROUP_CREATION_FAILED",
                    "message": "Failed to create server access group"
                })
        
        # Step 3: Check if user is already in the group
        user_groups = auth.list_groups_for_user(username)
        if instance_id in user_groups:
            logger.info(f"User already has access: email={user_email}, instance={instance_id}")
            return utl.response(409, {
                "error": "USER_ALREADY_EXISTS",
                "message": f"User {user_email} already has access to this server"
            })
        
        # Step 4: Add user to group
        if auth.add_user_to_group(instance_id, username):
            logger.info(f"Successfully added user to server: email={user_email}, instance={instance_id}")
            return utl.response(200, {
                "message": f"Successfully added {user_email} to the server",
                "user": {
                    "email": user_info['email'],
                    "fullName": user_info['fullName']
                }
            })
        else:
            logger.error(f"Failed to add user to group: email={user_email}, instance={instance_id}")
            return utl.response(500, {
                "error": "ADD_USER_FAILED",
                "message": "Failed to add user to server group"
            })
    
    except Exception as e:
        logger.error(f"Error adding user to server: email={user_email}, instance={instance_id}, error={str(e)}", exc_info=True)
        return utl.response(500, {
            "error": "INTERNAL_ERROR",
            "message": f"An unexpected error occurred: {str(e)}"
        })    

def handle_get_server_config(instance_id):
    """Helper function to handle get server config action"""
    try:
        dyn = ddbHelper.Dyn()
        
        server_config = dyn.get_server_config(instance_id)
        if server_config is None:
            logger.warning(f"No config found for instance {instance_id}, returning empty config")
            # Return empty config structure matching GraphQL schema
            return {
                'id': instance_id,
                'shutdownMethod': '',
                'stopScheduleExpression': '',
                'startScheduleExpression': '',
                'alarmThreshold': 0.0,
                'alarmEvaluationPeriod': 0,
                'runCommand': '',
                'workDir': '',
                'timezone': 'UTC',
                'isBootstrapComplete': False,
                'hasCognitoGroup': False,
                'minecraftVersion': '',
                'latestPatchUpdate': '',
                'runningMinutesCache': None,
                'runningMinutesCacheTimestamp': ''
            }
        return server_config
    except Exception as e:
        logger.error(f"Error getting server config for {instance_id}: {str(e)}", exc_info=True)
        return utl.response(500, {"error": f"Failed to get server config: {str(e)}"})

def handle_local_invocation(event, context):
    # Handle local invocations here
    return action_process_sync(event["action"], event["instanceId"])

def handler(event, context):
    """
    Main handler for ServerAction Lambda
    Validates authorization and routes requests to appropriate handlers
    
    Args:
        event: Lambda event from AppSync
        context: Lambda context
        
    Returns:
        dict: Response with appropriate status code and body
    """
    try:
        # Check for authorization header
        if 'request' in event:
            if 'headers' in event['request']:
                if 'authorization' in event['request']['headers']:
                    # Get JWT token from header
                    token = event['request']['headers']['authorization']
                else:
                    logger.error("No Authorization header found")
                    return utl.response(401, {"err": "No Authorization header found"})
            else:
                logger.error("No headers found in request")
                return utl.response(401, {"err": "No headers found in request"})
        else:
            # Local invocation
            return handle_local_invocation(event, context)

    except Exception as e:
        logger.error("Error processing request headers: %s", e)
        return utl.response(401, {"err": str(e)})

    # Get user info from JWT token
    try:
        user_attributes = auth.process_token(token)
    except Exception as e:
        logger.error(f"Token processing FAILED: error={str(e)}", exc_info=True)
        return utl.response(401, {"err": "Invalid token"})

    # Check if claims are valid
    if user_attributes is None:
        logger.error("Invalid Token")
        return utl.response(401, {"err": "Invalid token"})

    # Validate arguments exist
    if not event.get("arguments"):
        logger.error("No arguments found in the event")
        return utl.response(400, {"err": "No arguments found in the event"})

    # Extract instance_id from arguments
    instance_id = (event["arguments"].get("instanceId") or 
                 event["arguments"].get("id") or
                 event["arguments"].get("input", {}).get("id"))

    if not instance_id:
        logger.error("Instance id is not present in the event") 
        return utl.response(400, {"err": "Instance id is not present in the event"})

    # Extract input arguments if present
    input_data = None
    if input_args := event["arguments"].get("input"):
        # Pass through all input fields, ensuring id is set
        input_data = {**input_args, 'id': instance_id}
    
    logger.info("Received instanceId: %s", instance_id)

    # Check authorization
    try:
        is_authorized = check_authorization(event, instance_id, user_attributes)
    except Exception as e:
        logger.error(f"Authorization check FAILED with exception: user={user_attributes.get('email', 'unknown')}, instance={instance_id}, error={str(e)}", exc_info=True)
        return utl.response(500, {"err": "Authorization check failed"})

    if not is_authorized:
        logger.error("%s is not authorized for instance %s", user_attributes["email"], instance_id)
        return utl.response(401, {"err": "User not authorized"})

    # Field name determines the action to perform
    field_name = event["info"]["fieldName"]
    logger.info("Received field name: %s for user %s", field_name, user_attributes["email"])
    
    # Read-only operations processed immediately
    if field_name.lower() in ["getserverconfig", "getserverusers"]:
        return action_process_sync(field_name, instance_id, input_data)
    
    # Handle addUserToServer synchronously
    if field_name.lower() == "addusertoserver":
        user_email = event["arguments"].get("userEmail")
        if not user_email:
            logger.error("userEmail is required for addUserToServer")
            return utl.response(400, {"err": "userEmail is required"})
        return handle_add_user_to_server(instance_id, user_email)
    
    # Config mutations need to return the config data after queuing
    if field_name.lower() in ["putserverconfig", "updateserverconfig"]:
        # Queue the action for async processing
        queue_response = send_to_queue(field_name, instance_id, input_data, user_attributes["email"])
        
        # If queuing succeeded, return the input data as the response
        # (the actual processing happens async, but we return the expected config immediately)
        if queue_response.get('statusCode') == 202:
            logger.info(f"Config queued successfully, returning config data: instance={instance_id}")
            return input_data
        else:
            # If queuing failed, return the error
            logger.error(f"Config queuing failed: instance={instance_id}, response={queue_response}")
            return queue_response
    
    # Queue all other write operations (start/stop/restart)
    return send_to_queue(field_name, instance_id, input_data, user_attributes["email"])