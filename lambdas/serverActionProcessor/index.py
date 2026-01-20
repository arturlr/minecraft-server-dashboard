import boto3
import logging
import json
import os
import time
import ec2Helper
import ddbHelper
import utilHelper
from aws_croniter import AwsCroniter
from datetime import datetime
import pytz
from botocore.session import Session
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.httpsession import URLLib3Session
from botocore.exceptions import ClientError
# from errorHandler import ErrorHandler

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ec2_client = boto3.client('ec2')
eventbridge_client = boto3.client('events')
ec2_utils = ec2Helper.Ec2Utils()
utils = utilHelper.Utils()
dyn = ddbHelper.CoreTableDyn()
boto3_session = boto3.Session()

# Environment variables
appValue = os.getenv('TAG_APP_VALUE')
appName = os.getenv('APP_NAME')
envName = os.getenv('ENVIRONMENT_NAME')
ec2_instance_profile_name = os.getenv('EC2_INSTANCE_PROFILE_NAME')
ec2_instance_profile_arn = os.getenv('EC2_INSTANCE_PROFILE_ARN')
endpoint = os.getenv('APPSYNC_URL', None)

# Get AWS account and region info
sts_client = boto3.client('sts')
account_id = sts_client.get_caller_identity()['Account']
aws_region = boto3_session.region_name

# ============================================================================
# Schedule Event Management Functions
# ============================================================================

def _format_schedule_expression(cron_expression, timezone='UTC'):
    """Format cron expression for EventBridge using aws-croniter."""
    if not cron_expression:
        return None
    
    cron_expression = cron_expression.strip()
    
    # If already in EventBridge format, validate and return
    if cron_expression.startswith('cron(') and cron_expression.endswith(')'):
        cron_content = cron_expression[5:-1]
        try:
            AwsCroniter(cron_content)
            return cron_expression
        except Exception as e:
            logger.error(f"Invalid EventBridge cron expression: {e}")
            return None
    
    # Handle standard 5-field cron expression (minute hour day month day_of_week)
    fields = cron_expression.split()
    if len(fields) == 5:
        minute, hour, day, month, day_of_week = fields
        
        # Convert timezone to UTC if needed
        if timezone and timezone != 'UTC':
            hour, minute = _convert_timezone_to_utc(hour, minute, timezone)
        
        # Convert day-of-week from standard (0=Sun) to EventBridge (1=Sun)
        if day_of_week != '*' and day_of_week != '?':
            dow_parts = []
            for part in day_of_week.split(','):
                part = part.strip()
                if part.isdigit():
                    # Standard cron: 0=Sun, 1=Mon...6=Sat
                    # EventBridge: 1=Sun, 2=Mon...7=Sat
                    dow_parts.append(str(int(part) + 1))
                else:
                    dow_parts.append(part)
            day_of_week = ','.join(dow_parts)
        
        # EventBridge requires '?' for day when day_of_week is specified
        if day_of_week != '*' and day_of_week != '?':
            day = '?'
        
        # Build 6-field EventBridge cron (add year)
        eb_cron = f"{minute} {hour} {day} {month} {day_of_week} *"
        
        # Validate with aws-croniter
        try:
            AwsCroniter(eb_cron)
            return f"cron({eb_cron})"
        except Exception as e:
            logger.error(f"Invalid cron expression after conversion: {e}")
            return None
    
    return None

def _convert_timezone_to_utc(hour, minute, timezone):
    """Convert local time to UTC based on timezone."""
    if not timezone or timezone == 'UTC':
        return hour, minute
    
    try:
        tz = pytz.timezone(timezone)
        # Use current date to properly handle DST
        now = datetime.now()
        local_time = tz.localize(datetime(now.year, now.month, now.day, int(hour), int(minute)))
        utc_time = local_time.astimezone(pytz.UTC)
        return str(utc_time.hour), str(utc_time.minute)
    except Exception as e:
        logger.error(f"Error converting timezone {timezone} to UTC: {e}")
        return hour, minute

