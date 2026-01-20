import boto3
import logging
import os
import json
import time
import re
import authHelper
import ec2Helper
import utilHelper
import ddbHelper
# from errorHandler import ErrorHandler

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
core_dyn = ddbHelper.CoreTableDyn()


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
            
def _is_valid_cron(cron_expression):
    """
    Basic validation for cron expressions (5-field format)
    
    Args:
        cron_expression: String containing cron expression
        
    Returns:
        bool: True if valid format, False otherwise
    """
    if not cron_expression or not isinstance(cron_expression, str):
        return False
    
    parts = cron_expression.strip().split()
    if len(parts) != 5:
        return False
    
    # Basic pattern check - allows numbers, ranges, wildcards, lists
    cron_pattern = r'^[0-9*,/-]+$'
    return all(re.match(cron_pattern, part) for part in parts)

def validate_create_server_input(input_data):
    """
    Validate server creation parameters
    
    Args:
        input_data: Dictionary containing server creation parameters
        
    Returns:
        tuple: (is_valid, error_message)
    """
    # Server name validation
    server_name = input_data.get('serverName', '').strip()
    if not server_name or len(server_name) < 3 or len(server_name) > 50:
        return False, "Server name must be 3-50 characters"
    
    if not re.match(r'^[a-zA-Z0-9_-]+$', server_name):
        return False, "Server name can only contain alphanumeric characters, hyphens, and underscores"
    
    # Instance type validation
    instance_type = input_data.get('instanceType')
    allowed_types = ['t3.micro', 't3.small', 't3.medium', 't3.large', 't3.xlarge', 't3.2xlarge']
    if instance_type not in allowed_types:
        return False, f"Instance type must be one of {allowed_types}"
    
    # Shutdown method validation
    shutdown_method = input_data.get('shutdownMethod')
    if shutdown_method not in ['CPUUtilization', 'Connections', 'Schedule']:
        return False, "Invalid shutdown method"
    
    # Threshold validation for CPU and Connection based shutdown
    if shutdown_method in ['CPUUtilization', 'Connections']:
        threshold = input_data.get('alarmThreshold')
        if threshold is None or threshold < 0 or threshold > 100:
            return False, "Threshold must be between 0 and 100"
        
        eval_period = input_data.get('alarmEvaluationPeriod')
        if eval_period is None or eval_period < 1 or eval_period > 60:
            return False, "Evaluation period must be between 1 and 60 minutes"
    
    # Schedule validation
    if shutdown_method == 'Schedule':
        start_schedule = input_data.get('startScheduleExpression', '').strip()
        stop_schedule = input_data.get('stopScheduleExpression', '').strip()
        
        if not start_schedule or not stop_schedule:
            return False, "Both start and stop schedules required for scheduled shutdown"
        
        # Validate cron format (basic check)
        if not utl.is_valid_cron(start_schedule) or not utl.is_valid_cron(stop_schedule):
            return False, "Invalid cron expression format"
    
    return True, None

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
        'updateServerConfig', 'updateserverconfig',
        'updateServerName', 'updateservername',
        'createServer', 'createserver'
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
    """
    Helper function to handle get server users action using DynamoDB membership.
    Retrieves all users with access to a server, including their roles and full names from Cognito.
    
    Args:
        instance_id (str): EC2 instance ID
        
    Returns:
        list: List of ServerUsers objects with id, email, fullName, and role
        dict: Error response if operation fails
    """
    try:
        
        # Get all members for this server from DynamoDB
        members = core_dyn.list_server_members(instance_id)
        
        # Handle empty membership lists gracefully
        if not members:
            logger.info(f"No users found for server {instance_id}")
            return []
        
        # Convert to the expected ServerUsers format
        server_users = []
        for member in members:
            try:
                # Get user details from Cognito to get fullName
                user_info = auth.get_user_by_sub(member['userId'])
                full_name = user_info.get('fullName', member['email']) if user_info else member['email']
                
                server_users.append({
                    'id': member['userId'],
                    'email': member['email'],
                    'fullName': full_name,
                    'role': member['role']
                })
                
            except Exception as user_error:
                # If we can't get user details from Cognito, use email as fallback
                logger.warning(f"Could not get user details from Cognito for {member['userId']}: {str(user_error)}")
                server_users.append({
                    'id': member['userId'],
                    'email': member['email'],
                    'fullName': member['email'],  # Use email as fallback
                    'role': member['role']
                })
        
        logger.info(f"Retrieved {len(server_users)} users for server {instance_id} from DynamoDB")
        return server_users
    
    except Exception as e:
        logger.error("Error retrieving users for instance %s: %s", instance_id, str(e))
        return utl.response(500, {"error": f"Failed to retrieve users: {str(e)}"})

