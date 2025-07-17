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
    if not endpoint:
        logger.warning("No AppSync endpoint configured, skipping status update")
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
        
        headers = {"Content-Type": "application/json"}
        response = requests.post(
            endpoint,
            auth=auth,
            headers=headers,
            json=payload
        )
        
        if response.status_code == 200:
            logger.info(f"Successfully sent action status to AppSync: {action} - {status}")
            return True
        else:
            logger.error(f"Failed to send action status to AppSync: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        logger.error(f"Error sending action status to AppSync: {e}")
        return False

def process_server_action(message_body):
    """Process server action from SQS message"""
    try:
        message = json.loads(message_body)
        action = message['action'].lower().strip()
        instance_id = message['instanceId']
        arguments = message.get('arguments')
        user_email = message.get('userEmail')
        
        logger.info(f"Processing {action} for {instance_id} by {user_email}")
        
        # Send initial status to AppSync
        send_to_appsync(action, instance_id, "PROCESSING", f"Processing {action}", user_email)
        
        result = False
        if action in ['startserver', 'stopserver', 'restartserver']:
            result = handle_server_action(action.replace('server', ''), instance_id)
        elif action == 'fixserverrole':
            result = handle_fix_role(instance_id)
        elif action in ['putserverconfig', 'updateserverconfig']:
            result = handle_update_server_config(instance_id, arguments)
        else:
            logger.error(f"Unknown action: {action}")
            send_to_appsync(action, instance_id, "FAILED", f"Unknown action: {action}", user_email)
            return False
        
        # Send final status to AppSync
        if result:
            send_to_appsync(action, instance_id, "COMPLETED", f"Successfully completed {action}", user_email)
        else:
            send_to_appsync(action, instance_id, "FAILED", f"Failed to complete {action}", user_email)
            
        return result
            
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        try:
            send_to_appsync(
                message.get('action', 'unknown'), 
                message.get('instanceId', 'unknown'), 
                "FAILED", 
                f"Error processing message: {str(e)}", 
                message.get('userEmail')
            )
        except:
            pass
        return False

def handle_server_action(action, instance_id):
    """Handle EC2 instance actions"""
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
                return False

        # Handle stop action        
        elif action == "stop":
            if state == "running":
                ec2_client.stop_instances(InstanceIds=[instance_id])
                logger.info('Stopping instance %s', instance_id)
            else:
                logger.warning('Stop instance %s not possible - current state: %s', instance_id, state)
                return False

        # Handle restart action
        elif action == "restart":
            if state == "running":
                ec2_client.reboot_instances(InstanceIds=[instance_id])
                logger.info('Restarting instance %s', instance_id)
            else:
                logger.warning('Restart instance %s not possible - current state: %s', instance_id, state)
                return False
                
        return True
    except Exception as e:
        logger.error(f"Error in {action} action: {e}")
        return False

def handle_fix_role(instance_id):
    """Handle IAM role fix"""
    iam_profile = IamProfile(instance_id)
    resp = iam_profile.manage_iam_profile()
    logger.info("IAM role attachment response: %s", resp)
    
    # Check if the response is a dictionary with error information
    if isinstance(resp, dict) and resp.get("status") == "error":
        if resp.get("code") == "UnauthorizedOperation":
            logger.error("Unauthorized operation: %s", resp.get("message", ""))
            return False
    
    if resp is True:
        logger.info("Successfully attached IAM role to the Minecraft Instance")
        return True
    
    logger.error("Attaching IAM role failed")
    return False

def handle_update_server_config(instance_id, arguments):
    """Handle server configuration updates"""
    if not arguments:
        logger.error("Missing arguments for config update")
        return False
    
    try:
        response = ec2_utils.set_instance_attributes_to_tags(arguments)
        shutdown_method = response.get('shutdownMethod', '')
        logger.info(f"Processing shutdown method: {shutdown_method}")
        
        if shutdown_method == 'Schedule':
            stop_schedule = response.get('stopScheduleExpression')
            if not stop_schedule:
                logger.error("Missing schedule expression")
                return False
            
            try:
                # Remove alarm (switching to schedule)
                ec2_utils.remove_alarm(instance_id)
                # Configure event for scheduled shutdown
                ec2_utils.configure_shutdown_event(instance_id, stop_schedule)
                
                # Configure start schedule if provided
                start_schedule = response.get('startScheduleExpression')
                if start_schedule:
                    logger.info("Configuring start schedule: %s", start_schedule)
                    ec2_utils.configure_start_event(instance_id, start_schedule)
                else:
                    ec2_utils.remove_start_event(instance_id)
                    
            except ValueError as ve:
                logger.error("Invalid schedule expression: %s", str(ve))
                return False
            except Exception as e:
                logger.error("Error configuring schedule: %s", str(e))
                return False
                
        elif shutdown_method in ['CPUUtilization', 'Connections']:
            # CPU/Connections selected - activate alarm, deactivate schedule
            alarm_threshold = response.get('alarmThreshold')
            alarm_period = response.get('alarmEvaluationPeriod')
            
            if alarm_threshold is None or alarm_period is None:
                logger.error("Missing alarmEvaluationPeriod or alarmThreshold for alarm-based shutdown")
                return False
            
            # Remove schedule events (switching to alarm)
            ec2_utils.remove_shutdown_event(instance_id)
            ec2_utils.remove_start_event(instance_id)
            # Create alarm
            ec2_utils.update_alarm(instance_id, shutdown_method, alarm_threshold, alarm_period)
            logger.info(f"Created {shutdown_method} alarm with threshold {alarm_threshold}")
        else:
            logger.warning(f"Unknown shutdown method: {shutdown_method}")
        
        return True
    except Exception as e:
        logger.error(f"Error updating config: {e}")
        return False

def handler(event, context):
    """SQS event handler"""
    for record in event['Records']:
        success = process_server_action(record['body'])
        if not success:
            logger.error(f"Failed to process message: {record['messageId']}")
            # Message will be retried or sent to DLQ based on SQS configuration