def configure_scheduled_shutdown_event(instance_id, cron_expression, timezone='UTC'):
    """Configure EventBridge rule to stop EC2 instance on schedule."""
    logger.info(f"Original shutdown cron expression: {cron_expression}, timezone: {timezone}")
    
    # Validate and format the cron expression for EventBridge (converts to UTC)
    formatted_schedule = _format_schedule_expression(cron_expression, timezone)
    logger.info(f"Formatted schedule expression (UTC): {formatted_schedule}")
    
    if not formatted_schedule:
        logger.error(f"Invalid cron expression: {cron_expression}")
        raise ValueError(f"Invalid cron expression: {cron_expression}")
    
    rule_name = f"shutdown-{instance_id}"
    
    # Remove existing rule if it exists to avoid conflicts
    try:
        rules = eventbridge_client.list_rules(NamePrefix=rule_name)
        if rules.get('Rules'):
            logger.info(f"Removing existing rule {rule_name} before recreating")
            eventbridge_client.remove_targets(
                Rule=rule_name,
                Ids=[f"shutdown-target-{instance_id}"]
            )
            eventbridge_client.delete_rule(Name=rule_name)
    except ClientError as e:
        logger.warning(f"Error removing existing rule: {e}")
    
    # Create the rule with cron expression
    logger.info(f"Creating EventBridge rule {rule_name} with schedule: {formatted_schedule}")
    
    eventbridge_client.put_rule(
        Name=rule_name,
        ScheduleExpression=formatted_schedule,
        State='ENABLED'
    )
    
    # Create the target to invoke ServerAction Lambda
    lambda_function_name = f"{appName}-{envName}-serverAction"
    lambda_arn = f"arn:aws:lambda:{aws_region}:{account_id}:function:{lambda_function_name}"
    
    target = {
        'Id': f"shutdown-target-{instance_id}",
        'Arn': lambda_arn,
        'Input': json.dumps({
            "action": "stopServer",
            "instanceId": instance_id,
            "source": "scheduled-shutdown"
        })
    }
    
    eventbridge_client.put_targets(
        Rule=rule_name,
        Targets=[target]
    )
    logger.info(f"Shutdown event configured for {instance_id} with schedule: {formatted_schedule}")

def remove_scheduled_shutdown_event(instance_id):
    """Remove EventBridge rule for stopping EC2 instance."""
    rule_name = f"shutdown-{instance_id}"
    try:
        # Check if rule exists
        rules = eventbridge_client.list_rules(NamePrefix=rule_name)
        if not rules.get('Rules'):
            logger.info(f"No shutdown event rule found for {instance_id}")
            return
            
        eventbridge_client.remove_targets(
            Rule=rule_name,
            Ids=[f"shutdown-target-{instance_id}"]
        )
        eventbridge_client.delete_rule(Name=rule_name)
        logger.info(f"Shutdown event removed for {instance_id}")

    except ClientError as e:
        logger.error(f"Error removing shutdown event: {e}")