def handle_get_admin_users():
    """Helper function to get admin group members"""
    try:
        admin_group = os.getenv('ADMIN_GROUP_NAME', 'admin')
        users = auth.list_users_for_group(admin_group)
        return users
    except Exception as e:
        logger.error("Error retrieving admin users: %s", str(e))
        return []

def handle_search_user_by_email(email):
    """
    Helper function to search for a user by email address
    
    Args:
        email: Email address to search for
        
    Returns:
        dict: User information if found, None if not found, error response for exceptions
    """
    try:
        logger.info(f"Searching for user by email: {email}")
        
        # Use the existing find_user_by_email method from authHelper
        user_info = auth.find_user_by_email(email)
        
        if user_info is None:
            logger.info(f"No user found with email: {email}")
            # Return None for GraphQL nullable field instead of error response
            return None
        
        # Return user info in the expected ServerUsers format
        return {
            'id': user_info['sub'],
            'email': user_info['email'],
            'fullName': user_info['fullName']
        }
        
    except Exception as e:
        logger.error(f"Error searching for user by email {email}: {str(e)}", exc_info=True)
        return utl.response(500, {
            "error": "SEARCH_ERROR",
            "message": f"An error occurred while searching for user: {str(e)}"
        })

def handle_create_server(input_data, user_attributes):
    """
    Handle server creation request
    
    Args:
        input_data: Dictionary containing server creation parameters
        user_attributes: User information from JWT token
        
    Returns:
        dict: Response with appropriate status code and body
    """
    try:
        logger.info(f"Server creation request: user={user_attributes.get('email', 'unknown')}, data={input_data}")
        
        # Check if user is admin
        cognito_groups = user_attributes.get('cognito:groups', [])
        admin_group_name = os.getenv('ADMIN_GROUP_NAME', 'admin')
        
        if admin_group_name not in cognito_groups:
            logger.warning(f"Non-admin user attempted server creation: user={user_attributes.get('email', 'unknown')}, groups={cognito_groups}")
            return utl.response(403, {"err": "Only admin users can create servers"})
        
        logger.info(f"Admin authorization confirmed: user={user_attributes.get('email', 'unknown')}")
        
        # Validate input parameters
        is_valid, error_message = validate_create_server_input(input_data)
        if not is_valid:
            logger.error(f"Server creation validation failed: user={user_attributes.get('email', 'unknown')}, error={error_message}")
            return utl.response(400, {"err": error_message})
        
        logger.info(f"Server creation validation passed: user={user_attributes.get('email', 'unknown')}")
        
        # Prepare SQS message with all required parameters
        message_data = {
            'action': 'createServer',
            'serverName': input_data['serverName'],
            'instanceType': input_data['instanceType'],
            'shutdownMethod': input_data['shutdownMethod'],
            'userEmail': user_attributes.get('email'),
            'timestamp': int(time.time())
        }
        
        # Add optional parameters if provided
        if 'alarmThreshold' in input_data:
            message_data['alarmThreshold'] = input_data['alarmThreshold']
        
        if 'alarmEvaluationPeriod' in input_data:
            message_data['alarmEvaluationPeriod'] = input_data['alarmEvaluationPeriod']
        
        if 'startScheduleExpression' in input_data:
            message_data['startScheduleExpression'] = input_data['startScheduleExpression']
        
        if 'stopScheduleExpression' in input_data:
            message_data['stopScheduleExpression'] = input_data['stopScheduleExpression']
        
        logger.info(f"Queuing server creation: user={user_attributes.get('email', 'unknown')}, server={input_data['serverName']}")
        
        # Send to SQS queue
        if not server_action_queue_url:
            logger.error("Server creation FAILED: No queue URL configured")
            return utl.response(500, {"err": "Queue not configured"})
        
        try:
            response = sqs_client.send_message(
                QueueUrl=server_action_queue_url,
                MessageBody=json.dumps(message_data)
            )
            message_id = response.get('MessageId', 'unknown')
            logger.info(f"Server creation queued successfully: messageId={message_id}, server={input_data['serverName']}")
            
            # Send initial PROCESSING status
            send_status_to_appsync(
                action='createServer',
                instance_id='pending',  # No instance ID yet
                status='PROCESSING',
                message="Server creation request queued for processing",
                user_email=user_attributes.get('email')
            )
            
            return utl.response(202, {"msg": "Server creation request queued for processing"})
            
        except Exception as e:
            logger.error(f"Server creation queue FAILED: user={user_attributes.get('email', 'unknown')}, error={str(e)}", exc_info=True)
            return utl.response(500, {"err": "Failed to queue server creation request"})
    
    except Exception as e:
        logger.error(f"Server creation FAILED with exception: user={user_attributes.get('email', 'unknown')}, error={str(e)}", exc_info=True)
        return utl.response(500, {"err": "Server creation request failed"})

