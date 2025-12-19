import boto3
import logging
import json
import os
import time
import ec2Helper
import ddbHelper
import utilHelper
import httpx
from httpx_aws_auth import AwsSigV4Auth, AwsCredentials
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ec2_client = boto3.client('ec2')
eventbridge_client = boto3.client('events')
ec2_utils = ec2Helper.Ec2Utils()
utils = utilHelper.Utils()
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

def _strip_leading_zeros(field):
    """Strip leading zeros from cron field values."""
    if not field or field == '*' or field == '?':
        return field

    if ',' in field:
        values = field.split(',')
        return ','.join(_strip_leading_zeros(v.strip()) for v in values)
    
    if '-' in field and '/' not in field:
        try:
            start, end = field.split('-', 1)
            return f"{_strip_leading_zeros(start)}-{_strip_leading_zeros(end)}"
        except ValueError:
            return field
    
    if '/' in field:
        try:
            base, step = field.split('/', 1)
            return f"{_strip_leading_zeros(base)}/{step.lstrip('0') or '0'}"
        except ValueError:
            return field
    
    if field.isdigit():
        return field.lstrip('0') or '0'
    
    return field

def _convert_day_of_week(day_of_week):
    """Convert day-of-week from standard cron (0-6) to EventBridge (1-7)."""
    if day_of_week == '*':
        return '*'
    
    if ',' in day_of_week:
        values = day_of_week.split(',')
        converted_values = []
        for val in values:
            if val.strip() == '0':
                converted_values.append('7')
            elif val.strip().isdigit() and 1 <= int(val.strip()) <= 6:
                converted_values.append(val.strip())
        return ','.join(converted_values)
    
    if day_of_week == '0':
        return '7'
    elif day_of_week.isdigit() and 1 <= int(day_of_week) <= 6:
        return day_of_week
    
    return None

def _convert_timezone_to_utc(hour, minute, timezone):
    """Convert local time to UTC based on timezone."""
    from datetime import datetime
    import pytz
    
    if not timezone or timezone == 'UTC':
        return hour, minute
    
    try:
        # Create a datetime in the specified timezone
        tz = pytz.timezone(timezone)
        # Use a fixed date to get consistent offset (mid-January to avoid most DST transitions)
        local_time = tz.localize(datetime(2024, 1, 15, int(hour), int(minute)))
        
        # Convert to UTC
        utc_time = local_time.astimezone(pytz.UTC)
        
        return str(utc_time.hour), str(utc_time.minute)
    except Exception as e:
        logger.error(f"Error converting timezone {timezone} to UTC: {e}")
        # Return original values if conversion fails
        return hour, minute

def _format_schedule_expression(cron_expression, timezone='UTC'):
    """Format cron expression for EventBridge, converting from local timezone to UTC."""
    if not cron_expression:
        return None
    
    cron_expression = cron_expression.strip()
    
    # If already in EventBridge format, extract and clean it
    if cron_expression.startswith('cron(') and cron_expression.endswith(')'):
        cron_content = cron_expression[5:-1]
        fields = cron_content.split()
        if len(fields) == 6:
            minute, hour, day, month, day_of_week, year = fields
            
            # Convert timezone if not UTC
            if timezone and timezone != 'UTC':
                hour, minute = _convert_timezone_to_utc(hour, minute, timezone)
            
            minute = _strip_leading_zeros(minute)
            hour = _strip_leading_zeros(hour)
            day = _strip_leading_zeros(day)
            month = _strip_leading_zeros(month)
            return f"cron({minute} {hour} {day} {month} {day_of_week} {year})"
        return cron_expression
    
    # Handle standard 5-field cron expression
    fields = cron_expression.split()
    if len(fields) == 5:
        minute, hour, day, month, day_of_week = fields
        
        # Convert timezone to UTC if needed
        if timezone and timezone != 'UTC':
            hour, minute = _convert_timezone_to_utc(hour, minute, timezone)
        
        # Strip leading zeros
        minute = _strip_leading_zeros(minute)
        hour = _strip_leading_zeros(hour)
        day = _strip_leading_zeros(day)
        month = _strip_leading_zeros(month)
        
        # Convert day-of-week
        converted_dow = _convert_day_of_week(day_of_week)
        if not converted_dow:
            return None
        
        # Optimize: if all days are specified, use '*'
        if ',' in converted_dow:
            dow_values = set(converted_dow.split(','))
            if dow_values == {'1', '2', '3', '4', '5', '6', '7'}:
                converted_dow = '*'
        
        # EventBridge rule: when day-of-week is specified, day-of-month must be '?'
        if converted_dow != '?':
            day = '?'
        
        return f"cron({minute} {hour} {day} {month} {converted_dow} *)"
    
    return None

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
    """
    Log action status for monitoring and debugging.
    Note: Status updates are not persisted to DynamoDB.
    Future: Could broadcast via subscription for real-time UI updates.
    """
    logger.info(f"Action status: action={action}, instance={instance_id}, status={status}, user={user_email}, message={message}")
    
    # Status is logged but not persisted or broadcast
    # This keeps the logs clean for CloudWatch monitoring
    return True