def configure_start_event(instance_id, cron_expression, timezone='UTC'):
    """Configure EventBridge rule to start EC2 instance on schedule."""
    logger.info(f"Original start cron expression: {cron_expression}, timezone: {timezone}")
    
    # Validate and format the cron expression for EventBridge (converts to UTC)
    formatted_schedule = _format_schedule_expression(cron_expression, timezone)
    logger.info(f"Formatted start schedule expression (UTC): {formatted_schedule}")
    
    if not formatted_schedule:
        logger.error(f"Invalid cron expression: {cron_expression}")
        raise ValueError(f"Invalid cron expression: {cron_expression}")
    
    rule_name = f"start-{instance_id}"
    
    # Remove existing rule if it exists to avoid conflicts
    try:
        rules = eventbridge_client.list_rules(NamePrefix=rule_name)
        if rules.get('Rules'):
            logger.info(f"Removing existing rule {rule_name} before recreating")
            eventbridge_client.remove_targets(
                Rule=rule_name,
                Ids=[f"start-target-{instance_id}"]
            )
            eventbridge_client.delete_rule(Name=rule_name)
    except ClientError as e:
        logger.warning(f"Error removing existing rule: {e}")
    
    # Create the rule with cron expression for starting
    logger.info(f"Creating EventBridge start rule {rule_name} with schedule: {formatted_schedule}")
    
    eventbridge_client.put_rule(
        Name=rule_name,
        ScheduleExpression=formatted_schedule,
        State='ENABLED'
    )
    
    # Create the target to invoke ServerAction Lambda
    lambda_function_name = f"{appName}-{envName}-serverAction"
    lambda_arn = f"arn:aws:lambda:{aws_region}:{account_id}:function:{lambda_function_name}"
    
    target = {
        'Id': f"start-target-{instance_id}",
        'Arn': lambda_arn,
        'Input': json.dumps({
            "action": "startServer",
            "instanceId": instance_id,
            "source": "scheduled-start"
        })
    }
    
    eventbridge_client.put_targets(
        Rule=rule_name,
        Targets=[target]
    )
    logger.info(f"Start event configured for {instance_id} with schedule: {formatted_schedule}")

def remove_start_event(instance_id):
    """Remove EventBridge rule for starting EC2 instance."""
    rule_name = f"start-{instance_id}"
    try:
        # Check if rule exists
        rules = eventbridge_client.list_rules(NamePrefix=rule_name)
        if not rules.get('Rules'):
            logger.info(f"No start event rule found for {instance_id}")
            return
            
        eventbridge_client.remove_targets(
            Rule=rule_name,
            Ids=[f"start-target-{instance_id}"]
        )
        eventbridge_client.delete_rule(Name=rule_name)
        logger.info(f"Start event removed for {instance_id}")

    except ClientError as e:
        logger.error(f"Error removing start event: {e}")

def send_to_appsync(action, instance_id, status, message=None, user_email=None):
    """Send action status to AppSync via GraphQL mutation."""
    if not endpoint:
        logger.warning("AppSync endpoint not configured")
        return False
    
    try:
        # GraphQL mutation
        mutation = """
        mutation PutServerActionStatus($input: ServerActionStatusInput!) {
            putServerActionStatus(input: $input) {
                id
                action
                status
                message
                timestamp
            }
        }
        """
        
        variables = {
            "input": {
                "id": instance_id,
                "action": action,
                "status": status,
                "message": message or "",
                "userEmail": user_email or "",
                "timestamp": int(time.time())
            }
        }
        
        payload = {
            "query": mutation,
            "variables": variables
        }
        
        # Create AWS request with SigV4 signing
        session = Session()
        credentials = session.get_credentials()
        request = AWSRequest(
            method='POST',
            url=endpoint,
            data=json.dumps(payload),
            headers={'Content-Type': 'application/json'}
        )
        
        # Sign the request
        SigV4Auth(credentials, 'appsync', aws_region).add_auth(request)
        
        # Send request
        http_session = URLLib3Session()
        response = http_session.send(request)
        
        if response['status_code'] == 200:
            logger.info(f"Status sent to AppSync: {status}")
            return True
        else:
            logger.error(f"AppSync request failed: {response['status_code']} - {response['body']}")
            return False
            
    except Exception as e:
        logger.error(f"Failed to send to AppSync: {str(e)}")
        return False

def _parse_message(message_body):
    """Parse and validate SQS message"""
    try:
        message = json.loads(message_body)
        logger.info(f"Message parsed: action={message.get('action')}, instance={message.get('instanceId')}")
        return message
    except json.JSONDecodeError as e:
        # ErrorHandler.log_error('VALIDATION_ERROR',
        #                      context={'operation': 'parse_message'},
        #                      exception=e, error=str(e))
        return None