def handle_add_user_to_server(instance_id, user_email, user_attributes):
    """
    Helper function to add a user to a server using DynamoDB membership with default viewer role
    
    Args:
        instance_id: EC2 instance ID
        user_email: Email address of the user to add
        user_attributes: Attributes of the user making the request (for created_by field)
        
    Returns:
        dict: Success response or error response with appropriate status code
    """
    try:
        logger.info(f"Adding user to server: email={user_email}, instance={instance_id}")
        
        # Step 1: Find user by email in Cognito to get their sub
        user_info = auth.find_user_by_email(user_email)
        
        if user_info is None:
            # ErrorHandler.log_error('USER_NOT_FOUND',
            #                      context={'operation': 'add_user_to_server', 'user_email': user_email, 'instance_id': instance_id},
            #                      email=user_email)
            # return ErrorHandler.create_error_response(404, 'USER_NOT_FOUND', email=user_email)
            logger.error('USER_NOT_FOUND')
            return None
        
        user_sub = user_info['sub']
        logger.info(f"User found in Cognito: email={user_email}, sub={user_sub}")
        
        # Step 2: Create DynamoDB membership record with default viewer role
        try:            
            # Create membership with default viewer role
            core_dyn.create_user_server_membership(
                user_id=user_sub,
                server_id=instance_id,
                role='viewer',  # Default role as per requirements
                permissions=['read']
            )
            
            logger.info(f"Successfully added user to server: email={user_email}, instance={instance_id}, role=viewer")
            return utl.response(200, {
                "message": f"Successfully added {user_email} to the server with viewer role",
                "user": {
                    "id": user_sub,
                    "email": user_info['email'],
                    "fullName": user_info['fullName'],
                    "role": "viewer"
                }
            })
            
        except ValueError as e:
            # Handle membership already exists error
            if "already exists" in str(e):
                # ErrorHandler.log_error('MEMBERSHIP_ALREADY_EXISTS',
                #                      context={'operation': 'add_user_to_server', 'user_email': user_email, 'instance_id': instance_id})
                # return ErrorHandler.create_error_response(409, 'MEMBERSHIP_ALREADY_EXISTS')
                logger.error('MEMBERSHIP_ALREADY_EXISTS')
                return None
            else:
                # ErrorHandler.log_error('VALIDATION_ERROR',
                #                      context={'operation': 'add_user_to_server', 'user_email': user_email, 'instance_id': instance_id},
                #                      exception=e, error=str(e))
                # return ErrorHandler.create_error_response(400, 'VALIDATION_ERROR', error=str(e))
                logger.error('VALIDATION_ERROR')
                return None
        
    except Exception as e:
        # ErrorHandler.log_error('INTERNAL_ERROR',
        #                      context={'operation': 'add_user_to_server', 'user_email': user_email, 'instance_id': instance_id},
        #                      exception=e, error=str(e))
        # return ErrorHandler.create_error_response(500, 'INTERNAL_ERROR', error=str(e))    
        logger.error('INTERNAL_ERROR')
        return None