def process_server_action(message_body):
    """Process server action from SQS message"""
    logger.info(f"Action processing started: message_body_length={len(message_body)}")
    
    message = None
    try:
        # Parse message body
        try:
            message = json.loads(message_body)
            logger.info(f"Message parsed successfully: action={message.get('action')}, instance={message.get('instanceId')}")
        except json.JSONDecodeError as e:
            logger.error(f"Action processing FAILED: Invalid JSON in message body - error={str(e)}, body={message_body[:200]}", exc_info=True)
            return False
        
        # Extract required fields
        if 'action' not in message:
            logger.error(f"Action processing FAILED: Missing 'action' field in message - message={message}")
            return False
        if 'instanceId' not in message:
            logger.error(f"Action processing FAILED: Missing 'instanceId' field in message - message={message}")
            return False
            
        action = message['action'].lower().strip()
        instance_id = message['instanceId']
        arguments = message.get('arguments')
        user_email = message.get('userEmail')
        
        logger.info(f"Action processing: action={action}, instance={instance_id}, user={user_email}, has_arguments={arguments is not None}")
        
        # Send initial PROCESSING status to AppSync
        logger.info(f"Sending initial PROCESSING status: action={action}, instance={instance_id}")
        status_sent = send_to_appsync(action, instance_id, "PROCESSING", f"Processing {action}", user_email)
        if status_sent:
            logger.info(f"Initial PROCESSING status sent successfully: action={action}, instance={instance_id}")
        else:
            logger.warning(f"Initial PROCESSING status failed to send: action={action}, instance={instance_id}")
        
        # Route to appropriate handler based on action type
        result = False
        error_message = None
        
        logger.info(f"Routing action to handler: action={action}, instance={instance_id}")
        
        try:
            if action == 'start' or action == 'startserver':
                logger.info(f"Routing to handle_server_action(start): instance={instance_id}")
                result = handle_server_action('start', instance_id)
                error_message = "Failed to start server" if not result else None
            elif action == 'stop' or action == 'stopserver':
                logger.info(f"Routing to handle_server_action(stop): instance={instance_id}")
                result = handle_server_action('stop', instance_id)
                error_message = "Failed to stop server" if not result else None
            elif action == 'restart' or action == 'restartserver':
                logger.info(f"Routing to handle_server_action(restart): instance={instance_id}")
                result = handle_server_action('restart', instance_id)
                error_message = "Failed to restart server" if not result else None
            elif action == 'putserverconfig' or action == 'updateserverconfig':
                logger.info(f"Routing to handle_update_server_config: instance={instance_id}")
                result = handle_update_server_config(instance_id, arguments)
                error_message = "Failed to update server configuration" if not result else None
            elif action == 'updateservername':
                logger.info(f"Routing to handle_update_server_name: instance={instance_id}")
                result = handle_update_server_name(instance_id, arguments)
                error_message = "Failed to update server name" if not result else None
            else:
                logger.error(f"Action routing FAILED: Unknown action type - action={action}, instance={instance_id}")
                send_to_appsync(action, instance_id, "FAILED", f"Unknown action: {action}", user_email)
                return False
        except Exception as handler_error:
            logger.error(f"Handler execution FAILED with exception: action={action}, instance={instance_id}, error={str(handler_error)}", exc_info=True)
            error_message = f"Handler error: {str(handler_error)}"
            result = False
        
        # Send final status to AppSync
        logger.info(f"Sending final status: action={action}, instance={instance_id}, result={result}")
        if result:
            logger.info(f"Action completed successfully: action={action}, instance={instance_id}")
            final_status_sent = send_to_appsync(action, instance_id, "COMPLETED", f"Successfully completed {action}", user_email)
            if final_status_sent:
                logger.info(f"Final COMPLETED status sent successfully: action={action}, instance={instance_id}")
            else:
                logger.warning(f"Final COMPLETED status failed to send: action={action}, instance={instance_id}")
        else:
            final_message = error_message or f"Failed to complete {action}"
            logger.error(f"Action failed: action={action}, instance={instance_id}, error={final_message}")
            final_status_sent = send_to_appsync(action, instance_id, "FAILED", final_message, user_email)
            if final_status_sent:
                logger.info(f"Final FAILED status sent successfully: action={action}, instance={instance_id}")
            else:
                logger.warning(f"Final FAILED status failed to send: action={action}, instance={instance_id}")
            
        return result
            
    except Exception as e:
        logger.error(f"Action processing FAILED with unexpected exception: error={str(e)}, message={message}", exc_info=True)
        # Try to send failure status if we have enough information
        try:
            if message:
                action = message.get('action', 'unknown')
                instance_id = message.get('instanceId', 'unknown')
                user_email = message.get('userEmail')
                logger.info(f"Attempting to send error status to AppSync: action={action}, instance={instance_id}")
                status_sent = send_to_appsync(
                    action, 
                    instance_id, 
                    "FAILED", 
                    f"Error processing message: {str(e)}", 
                    user_email
                )
                if status_sent:
                    logger.info(f"Error status sent successfully to AppSync: action={action}, instance={instance_id}")
                else:
                    logger.warning(f"Error status failed to send to AppSync: action={action}, instance={instance_id}")
        except Exception as appsync_error:
            logger.error(f"Failed to send error status to AppSync with exception: error={str(appsync_error)}", exc_info=True)
        return False