def _validate_message(message):
    """Validate required message fields"""
    if 'action' not in message:
        # ErrorHandler.log_error('VALIDATION_ERROR',
        #                      context={'operation': 'validate_message'},
        #                      error='Missing action field')
        return False
    
    action = message['action'].lower().strip()
    if action != 'createserver' and 'instanceId' not in message:
        # ErrorHandler.log_error('VALIDATION_ERROR',
        #                      context={'operation': 'validate_message', 'action': action},
        #                      error='Missing instanceId field')
        return False
    
    return True

def _route_action(action, instance_id, arguments, message):
    """Route action to appropriate handler"""
    handlers = {
        ('start', 'startserver'): lambda: handle_server_action('start', instance_id),
        ('stop', 'stopserver'): lambda: handle_server_action('stop', instance_id),
        ('restart', 'restartserver'): lambda: handle_server_action('restart', instance_id),
        ('putserverconfig', 'updateserverconfig'): lambda: handle_update_server_config(instance_id, arguments),
        ('updateservername',): lambda: handle_update_server_name(instance_id, arguments),
        ('createserver',): lambda: process_create_server(message)
    }
    
    for actions, handler in handlers.items():
        if action in actions:
            try:
                return handler()
            except Exception as e:
                # ErrorHandler.log_error('INTERNAL_ERROR',
                #                      context={'operation': 'route_action', 'action': action, 'instance_id': instance_id},
                #                      exception=e, error=str(e))
                return False
    
    # ErrorHandler.log_error('VALIDATION_ERROR',
    #                      context={'operation': 'route_action', 'action': action, 'instance_id': instance_id},
    #                      error=f'Unknown action: {action}')
    return False

def _send_status_update(action, instance_id, status, message, user_email):
    """Send status update with error handling"""
    try:
        send_to_appsync(action, instance_id, status, message, user_email)
        logger.info(f"Status sent: {status}")
    except Exception as e:
        # ErrorHandler.log_error('NETWORK_ERROR',
        #                      context={'operation': 'send_status_update', 'action': action, 'instance_id': instance_id},
        #                      exception=e, error=str(e))

def process_server_action(message_body):
    """Process server action from SQS message"""
    logger.info(f"Processing action: body_length={len(message_body)}")
    
    # Parse message
    message = _parse_message(message_body)
    if not message:
        return False
    
    # Validate message
    if not _validate_message(message):
        return False
    
    action = message['action'].lower().strip()
    instance_id = message.get('instanceId', 'pending')
    arguments = message.get('arguments')
    user_email = message.get('userEmail')
    
    logger.info(f"Action: {action}, instance: {instance_id}")
    
    # Send initial status (except for createserver)
    if action != 'createserver':
        _send_status_update(action, instance_id, "PROCESSING", f"Processing {action}", user_email)
    
    # Execute action
    try:
        result = _route_action(action, instance_id, arguments, message)
        error_message = f"Failed to {action}" if not result else None
    except Exception as e:
        logger.error(f"Handler failed: {str(e)}", exc_info=True)
        result = False
        error_message = f"Handler error: {str(e)}"
    
    # Send final status
    if result:
        if action != 'createserver':  # createserver handles its own status
            _send_status_update(action, instance_id, "COMPLETED", f"Successfully completed {action}", user_email)
    else:
        final_message = error_message or f"Failed to complete {action}"
        _send_status_update(action, instance_id, "FAILED", final_message, user_email)
    
    return result

def _get_server_context(instance_id):
    """Get server info and EC2 state"""
    server_info = dyn.get_server_info(instance_id)
    if not server_info:
        return None, None, None, None
    
    instance = ec2_utils.list_server_by_id(instance_id)
    if not instance.get('Instances'):
        return None, None, None, None
    
    state = instance['Instances'][0]["State"]["Name"]
    user_email = server_info.get('userEmail')
    server_name = server_info.get('name', instance_id)
    
    return state, user_email, server_name, True