def handle_update_user_role(instance_id, user_id, new_role, requesting_user_attributes):
    """
    Helper function to update a user's role for a server
    
    Args:
        instance_id: EC2 instance ID
        user_id: Cognito user sub of the user whose role to update
        new_role: New role to assign (admin, moderator, viewer)
        requesting_user_attributes: Attributes of the user making the request
        
    Returns:
        dict: Success response with updated membership or error response
    """
    try:
        requesting_user_email = requesting_user_attributes.get('email', 'unknown')
        requesting_user_sub = requesting_user_attributes.get('sub')
        
        logger.info(f"Updating user role: user={user_id}, instance={instance_id}, new_role={new_role}, requester={requesting_user_email}")
                
        # Step 1: Check if requesting user has admin permissions
        requesting_user_access = core_dyn.check_user_server_access(requesting_user_sub, instance_id)
        is_global_admin = core_dyn.check_global_admin(requesting_user_sub)
        
        if not (requesting_user_access and requesting_user_access['role'] == 'admin') and not is_global_admin:
            logger.warning(f"Unauthorized role update attempt: requester={requesting_user_email}")
            # return ErrorHandler.create_error_response(403, 'INSUFFICIENT_PERMISSIONS', 
            #                                         error="Insufficient permissions. Admin role required.")
            return None
        
        # Step 2: Prevent users from modifying their own admin role (lockout protection)
        if user_id == requesting_user_sub and requesting_user_access and requesting_user_access['role'] == 'admin' and new_role != 'admin':
            logger.warning(f"Self-admin-role modification blocked: user={requesting_user_email}")
            # return ErrorHandler.create_error_response(403, 'SELF_ADMIN_ROLE_PROTECTION', 
            #                                         error="Cannot modify your own admin role to prevent lockout")
            return None
        
        # Step 3: Update the user's role
        try:
            # Get current membership to preserve email
            current_membership = core_dyn.check_user_server_access(user_id, instance_id)
            # if not current_membership:
            #     return ErrorHandler.create_error_response(404, 'MEMBERSHIP_NOT_FOUND', 
            #                                             error="User membership not found")
            return None
            
            # Create new membership with updated role
            permissions_map = {'admin': ['read', 'write', 'delete', 'manage_users'], 'moderator': ['read', 'write', 'restart'], 'viewer': ['read']}
            updated_membership = core_dyn.create_user_server_membership(
                user_id=user_id,
                server_id=instance_id,
                role=new_role,
                permissions=permissions_map.get(new_role, ['read'])
            )
            
            logger.info(f"Successfully updated user role: user={user_id}, instance={instance_id}, new_role={new_role}")
            
            # Return UserMembership object directly for GraphQL
            return {
                "userId": user_id,
                "serverId": instance_id,
                "email": current_membership.get('email', ''),
                "role": new_role,
                "createdAt": updated_membership['createdAt'],
                "updatedAt": updated_membership['updatedAt'],
                "createdBy": updated_membership['createdBy']
            }
            
        except ValueError as e:
            if "not found" in str(e):
                logger.error(f"User membership not found for role update: user={user_id}, instance={instance_id}")
                # return ErrorHandler.create_error_response(404, 'USER_MEMBERSHIP_NOT_FOUND', 
                #                                         error=f"User membership not found for server {instance_id}")
                return None
            else:
                logger.error(f"Validation error updating role: {str(e)}")
                # return ErrorHandler.create_error_response(400, 'VALIDATION_ERROR', error=str(e))
                return None
        
    except Exception as e:
        logger.error(f"Error updating user role: user={user_id}, instance={instance_id}, error={str(e)}", exc_info=True)
        # return ErrorHandler.create_error_response(500, 'INTERNAL_ERROR', error=f"An unexpected error occurred: {str(e)}")