def handle_server_action(action, instance_id):
    """Handle EC2 instance actions (start/stop/restart)"""
    logger.info(f"Server action handler started: action={action}, instance={instance_id}")
    
    try:
        # Get server info from DynamoDB
        dyn = ddbHelper.Dyn()
        server_info = dyn.get_server_info(instance_id)
        
        if not server_info:
            logger.error(f"Server action FAILED: Server info not found in DynamoDB - instance={instance_id}")
            return False
        
        user_email = server_info.get('userEmail')
        server_name = server_info.get('name', instance_id)
        
        # Retrieve EC2 instance information
        logger.info(f"Retrieving EC2 instance information: instance={instance_id}")
        instance = ec2_utils.list_server_by_id(instance_id)
        if not instance.get('Instances'):
            logger.error(f"Server action FAILED: EC2 instance not found - instance={instance_id}")
            return False
            
        instance_info = instance['Instances'][0]        
        state = instance_info["State"]["Name"]
        
        logger.info(f"Instance state retrieved: instance={instance_id}, state={state}, name={server_name}, user={user_email}")
        
        # Handle start action
        if action == "start":
            if state == "stopped":
                try:
                    logger.info(f"Executing EC2 start_instances: instance={instance_id}")
                    ec2_client.start_instances(InstanceIds=[instance_id])
                    logger.info(f"Server action SUCCESS: Start initiated for instance {instance_id}")
                    
                    # Send email notification
                    if user_email:
                        utils.send_server_notification_email(user_email, server_name, 'start', instance_id)
                    else:
                        logger.warning(f"No userEmail found for instance {instance_id}, skipping email notification")
                    
                    return True
                except Exception as e:
                    logger.error(f"Server action FAILED: Start failed for instance {instance_id}, error={str(e)}", exc_info=True)
                    return False
            else:
                logger.warning(f"Server action SKIPPED: Cannot start instance {instance_id} in state {state}")
                return False

        # Handle stop action        
        elif action == "stop":
            if state == "running":
                try:
                    logger.info(f"Executing EC2 stop_instances: instance={instance_id}")
                    ec2_client.stop_instances(InstanceIds=[instance_id])
                    logger.info(f"Server action SUCCESS: Stop initiated for instance {instance_id}")
                    
                    # Send email notification
                    if user_email:
                        utils.send_server_notification_email(user_email, server_name, 'stop', instance_id)
                    else:
                        logger.warning(f"No userEmail found for instance {instance_id}, skipping email notification")
                    
                    return True
                except Exception as e:
                    logger.error(f"Server action FAILED: Stop failed for instance {instance_id}, error={str(e)}", exc_info=True)
                    return False
            else:
                logger.warning(f"Server action SKIPPED: Cannot stop instance {instance_id} in state {state}")
                return False

        # Handle restart action
        elif action == "restart":
            if state == "running":
                try:
                    logger.info(f"Executing EC2 reboot_instances: instance={instance_id}")
                    ec2_client.reboot_instances(InstanceIds=[instance_id])
                    logger.info(f"Server action SUCCESS: Restart initiated for instance {instance_id}")
                    
                    # Send email notification
                    if user_email:
                        utils.send_server_notification_email(user_email, server_name, 'restart', instance_id)
                    else:
                        logger.warning(f"No userEmail found for instance {instance_id}, skipping email notification")
                    
                    return True
                except Exception as e:
                    logger.error(f"Server action FAILED: Restart failed for instance {instance_id}, error={str(e)}", exc_info=True)
                    return False
            else:
                logger.warning(f"Server action SKIPPED: Cannot restart instance {instance_id} in state {state}")
                return False
        else:
            logger.error(f"Server action FAILED: Unknown action type - action={action}, instance={instance_id}")
            return False
                
    except Exception as e:
        logger.error(f"Server action handler FAILED with exception: action={action}, instance={instance_id}, error={str(e)}", exc_info=True)
        return False

