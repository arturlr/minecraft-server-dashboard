import boto3
import logging
import os
from datetime import datetime, timezone, timedelta
import httpx
from httpx_aws_auth import AwsSigV4Auth, AwsCredentials 
import ec2Helper
import utilHelper
import pytz
# from errorHandler import ErrorHandler

logger = logging.getLogger()
logger.setLevel(logging.INFO)

appsync = boto3.client('appsync')
eb_client = boto3.client('events')

ENCODING = 'utf-8'

appValue = os.getenv('TAG_APP_VALUE')
appName = os.getenv('APP_NAME') 
envName = os.getenv('ENVIRONMENT_NAME')
endpoint = os.getenv('APPSYNC_URL', None) 
cognito_pool_id = os.getenv('COGNITO_USER_POOL_ID', None)

utl = utilHelper.Utils()
ec2_utils = ec2Helper.Ec2Utils()
utc = pytz.utc
pst = pytz.timezone('US/Pacific')

scheduled_event_bridge_rule = utl.get_ssm_param(f"/{appName}/{envName}/scheduledrule")
logger.info(f"Scheduled EventBridge Rule: {scheduled_event_bridge_rule}")

boto3_session = boto3.Session()
boto3_credentials = boto3_session.get_credentials()

credentials = AwsCredentials(
    access_key=boto3_credentials.access_key,
    secret_key=boto3_credentials.secret_key,
    session_token=boto3_credentials.token,
)

# Create an authenticated client
httpxClient = httpx.Client(
    auth=AwsSigV4Auth(
        credentials=credentials,
        region=boto3_session.region_name,
        service='appsync',
    )
)

putServerMetric = """
mutation PutServerMetric($input: ServerMetricInput!) {
    putServerMetric(input: $input) {
        id
        memStats
        cpuStats
        networkStats
        activeUsers
    }
}
"""

changeServerState = """
  mutation ChangeServerState($input: ServerInfoInput!) {
    changeServerState(input: $input) {
      id
      name
      type
      userEmail
      state
      vCpus
      memSize
      diskSize
      launchTime
      publicIp
      initStatus
      iamStatus
      runningMinutes
    }
}
"""

def send_to_appsync(payload):
    logger.info("------- send_to_appsync")
    try:
        headers={"Content-Type": "application/json"}
        # sending response to AppSync
        response = httpxClient.post(
            endpoint,
            headers=headers,
            json=payload
        )
        logger.info(response.json())
    except Exception as e:
        # ErrorHandler.log_error('NETWORK_ERROR',
        #                      context={'operation': 'send_to_appsync'},
        #                      exception=e, error=str(e))
        logger.error(str(e))
    
def schedule_event_response():
    logger.info("------- schedule_event_response")
    # Check for instances running to update their stats. It can only be a Schedule Event
    instances_running = ec2_utils.list_servers_by_state("running")    

    logger.info(instances_running)

    if instances_running["TotalInstances"] == 0:  
        logger.error("No Instances Found for updating")
        return None

    instances_payload = []
    dt_start_time = datetime.now(tz=timezone.utc) - timedelta(hours=1)
    dt_now = datetime.now(tz=timezone.utc)

    for instance in instances_running["Instances"]:
        instance_info = {
            'id': instance["InstanceId"],
            'memStats': utl.get_metrics_data(instance["InstanceId"], 'MinecraftDashboard', 'mem_usage', 'Percent', 'Average', dt_start_time, dt_now, 60),
            'cpuStats': utl.get_metrics_data(instance["InstanceId"], 'MinecraftDashboard', 'cpu_usage', 'Percent', 'Average', dt_start_time, dt_now, 60),
            'networkStats': utl.get_metrics_data(instance["InstanceId"], 'MinecraftDashboard', 'transmit_bandwidth', 'Bytes/Second', 'Sum', dt_start_time, dt_now, 60),
            'activeUsers': utl.get_metrics_data(instance["InstanceId"], 'MinecraftDashboard', 'user_count', 'Count', 'Maximum', dt_start_time, dt_now, 60)
        }
        instances_payload.append(instance_info)

    return instances_payload

def enable_scheduled_rule():    
    logger.info("------- enable_scheduled_rule")
    evtRule = eb_client.describe_rule(Name=scheduled_event_bridge_rule)
    if evtRule["State"] == "DISABLED":                    
        eb_client.enable_rule(Name=scheduled_event_bridge_rule)
        logger.info("Enabled Evt Bridge Rule")

