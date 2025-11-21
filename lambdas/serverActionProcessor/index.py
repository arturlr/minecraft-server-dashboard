import boto3
import logging
import json
import os
import time
import ec2Helper
import utilHelper
import requests
from requests_aws4auth import AWS4Auth

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ec2_client = boto3.client('ec2')
ec2_utils = ec2Helper.Ec2Utils()
utl = utilHelper.Utils()

# Environment variables
appValue = os.getenv('TAG_APP_VALUE')
appName = os.getenv('APP_NAME')
envName = os.getenv('ENVIRONMENT_NAME')
ec2_instance_profile_name = os.getenv('EC2_INSTANCE_PROFILE_NAME')
ec2_instance_profile_arn = os.getenv('EC2_INSTANCE_PROFILE_ARN')
endpoint = os.getenv('APPSYNC_URL', None)

# Set up AWS4Auth for AppSync
boto3_session = boto3.Session()
credentials = boto3_session.get_credentials()
credentials = credentials.get_frozen_credentials()

auth = AWS4Auth(
    credentials.access_key,
    credentials.secret_key,
    boto3_session.region_name,
    'appsync',
    session_token=credentials.token,
)

# GraphQL mutation for server action status
putServerActionStatus = """
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

        logger.info("Attaching IAM role to the Minecraft Instance")
        return self.attach_iam_profile()

    def disassociate_iam_profile(self):
        logger.info("Disassociating IAM profile: %s", self.association_id)
        try:
            # Call EC2 API to remove the profile association
            self.ec2_client.disassociate_iam_instance_profile(AssociationId=self.association_id)
        except Exception as e:
            if "InvalidAssociationID.NotFound" in str(e):
                # Handle the case where the association ID doesn't exist
                logger.warning("Association ID not found: %s. This is not an error, continuing...", self.association_id)
                # Return True to continue with attaching the profile
                return True
            else:
                logger.error("Error disassociating IAM profile: %s", str(e))
                return False

        # Helper function that checks if profile is fully disassociated
        def check_disassociated_status():
            try:
                return ec2_utils.describe_iam_profile(self.instance_id, "disassociated", self.association_id) is not None
            except Exception as e:
                # If we get an error checking the status, assume it's disassociated
                logger.warning("Error checking disassociation status: %s. Assuming profile is disassociated.", str(e))
                return True

        # Retry checking disassociation status for up to 30 times with 5 second delays
        if not utl.retry_operation(check_disassociated_status, max_retries=30, delay=5):
            logger.warning("Profile timeout during disassociating")
            # Even if we time out, we'll try to attach the new profile anyway
            return True

        # Profile was successfully disassociated
        return True
    
    def attach_iam_profile(self):
        logger.info("Attaching IAM profile: %s", ec2_instance_profile_name)
        
        try:
            # Call EC2 API to associate the IAM profile with the instance
            response = self.ec2_client.associate_iam_instance_profile(
                IamInstanceProfile={"Name": ec2_instance_profile_name},
                InstanceId=self.instance_id
            )
        except Exception as e:
            error_msg = str(e)
            # Check if this is an unauthorized operation
            if "UnauthorizedOperation" in error_msg:
                logger.error("Unauthorized operation when attaching IAM profile: %s", error_msg)
                return {"status": "error", "message": error_msg, "code": "UnauthorizedOperation"}
            else:
                logger.error("Error attaching IAM profile: %s", error_msg)
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
        if not utl.retry_operation(check_associated_status, max_retries=30, delay=5):
            logger.warning("Profile timeout during association")
            return False

        # Profile was successfully attached
        return True

def send_to_appsync(action, instance_id, status, message=None, user_email=None):
    """Send action status to AppSync"""
    logger.info(f"AppSync status update: action={action}, instance={instance_id}, status={status}, user={user_email}, message={message}")
    
    if not endpoint:
        logger.warning(f"AppSync status update SKIPPED: No endpoint configured - action={action}, instance={instance_id}, status={status}")
        return False
    
    try:
        input_data = {
            "id": instance_id,
            "action": action,
            "status": status,
            "timestamp": int(time.time()),
            "message": message,
            "userEmail": user_email
        }
        
        payload = {
            "query": putServerActionStatus,
            "variables": {
                "input": input_data
            }
        }
        
        logger.info(f"Sending status to AppSync endpoint: action={action}, instance={instance_id}, status={status}")
        
        headers = {"Content-Type": "application/json"}
        response = requests.post(
            endpoint,
            auth=auth,
            headers=headers,
            json=payload
        )
        
        if response.status_code == 200:
            logger.info(f"AppSync status update SUCCESS: action={action}, instance={instance_id}, status={status}")
            return True
        else:
            logger.error(f"AppSync status update FAILED: action={action}, instance={instance_id}, status={status}, http_code={response.status_code}, response={response.text}")
            return False
    except Exception as e:
        logger.error(f"AppSync status update FAILED with exception: action={action}, instance={instance_id}, status={status}, error={str(e)}", exc_info=True)
        return False

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
            if action in ['start', 'startserver']:
                logger.info(f"Routing to handle_server_action(start): instance={instance_id}")
                result = handle_server_action('start', instance_id)
                error_message = "Failed to start server" if not result else None
            elif action in ['stop', 'stopserver']:
                logger.info(f"Routing to handle_server_action(stop): instance={instance_id}")
                result = handle_server_action('stop', instance_id)
                error_message = "Failed to stop server" if not result else None
            elif action in ['restart', 'restartserver']:
                logger.info(f"Routing to handle_server_action(restart): instance={instance_id}")
                result = handle_server_action('restart', instance_id)
                error_message = "Failed to restart server" if not result else None
            elif action in ['fixserverrole', 'fixrole']:
                logger.info(f"Routing to handle_fix_role: instance={instance_id}")
                result = handle_fix_role(instance_id)
                error_message = "Failed to fix IAM role" if not result else None
            elif action in ['putserverconfig', 'updateserverconfig']:
                logger.info(f"Routing to handle_update_server_config: instance={instance_id}")
                result = handle_update_server_config(instance_id, arguments)
                error_message = "Failed to update server configuration" if not result else None
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
        # Retrieve instance information
        logger.info(f"Retrieving instance information: instance={instance_id}")
        instance = ec2_utils.list_server_by_id(instance_id)
        if not instance.get('Instances'):
            logger.error(f"Server action FAILED: Instance not found - instance={instance_id}")
            return False
            
        instance_info = instance['Instances'][0]        
        state = instance_info["State"]["Name"]
        
        logger.info(f"Instance state retrieved: instance={instance_id}, state={state}")
        
        # Handle start action
        if action == "start":
            if state == "stopped":
                try:
                    logger.info(f"Executing EC2 start_instances: instance={instance_id}")
                    ec2_client.start_instances(InstanceIds=[instance_id])
                    logger.info(f"Server action SUCCESS: Start initiated for instance {instance_id}")
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

def handle_fix_role(instance_id):
    """Handle IAM role fix for instance"""
    logger.info(f"IAM role fix handler started: instance={instance_id}")
    
    try:
        logger.info(f"Creating IamProfile manager: instance={instance_id}")
        iam_profile = IamProfile(instance_id)
        
        logger.info(f"Executing IAM profile management: instance={instance_id}")
        resp = iam_profile.manage_iam_profile()
        logger.info(f"IAM profile management response: instance={instance_id}, response={resp}")
        
        # Check if the response is a dictionary with error information
        if isinstance(resp, dict) and resp.get("status") == "error":
            if resp.get("code") == "UnauthorizedOperation":
                logger.error(f"IAM role fix FAILED: Unauthorized operation - instance={instance_id}, message={resp.get('message', '')}")
                return False
            else:
                logger.error(f"IAM role fix FAILED: Error response - instance={instance_id}, message={resp.get('message', 'Unknown error')}")
                return False
        
        if resp is True:
            logger.info(f"IAM role fix SUCCESS: Role attached successfully - instance={instance_id}")
            return True
        
        logger.error(f"IAM role fix FAILED: Unexpected response - instance={instance_id}, response={resp}")
        return False
        
    except Exception as e:
        logger.error(f"IAM role fix handler FAILED with exception: instance={instance_id}, error={str(e)}", exc_info=True)
        return False

def handle_update_server_config(instance_id, arguments):
    """Handle server configuration updates"""
    logger.info(f"Config update handler started: instance={instance_id}, has_arguments={arguments is not None}")
    
    try:
        if not arguments:
            logger.error(f"Config update FAILED: Missing arguments - instance={instance_id}")
            return False
        
        logger.info(f"Config update: Processing arguments - instance={instance_id}, arguments={arguments}")
        
        # Set instance attributes to tags
        try:
            logger.info(f"Setting instance attributes to tags: instance={instance_id}")
            response = ec2_utils.set_instance_attributes_to_tags(arguments)
            logger.info(f"Instance attributes set successfully: instance={instance_id}, response={response}")
        except Exception as e:
            logger.error(f"Config update FAILED: Failed to set instance attributes to tags - instance={instance_id}, error={str(e)}", exc_info=True)
            return False
        
        shutdown_method = response.get('shutdownMethod', '')
        logger.info(f"Config update: Processing shutdown method - instance={instance_id}, method={shutdown_method}")
        
        # Handle Schedule-based shutdown
        if shutdown_method == 'Schedule':
            stop_schedule = response.get('stopScheduleExpression')
            if not stop_schedule:
                logger.error(f"Config update FAILED: Missing stop schedule expression - instance={instance_id}")
                return False
            
            try:
                # Remove alarm (switching to schedule)
                logger.info(f"Config update: Removing alarm (switching to schedule) - instance={instance_id}")
                ec2_utils.remove_alarm(instance_id)
                logger.info(f"Alarm removed successfully: instance={instance_id}")
                
                # Configure event for scheduled shutdown
                logger.info(f"Config update: Configuring shutdown schedule - instance={instance_id}, schedule={stop_schedule}")
                ec2_utils.configure_shutdown_event(instance_id, stop_schedule)
                logger.info(f"Shutdown schedule configured successfully: instance={instance_id}")
                
                # Configure start schedule if provided
                start_schedule = response.get('startScheduleExpression')
                if start_schedule:
                    logger.info(f"Config update: Configuring start schedule - instance={instance_id}, schedule={start_schedule}")
                    ec2_utils.configure_start_event(instance_id, start_schedule)
                    logger.info(f"Start schedule configured successfully: instance={instance_id}")
                else:
                    logger.info(f"Config update: Removing start schedule - instance={instance_id}")
                    ec2_utils.remove_start_event(instance_id)
                    logger.info(f"Start schedule removed successfully: instance={instance_id}")
                    
            except ValueError as ve:
                logger.error(f"Config update FAILED: Invalid schedule expression - instance={instance_id}, error={str(ve)}", exc_info=True)
                return False
            except Exception as e:
                logger.error(f"Config update FAILED: Error configuring schedule - instance={instance_id}, error={str(e)}", exc_info=True)
                return False
                
        # Handle CPU/Connections-based shutdown
        elif shutdown_method in ['CPUUtilization', 'Connections']:
            alarm_threshold = response.get('alarmThreshold')
            alarm_period = response.get('alarmEvaluationPeriod')
            
            if alarm_threshold is None or alarm_period is None:
                logger.error(f"Config update FAILED: Missing alarm parameters - instance={instance_id}, threshold={alarm_threshold}, period={alarm_period}")
                return False
            
            try:
                # Remove schedule events (switching to alarm)
                logger.info(f"Config update: Removing schedule events (switching to alarm) - instance={instance_id}")
                ec2_utils.remove_shutdown_event(instance_id)
                ec2_utils.remove_start_event(instance_id)
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