def handle_update_server_config(instance_id, arguments):
    """Handle server configuration updates"""
    logger.info(f"Config update handler started: instance={instance_id}, has_arguments={arguments is not None}")
    
    try:
        if not arguments:
            logger.error(f"Config update FAILED: Missing arguments - instance={instance_id}")
            return False
        
        logger.info(f"Config update: Processing arguments - instance={instance_id}, arguments={arguments}")
        
        # Ensure instance_id is in the config
        if 'id' not in arguments:
            arguments['id'] = instance_id
        
        dyn = ddbHelper.Dyn()

        # Save configuration to DynamoDB
        try:
            logger.info(f"Saving server config to DynamoDB: instance={instance_id}")
            response = dyn.put_server_config(arguments)
            logger.info(f"Server config saved successfully: instance={instance_id}, response={response}")

        except Exception as e:
            logger.error(f"Config update FAILED: Failed to save server config to DynamoDB - instance={instance_id}, error={str(e)}", exc_info=True)
            return False
        
        shutdown_method = arguments.get('shutdownMethod', '')
        logger.info(f"Config update: Processing shutdown method - instance={instance_id}, method={shutdown_method}")
        
        # Handle Schedule-based shutdown
        if shutdown_method == 'Schedule':
            stop_schedule = arguments.get('stopScheduleExpression')
            timezone = arguments.get('timezone', 'UTC')
            
            if not stop_schedule:
                logger.error(f"Config update FAILED: Missing stop schedule expression - instance={instance_id}")
                return False
            
            try:
                # Remove alarm (switching to schedule)
                logger.info(f"Config update: Removing alarm (switching to schedule) - instance={instance_id}")
                ec2_utils.remove_alarm(instance_id)
                logger.info(f"Alarm removed successfully: instance={instance_id}")
                
                # Configure event for scheduled shutdown
                logger.info(f"Config update: Configuring shutdown schedule - instance={instance_id}, schedule={stop_schedule}, timezone={timezone}")
                configure_scheduled_shutdown_event(instance_id, stop_schedule, timezone)
                logger.info(f"Shutdown schedule configured successfully: instance={instance_id}")
                
                # Configure start schedule if provided
                start_schedule = arguments.get('startScheduleExpression')
                if start_schedule:
                    logger.info(f"Config update: Configuring start schedule - instance={instance_id}, schedule={start_schedule}, timezone={timezone}")
                    configure_start_event(instance_id, start_schedule, timezone)
                    logger.info(f"Start schedule configured successfully: instance={instance_id}")
                else:
                    logger.info(f"Config update: Removing start schedule - instance={instance_id}")
                    remove_start_event(instance_id)
                    logger.info(f"Start schedule removed successfully: instance={instance_id}")
                    
            except ValueError as ve:
                logger.error(f"Config update FAILED: Invalid schedule expression - instance={instance_id}, error={str(ve)}", exc_info=True)
                return False
            except Exception as e:
                error_msg = str(e)
                # Check for AWS ValidationException
                if "ValidationException" in error_msg or "Parameter ScheduleExpression is not valid" in error_msg:
                    logger.error(f"Config update FAILED: Invalid schedule expression format - instance={instance_id}, error={error_msg}", exc_info=True)
                else:
                    logger.error(f"Config update FAILED: Error configuring schedule - instance={instance_id}, error={error_msg}", exc_info=True)
                return False
                
        # Handle CPU/Connections-based shutdown
        elif shutdown_method in ['CPUUtilization', 'Connections']:
            alarm_threshold = arguments.get('alarmThreshold')
            alarm_period = arguments.get('alarmEvaluationPeriod')
            
            if alarm_threshold is None or alarm_period is None:
                logger.error(f"Config update FAILED: Missing alarm parameters - instance={instance_id}, threshold={alarm_threshold}, period={alarm_period}")
                return False
            
            try:
                # Remove schedule events (switching to alarm)
                logger.info(f"Config update: Removing schedule events (switching to alarm) - instance={instance_id}")
                remove_scheduled_shutdown_event(instance_id)
                remove_start_event(instance_id)
                logger.info(f"Schedule events removed successfully: instance={instance_id}")
                
                # Create alarm
                logger.info(f"Config update: Creating {shutdown_method} alarm - instance={instance_id}, threshold={alarm_threshold}, period={alarm_period}")
                ec2_utils.update_alarm(instance_id, shutdown_method, alarm_threshold, alarm_period)
                logger.info(f"Alarm created successfully: instance={instance_id}, type={shutdown_method}")
            except Exception as e:
                logger.error(f"Config update FAILED: Error configuring alarm - instance={instance_id}, error={str(e)}", exc_info=True)
                return False
        else:
            if shutdown_method:
                logger.warning(f"Config update: Unknown shutdown method - instance={instance_id}, method={shutdown_method}")
            else:
                logger.info(f"Config update: No shutdown method specified - instance={instance_id}")
        
        logger.info(f"Config update SUCCESS: Configuration updated successfully - instance={instance_id}")
        return True
        
    except Exception as e:
        logger.error(f"Config update handler FAILED with exception: instance={instance_id}, error={str(e)}", exc_info=True)
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
            dyn = ddbHelper.Dyn()
            
            # Update just the server name
            response = dyn.update_server_name(instance_id, new_name)
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
        
        success = process_server_action(record['body'])
        
        if not success:
            logger.error(f"Message processing FAILED: messageId={message_id}")
            # Message will be retried or sent to DLQ based on SQS configuration
        else:
            logger.info(f"Message processing SUCCESS: messageId={message_id}")