def disable_scheduled_rule():
    logger.info("------- disable_scheduled_rule")
    # Check for instances running
    instances_running = ec2_utils.list_servers_by_state("running")
    
    if instances_running["TotalInstances"] == 0:  
        logger.error("No Instances running. Disabling Scheduled Event")
        evtRule = eb_client.describe_rule(Name=scheduled_event_bridge_rule)
        if evtRule["State"] == "ENABLED":
            eb_client.disable_rule(Name=scheduled_event_bridge_rule)
            logger.info("Disabled Evt Bridge Rule")

def state_change_response(instance_id):
    logger.info("------- state_change_response: " + instance_id)

    server_info = ec2_utils.list_server_by_id(instance_id)
    instance_info = server_info['Instances'][0]
    ec2Status = ec2_utils.describe_instance_status(instance_id)
    launchTime = instance_info["LaunchTime"]
    if "Association" in instance_info["NetworkInterfaces"][0]:
        publicIp = instance_info["NetworkInterfaces"][0]["Association"]["PublicIp"]
    else:
        publicIp = "none"

    tags = {tag['Key']: tag['Value'] for tag in instance_info["Tags"]}
    userEmail = tags.get("Owner", "minecraft-dashboard@maildrop.cc")
    instanceName = tags.get("Name", "Undefined")

    # Converting to PST as the logs are in PST        
    pstLaunchTime = launchTime.astimezone(pst)

    # Get cached running minutes with timestamp
    runtime_data = ec2_utils.get_cached_running_minutes(instance_id)
    
    # building payload
    input = {
        "id": instance_id,
        "userEmail": userEmail,
        "name": instanceName,
        "type": instance_info["InstanceType"],
        "state": instance_info["State"]["Name"].lower(),
        "initStatus": ec2Status["initStatus"].lower(),
        "iamStatus": ec2Status["iamStatus"].lower(),
        "launchTime": pstLaunchTime.strftime("%m/%d/%Y - %H:%M:%S"),
        "publicIp": publicIp,
        "runningMinutes": runtime_data['minutes'],
        "runningMinutesCacheTimestamp": runtime_data.get('timestamp', '')
    }

    return input
    
def handle_instance_state_change(event):
    """Handle EC2 Instance State-change Notification events."""
    if not scheduled_event_bridge_rule:
        logger.error("Scheduled Event Name not registered")
        return "No Scheduled Event"
    
    instance_id = event['detail']['instance-id']
    state = event['detail']['state']
    
    logger.info("Found InstanceId: " + instance_id + ' at ' + state + ' state')
    
    if state == "running":
        handle_instance_running(instance_id)
    elif state == "stopped":
        handle_instance_stopped()
    
    # Send state change notification
    input_data = state_change_response(instance_id)
    payload = {"query": changeServerState, 'variables': {"input": input_data}}
    send_to_appsync(payload)

def handle_instance_running(instance_id):
    """Handle instance running state setup."""
    enable_scheduled_rule()
    
def handle_instance_stopped():
    """Handle instance stopped state cleanup."""
    disable_scheduled_rule()

def handle_scheduled_event():
    """Handle Scheduled Event notifications."""
    input_data = schedule_event_response()
    
    for metrics in input_data:
        payload = {"query": putServerMetric, 'variables': {"input": metrics}}
        send_to_appsync(payload)

def handler(event, context):
    """Main handler for ec2StateHandler Lambda."""
    try:
        # Check if this is an EventBridge event
        if 'detail-type' not in event:
            # ErrorHandler.log_error('VALIDATION_ERROR',
            #                      context={'operation': 'handler'},
            #                      error='No detail-type found in event')
            logger.error("No detail-type found in event")
            return "No Event Found"
        
        detail_type = event['detail-type']
        logger.info(detail_type)
        
        if detail_type == "EC2 Instance State-change Notification":
            handle_instance_state_change(event)
        elif detail_type == "Scheduled Event":
            handle_scheduled_event()
        else:
            # ErrorHandler.log_error('VALIDATION_ERROR',
            #                      context={'operation': 'handler', 'detail_type': detail_type},
            #                      error=f'Unknown event type: {detail_type}')
            logger.error(f'Unknown event type: {detail_type}')
            return "No Event Found"
        
        return "Event Successfully processed"
        
    except Exception as e:
        # ErrorHandler.log_error('INTERNAL_ERROR',
        #                      context={'operation': 'handler'},
        #                      exception=e, error=str(e))
        logger.error(f"Error processing event: {str(e)}")
        return f"Error processing event: {str(e)}"