def handle_remove_user_from_server(instance_id, user_id, requesting_user_attributes):
    """
    Helper function to remove a user from a server
    
    Args:
        instance_id: EC2 instance ID
        user_id: Cognito user sub of the user to remove
        requesting_user_attributes: Attributes of the user making the request
        
    Returns:
        dict: Success response or error response
    """
    try:
        requesting_user_email = requesting_user_attributes.get('email', 'unknown')
        requesting_user_sub = requesting_user_attributes.get('sub')
        
        logger.info(f"Removing user from server: user={user_id}, instance={instance_id}, requester={requesting_user_email}")
        
        # Step 1: Check if requesting user has admin permissions
        requesting_user_access = core_dyn.check_user_server_access(requesting_user_sub, instance_id)
        is_global_admin = core_dyn.check_global_admin(requesting_user_sub)
        
        if not (requesting_user_access and requesting_user_access['role'] == 'admin') and not is_global_admin:
            logger.warning(f"Unauthorized user removal attempt: requester={requesting_user_email}")
            # return ErrorHandler.create_error_response(403, 'INSUFFICIENT_PERMISSIONS', 
            #                                         error="Insufficient permissions. Admin role required.")
            return None
        
        # Step 2: Prevent users from removing themselves if they're the only admin (lockout protection)
        if user_id == requesting_user_sub and requesting_user_access and requesting_user_access['role'] == 'admin':
            # Check if there are other admins
            all_members = core_dyn.list_server_members(instance_id)
            admin_members = [m for m in all_members if m.get('role') == 'admin']
            if len(admin_members) <= 1:
                logger.warning(f"Self-removal blocked - only admin: user={requesting_user_email}")
                # return ErrorHandler.create_error_response(403, 'LAST_ADMIN_PROTECTION', 
                #                                         error="Cannot remove yourself as you are the only admin for this server")
                return None
        
        # Step 3: Remove the user's membership
        try:
            deleted_membership = core_dyn.delete_membership(user_id, instance_id)
            
            logger.info(f"Successfully removed user from server: user={user_id}, instance={instance_id}")
            
            # Return JSON response as expected by GraphQL AWSJSON type
            return {
                "message": "Successfully removed user from server",
                "removedUser": {
                    "userId": deleted_membership['userId'],
                    "email": deleted_membership['email'],
                    "role": deleted_membership['role']
                }
            }
            
        except ValueError as e:
            if "not found" in str(e):
                logger.error(f"User membership not found for removal: user={user_id}, instance={instance_id}")
                # return ErrorHandler.create_error_response(404, 'USER_MEMBERSHIP_NOT_FOUND', 
                #                                         error=f"User membership not found for server {instance_id}")
                return None
            else:
                # logger.error(f"Validation error removing user: {str(e)}")
                # return ErrorHandler.create_error_response(400, 'VALIDATION_ERROR', error=str(e))
                return None
        
    except Exception as e:
        logger.error(f"Error removing user from server: user={user_id}, instance={instance_id}, error={str(e)}", exc_info=True)
        return None
        #return ErrorHandler.create_error_response(500, 'INTERNAL_ERROR', error=f"An unexpected error occurred: {str(e)}")

def handle_get_server_config_old(instance_id):
    """Helper function to handle get server config action"""
    try:

        server_config = core_dyn.get_server_config(instance_id)
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

def handle_get_server_config(instance_id):
    """Helper function to handle get server config action"""
    try:
        
        server_config = core_dyn.get_server_config(instance_id)
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

def handle_search_user_by_email_operation(event):
    """Handle searchUserByEmail operation."""
    email = event["arguments"].get("email")
    if not email:
        return utl.response(400, {"err": "email is required"})
    return handle_search_user_by_email(email)

def handle_create_server_operation(event, user_attributes):
    """Handle createServer operation."""
    input_data = event["arguments"].get("input")
    if not input_data:
        return utl.response(400, {"err": "input is required for createServer"})
    return handle_create_server(input_data, user_attributes)