def _execute_ec2_action(action, instance_id):
    """Execute EC2 action and return success"""
    actions = {
        'start': lambda: ec2_client.start_instances(InstanceIds=[instance_id]),
        'stop': lambda: ec2_client.stop_instances(InstanceIds=[instance_id]),
        'restart': lambda: ec2_client.reboot_instances(InstanceIds=[instance_id])
    }
    
    try:
        actions[action]()
        return True
    except Exception as e:
        logger.error(f"EC2 {action} failed: {str(e)}")
        return False

def _send_notification(user_email, server_name, action, instance_id):
    """Send email notification if user email exists"""
    if user_email:
        utils.send_server_notification_email(user_email, server_name, action, instance_id)

def handle_server_action(action, instance_id):
    """Handle EC2 instance actions (start/stop/restart)"""
    logger.info(f"Handling {action} for {instance_id}")
    
    # Get server context
    state, user_email, server_name, success = _get_server_context(instance_id)
    if not success:
        logger.error(f"Server info not found: {instance_id}")
        return False
    
    # Check valid state transitions
    valid_states = {
        'start': 'stopped',
        'stop': 'running', 
        'restart': 'running'
    }
    
    if state != valid_states.get(action):
        logger.warning(f"Cannot {action} instance in state {state}")
        return False
    
    # Execute action
    if _execute_ec2_action(action, instance_id):
        _send_notification(user_email, server_name, action, instance_id)
        logger.info(f"{action.capitalize()} initiated for {instance_id}")
        return True
    
    return False

def _save_config_to_db(instance_id, arguments):
    """Save configuration to DynamoDB"""
    if 'id' not in arguments:
        arguments['id'] = instance_id
    
    dyn.put_server_config(arguments)

def _configure_schedule_shutdown(instance_id, arguments):
    """Configure schedule-based shutdown"""
    stop_schedule = arguments.get('stopScheduleExpression')
    start_schedule = arguments.get('startScheduleExpression')
    timezone = arguments.get('timezone', 'UTC')
    
    # Configure or remove stop schedule
    if stop_schedule:
        configure_scheduled_shutdown_event(instance_id, stop_schedule, timezone)
    else:
        remove_scheduled_shutdown_event(instance_id)
    
    # Configure or remove start schedule
    if start_schedule:
        configure_start_event(instance_id, start_schedule, timezone)
    else:
        remove_start_event(instance_id)

def _configure_alarm_shutdown(instance_id, arguments):
    """Configure alarm-based shutdown (CPU-based)"""
    alarm_threshold = arguments.get('alarmThreshold', 0)
    alarm_period = arguments.get('alarmEvaluationPeriod', 10)
    
    if alarm_threshold and alarm_threshold > 0:
        ec2_utils.update_alarm(instance_id, 'CPUUtilization', alarm_threshold, alarm_period)
    else:
        ec2_utils.remove_alarm(instance_id)

def handle_update_server_config(instance_id, arguments):
    """Handle server configuration updates"""
    logger.info(f"Updating config for {instance_id}")
    
    if not arguments:
        logger.error("Missing arguments")
        return False
    
    try:
        # Save to database
        _save_config_to_db(instance_id, arguments)
        
        # Configure CPU-based alarm (independent of schedule)
        _configure_alarm_shutdown(instance_id, arguments)
        
        # Configure schedules (independent of alarm)
        _configure_schedule_shutdown(instance_id, arguments)
        
        logger.info(f"Config updated successfully for {instance_id}")
        return True
        
    except Exception as e:
        logger.error(f"Config update failed: {str(e)}")
        return False

