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

def send_status_to_appsync(action, instance_id, status, message=None, user_email=None):
    """
    Send action status update to AppSync for real-time subscriptions
    
    Args:
        action: Action being performed
        instance_id: EC2 instance ID
        status: Status of the action (PROCESSING, COMPLETED, FAILED)
        message: Optional status message
        user_email: Email of user who initiated the action
        
    Returns:
        bool: True if successful, False otherwise
    """
    logger.info(f"AppSync status update: action={action}, instance={instance_id}, status={status}, user={user_email}")
    
    appsync_url = os.getenv('APPSYNC_URL')
    if not appsync_url:
        logger.warning(f"AppSync status update SKIPPED: APPSYNC_URL not configured for action={action}, instance={instance_id}")
        return False
    
    mutation = """
    mutation PutServerActionStatus($input: ServerActionStatusInput!) {
        putServerActionStatus(input: $input) {
            id
            action
            status
            timestamp
            message
            userEmail
        }
    }
    """
    
    variables = {
        "input": {
            "id": instance_id,
            "action": action,
            "status": status,
            "timestamp": int(time.time()),
            "message": message,
            "userEmail": user_email
        }
    }
    
    try:
        # Get AWS credentials for signing the request
        session = boto3.Session()
        credentials = session.get_credentials()
        
        # Prepare the GraphQL request
        headers = {
            'Content-Type': 'application/json'
        }
        
        payload = {
            'query': mutation,
            'variables': variables
        }
        
        # Use requests_aws4auth if available, otherwise use IAM auth
        try:
            from requests_aws4auth import AWS4Auth
            region = os.getenv('AWS_REGION', 'us-east-1')
            auth_header = AWS4Auth(
                credentials.access_key,
                credentials.secret_key,
                region,
                'appsync',
                session_token=credentials.token
            )
            
            import requests
            response = requests.post(
                appsync_url,
                auth=auth_header,
                json=payload,
                headers=headers
            )
            
            if response.status_code == 200:
                logger.info(f"AppSync status update SUCCESS: action={action}, instance={instance_id}, status={status}")
                return True
            else:
                logger.error(f"AppSync status update FAILED: action={action}, instance={instance_id}, status={status}, http_code={response.status_code}, response={response.text}")
                return False
                
        except ImportError as ie:
            # Fallback: log the status update but don't fail
            logger.warning(f"AppSync status update SKIPPED: requests_aws4auth not available - action={action}, instance={instance_id}, error={str(ie)}")
            logger.info(f"Status update (not sent): {action} on {instance_id} - {status}: {message}")
            return False
            
    except Exception as e:
        logger.error(f"AppSync status update FAILED with exception: action={action}, instance={instance_id}, status={status}, error={str(e)}", exc_info=True)
        return False

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
        'fixServerRole', 'fixserverrole',
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

def handle_get_server_config(instance_id):
    """Helper function to handle get server config action"""
    instance_tags = ec2_utils.get_instance_attributes_from_tags(instance_id)
    return instance_tags

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
        input_data = {
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
    
    # Queue all write operations
    return send_to_queue(field_name, instance_id, input_data, user_attributes["email"])