def route_instance_operation(event, instance_id, user_attributes):
    """Route operations that require instance authorization with role-based permissions."""
    field_name = event["info"]["fieldName"].lower()
    
    # Prepare input data
    input_data = None
    if input_args := event["arguments"].get("input"):
        input_data = {**input_args, 'id': instance_id}
    
    # Determine minimum permission based on server operation
    required_permission = 'manage_server'  # Default for server operations (stop/start, config and user mngmt)
        
    # Check authorization with role-based permissions
    try:
        is_authorized, user_role, auth_reason = core_dyn.check_user_authorization(user_attributes['sub'], instance_id, required_permission)
        if not is_authorized:
            logger.error(f"User {user_attributes['email']} not authorized for {field_name} on instance {instance_id}: {auth_reason}")
            return utl.response(403, {"err": f"Insufficient permissions. {auth_reason}"})
        
        logger.info(f"Authorization granted: user={user_attributes['email']}, role={user_role}, operation={field_name}")
        
    except Exception as e:
        logger.error(f"Authorization check FAILED: user={user_attributes.get('email', 'unknown')}, instance={instance_id}, error={str(e)}", exc_info=True)
        return utl.response(500, {"err": "Authorization check failed"})
    
    # Read-only operations
    if field_name in ["getserverconfig", "getserverusers"]:
        return action_process_sync(field_name, instance_id, input_data)
    
    # Add user operation - create DynamoDB membership with default viewer role
    if field_name == "addusertoserver":
        user_email = event["arguments"].get("userEmail")
        if not user_email:
            return utl.response(400, {"err": "userEmail is required"})
        return handle_add_user_to_server(instance_id, user_email, user_attributes)
    
    # Update user role operation - new DynamoDB-based role management
    if field_name == "updateuserrole":
        user_id = event["arguments"].get("userId")
        new_role = event["arguments"].get("role")
        if not user_id or not new_role:
            return utl.response(400, {"err": "userId and role are required"})
        return handle_update_user_role(instance_id, user_id, new_role, user_attributes)
    
    # Remove user from server operation - new DynamoDB-based user removal
    if field_name == "removeuserfromserver":
        user_id = event["arguments"].get("userId")
        if not user_id:
            return utl.response(400, {"err": "userId is required"})
        return handle_remove_user_from_server(instance_id, user_id, user_attributes)
    
    # Update server name
    if field_name == "updateservername":
        new_name = event["arguments"].get("newName")
        if not new_name:
            return utl.response(400, {"err": "newName is required"})
        
        new_name = new_name.strip()
        if not new_name:
            return utl.response(400, {"err": "Server name cannot be empty"})
        if len(new_name) > 255:
            return utl.response(400, {"err": "Server name cannot exceed 255 characters"})
        
        return send_to_queue("updateServerName", instance_id, {"newName": new_name}, user_attributes["email"])
    
    # Config operations
    if field_name in ["putserverconfig", "updateserverconfig"]:
        queue_response = send_to_queue(field_name, instance_id, input_data, user_attributes["email"])
        
        if queue_response.get('statusCode') == 202:
            logger.info(f"Config queued successfully, returning config data: instance={instance_id}")
            return input_data
        else:
            logger.error(f"Config queuing failed: instance={instance_id}, response={queue_response}")
            return queue_response
    
    # All other write operations
    return send_to_queue(field_name, instance_id, input_data, user_attributes["email"])

def handler(event, context):
    """
    Main handler for ec2ActionValidator Lambda
    Validates authorization and routes requests to appropriate handlers
    """
    try:
        # Handle local invocation or extract token
        try:
            token = utl.extract_auth_token(event)
        except ValueError as e:
            if str(e) == "Local invocation detected":
                return handle_local_invocation(event, context)
            logger.error(str(e))
            return utl.response(401, {"err": str(e)})
        
        # Validate token and get user
        try:
            user_attributes = auth.process_token(token)
        except ValueError as e:
            return utl.response(401, {"err": str(e)})
        
        # Validate arguments exist
        if not event.get("arguments"):
            logger.error("No arguments found in the event")
            return utl.response(400, {"err": "No arguments found in the event"})

        logger.info(event)
        
        # Handle special operations (no instance ID required)
        field_name = event["info"]["fieldName"].lower()
        
        if field_name == "searchuserbyemail":
            return handle_search_user_by_email_operation(event)
        
        if field_name == "getadminusers":
            return handle_get_admin_users()
        
        if field_name == "createserver":
            return handle_create_server_operation(event, user_attributes)
        
        # Extract instance ID for regular operations
        instance_id = ec2Helper.extract_instance_id(event)
        if not instance_id:
            logger.error("Instance id is not present in the event")
            return utl.response(400, {"err": "Instance id is not present in the event"})
        
        logger.info("Received instanceId: %s", instance_id)
        logger.info("Received field name: %s for user %s", event["info"]["fieldName"], user_attributes["email"])
        
        # Route instance operations        
        return route_instance_operation(event, instance_id, user_attributes)
        
    except Exception as e:
        logger.error("Unexpected error in handler: %s", e, exc_info=True)
        return utl.response(500, {"err": "Internal server error"})