def process_create_server(message):
    """Process server creation request from SQS message"""
    logger.info(f"Server creation handler started: message={message}")
    
    try:
        # Extract parameters directly from message (not from arguments field)
        server_name = message.get('serverName')
        instance_type = message.get('instanceType', 't3.micro')
        user_email = message.get('userEmail')
        
        if not server_name:
            logger.error("Server creation FAILED: Missing serverName in message")
            return False
        
        logger.info(f"Server creation: Processing request - name={server_name}, type={instance_type}, user={user_email}")
        
        # Create EC2 instance using ec2Helper
        logger.info(f"Creating EC2 instance: name={server_name}, type={instance_type}")
        instance_id = ec2_utils.create_ec2_instance(
            instance_name=server_name,
            instance_type=instance_type,
            subnet_id=None,  # Use default
            security_group_id=None  # Use default
        )
        
        if not instance_id:
            logger.error(f"Server creation FAILED: EC2 instance creation failed for {server_name}")
            return False
        
        logger.info(f"EC2 instance created successfully: instance_id={instance_id}, name={server_name}")
        
        # Configure default shutdown mechanism 
        try:
            alarm_threshold = message.get('alarmThreshold', 5.0)
            alarm_period = message.get('alarmEvaluationPeriod', 30)
            logger.info(f"Configuring CPU-based shutdown: instance={instance_id}, threshold={alarm_threshold}, period={alarm_period}")
            ec2_utils.update_alarm(instance_id, 'CPUUtilization', alarm_threshold, alarm_period)
            logger.info(f"CPU alarm configured successfully: instance={instance_id}")
                
            # elif shutdown_method == 'Connections':
            #     alarm_threshold = message.get('alarmThreshold', 0)
            #     alarm_period = message.get('alarmEvaluationPeriod', 30)
            #     logger.info(f"Configuring connection-based shutdown: instance={instance_id}, threshold={alarm_threshold}, period={alarm_period}")
            #     ec2_utils.update_alarm(instance_id, 'Connections', alarm_threshold, alarm_period)
            #     logger.info(f"Connection alarm configured successfully: instance={instance_id}")
                
            start_schedule = message.get('startScheduleExpression', '')
            stop_schedule = message.get('stopScheduleExpression', '')
            timezone = message.get('timezone', 'UTC')
                
            if utils.is_valid_cron(stop_schedule):
                logger.info(f"Configuring scheduled shutdown: instance={instance_id}, schedule={stop_schedule}, timezone={timezone}")
                configure_scheduled_shutdown_event(instance_id, stop_schedule, timezone)
                logger.info(f"Shutdown schedule configured successfully: instance={instance_id}")
            
            if utils.is_valid_cron(start_schedule):
                logger.info(f"Configuring scheduled start: instance={instance_id}, schedule={start_schedule}, timezone={timezone}")
                configure_start_event(instance_id, start_schedule, timezone)
                logger.info(f"Start schedule configured successfully: instance={instance_id}")
                    
        except Exception as e:
            logger.error(f"Server creation WARNING: Failed to configure shutdown mechanism - instance={instance_id}, error={str(e)}", exc_info=True)
            # Continue with creation even if shutdown configuration fails
        
        # Store initial configuration in DynamoDB
        try:
            logger.info(f"Storing server configuration in DynamoDB: instance={instance_id}")
            
            config = {
                'id': instance_id,
                'alarmThreshold': message.get('alarmThreshold', 0.0),
                'alarmEvaluationPeriod': message.get('alarmEvaluationPeriod', 0),
                'startScheduleExpression': message.get('startScheduleExpression', ''),
                'stopScheduleExpression': message.get('stopScheduleExpression', ''),
                'runCommand': '/opt/minecraft/start.sh',  # Default Minecraft command
                'workDir': '/opt/minecraft',  # Default working directory
                'timezone': message.get('timezone', 'UTC'),
                'autoConfigured': False,  # User-configured server
                'isBootstrapComplete': False,  # Will be set to true after bootstrap
                'minecraftVersion': '',
                'latestPatchUpdate': ''
            }
            
            dyn.put_server_config(config)
            logger.info(f"Server configuration stored successfully: instance={instance_id}")
            
        except Exception as e:
            logger.error(f"Server creation WARNING: Failed to store configuration in DynamoDB - instance={instance_id}, error={str(e)}", exc_info=True)
            # Continue with creation even if DynamoDB storage fails
        
        # Send status update to AppSync with the actual instance ID
        try:
            logger.info(f"Sending completion status to AppSync: instance={instance_id}")
            send_to_appsync('createServer', instance_id, 'COMPLETED', 
                          f"Server {server_name} created successfully", user_email)
            logger.info(f"Completion status sent successfully: instance={instance_id}")
        except Exception as e:
            logger.error(f"Server creation WARNING: Failed to send status to AppSync - instance={instance_id}, error={str(e)}", exc_info=True)
        
        logger.info(f"Server creation SUCCESS: Server {server_name} created successfully with instance ID {instance_id}")
        return True
        
    except Exception as e:
        logger.error(f"Server creation handler FAILED with exception: error={str(e)}", exc_info=True)
        return False

def handle_update_server_name(instance_id, arguments):
    """Handle server name updates"""
    logger.info(f"Server name update handler started: instance={instance_id}, has_arguments={arguments is not None}")
    
    try:
        if not arguments:
            logger.error(f"Server name update FAILED: Missing arguments - instance={instance_id}")
            return False
        
        new_name = arguments.get('newName')
        if not new_name:
            logger.error(f"Server name update FAILED: Missing newName in arguments - instance={instance_id}")
            return False
        
        logger.info(f"Server name update: Processing name change - instance={instance_id}, newName={new_name}")
        
        # Update the EC2 instance Name tag
        try:
            logger.info(f"Updating EC2 instance Name tag: instance={instance_id}, newName={new_name}")
            success = ec2_utils.update_instance_name_tag(instance_id, new_name)
            
            if not success:
                logger.error(f"Server name update FAILED: Failed to update EC2 Name tag - instance={instance_id}")
                return False
                
            logger.info(f"EC2 Name tag updated successfully: instance={instance_id}, newName={new_name}")
            
        except Exception as e:
            logger.error(f"Server name update FAILED: Error updating EC2 Name tag - instance={instance_id}, error={str(e)}", exc_info=True)
            return False
        
        # Update the server name in DynamoDB
        try:
            logger.info(f"Updating server name in DynamoDB: instance={instance_id}, newName={new_name}")
            
            # Update just the server name
            dyn.update_server_name(instance_id, new_name)
            logger.info(f"Server name updated successfully in DynamoDB: instance={instance_id}")
            
        except Exception as e:
            logger.error(f"Server name update FAILED: Error updating DynamoDB - instance={instance_id}, error={str(e)}", exc_info=True)
            return False
        
        logger.info(f"Server name update SUCCESS: Name updated successfully - instance={instance_id}, newName={new_name}")
        return True
        
    except Exception as e:
        logger.error(f"Server name update handler FAILED with exception: instance={instance_id}, error={str(e)}", exc_info=True)
        return False

def handler(event, context):
    """SQS event handler"""
    logger.info(f"SQS handler invoked: record_count={len(event.get('Records', []))}")
    
    for idx, record in enumerate(event['Records']):
        message_id = record.get('messageId', 'unknown')
        logger.info(f"Processing SQS message {idx + 1}/{len(event['Records'])}: messageId={message_id}")
        
        try:
            success = process_server_action(record['body'])
            
            if not success:
                # ErrorHandler.log_error('INTERNAL_ERROR',
                #                      context={'operation': 'handler', 'message_id': message_id},
                #                      error='Message processing failed')
                # Message will be retried or sent to DLQ based on SQS configuration
            else:
                logger.info(f"Message processing SUCCESS: messageId={message_id}")
                
        except Exception as e:
            # ErrorHandler.log_error('INTERNAL_ERROR',
            #                      context={'operation': 'handler', 'message_id': message_id},
            #                      exception=e, error=str(e))
            return None