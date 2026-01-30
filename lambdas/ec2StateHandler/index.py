import boto3
import logging
import os
from datetime import datetime, timezone, timedelta
import httpx
from httpx_aws_auth import AwsSigV4Auth, AwsCredentials 
from botocore.config import Config
import ec2Helper
import utilHelper
import ddbHelper
import pytz
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Configure boto3 clients with timeouts
boto_config = Config(
    connect_timeout=5,
    read_timeout=10,
    retries={'max_attempts': 3, 'mode': 'standard'}
)

eb_client = boto3.client('events', config=boto_config)

appValue = os.getenv('TAG_APP_VALUE')
appName = os.getenv('APP_NAME') 
envName = os.getenv('ENVIRONMENT_NAME')
endpoint = os.getenv('APPSYNC_URL')
cognito_pool_id = os.getenv('COGNITO_USER_POOL_ID', None)

utl = utilHelper.Utils()
ec2_utils = ec2Helper.Ec2Utils()
ddb = ddbHelper.CoreTableDyn()
utc = pytz.utc
pst = pytz.timezone('US/Pacific')

scheduled_event_bridge_rule = utl.get_ssm_param(f"/{appName}/{envName}/scheduledrule")
logger.info(f"Scheduled EventBridge Rule: {scheduled_event_bridge_rule}")

# Connection pool for AppSync client
_appsync_client = None

def get_appsync_client():
    """Get or create AppSync client with connection pooling."""
    global _appsync_client
    if _appsync_client is None:
        session = boto3.Session()
        creds = session.get_credentials()
        _appsync_client = httpx.Client(
            auth=AwsSigV4Auth(
                credentials=AwsCredentials(
                    access_key=creds.access_key,
                    secret_key=creds.secret_key,
                    session_token=creds.token,
                ),
                region=session.region_name,
                service='appsync',
            ),
            timeout=30.0
        )
    return _appsync_client

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
    if not endpoint:
        raise ValueError("APPSYNC_URL environment variable not set")
    
    headers = {"Content-Type": "application/json"}
    client = get_appsync_client()
    try:
        response = client.post(endpoint, headers=headers, json=payload)
        response.raise_for_status()
        logger.info(response.json())
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error sending to AppSync: {e}")
        raise
    except Exception as e:
        logger.error(f"Error sending to AppSync: {e}")
        raise
    
def schedule_event_response():
    logger.info("------- schedule_event_response")
    # Check for instances running to update their stats. It can only be a Schedule Event
    instances_running = ec2_utils.list_servers_by_state("running")    

    logger.info(instances_running)

    if not instances_running or "TotalInstances" not in instances_running or instances_running["TotalInstances"] == 0:  
        logger.error("No Instances Found for updating")
        return None

    instances_payload = []
    dt_start_time = datetime.now(tz=timezone.utc) - timedelta(hours=1)
    dt_now = datetime.now(tz=timezone.utc)

    # TODO: Optimize with CloudWatch get_metric_data batch API to reduce N+1 queries
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

def manage_scheduled_rule(increment=True):
    """Enable or disable scheduled rule based on atomic counter."""
    logger.info(f"------- manage_scheduled_rule (increment={increment})")
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            if increment:
                response = ddb.table.update_item(
                    Key={'PK': 'InstanceCounter', 'SK': 'METADATA'},
                    UpdateExpression='SET #count = if_not_exists(#count, :zero) + :inc',
                    ExpressionAttributeNames={'#count': 'count'},
                    ExpressionAttributeValues={':inc': 1, ':zero': 0},
                    ReturnValues='ALL_OLD'
                )
                previous_count = int(response.get('Attributes', {}).get('count', 0))
                new_count = previous_count + 1
                
                if previous_count == 0:
                    try:
                        eb_client.enable_rule(Name=scheduled_event_bridge_rule)
                        logger.info("Enabled EventBridge Rule (first instance)")
                    except Exception as e:
                        logger.error(f"Failed to enable EventBridge rule: {e}")
                        # Rollback counter increment
                        ddb.table.update_item(
                            Key={'PK': 'InstanceCounter', 'SK': 'METADATA'},
                            UpdateExpression='SET #count = #count - :dec',
                            ExpressionAttributeNames={'#count': 'count'},
                            ExpressionAttributeValues={':dec': 1}
                        )
                        raise
            else:
                response = ddb.table.update_item(
                    Key={'PK': 'InstanceCounter', 'SK': 'METADATA'},
                    UpdateExpression='SET #count = #count - :dec',
                    ConditionExpression='#count > :zero',
                    ExpressionAttributeNames={'#count': 'count'},
                    ExpressionAttributeValues={':dec': 1, ':zero': 0},
                    ReturnValues='ALL_OLD'
                )
                previous_count = int(response['Attributes']['count'])
                new_count = previous_count - 1
                
                if previous_count == 1:
                    try:
                        eb_client.disable_rule(Name=scheduled_event_bridge_rule)
                        logger.info("Disabled EventBridge Rule (last instance)")
                    except Exception as e:
                        logger.error(f"Failed to disable EventBridge rule: {e}")
                        # Rollback counter decrement
                        ddb.table.update_item(
                            Key={'PK': 'InstanceCounter', 'SK': 'METADATA'},
                            UpdateExpression='SET #count = #count + :inc',
                            ExpressionAttributeNames={'#count': 'count'},
                            ExpressionAttributeValues={':inc': 1}
                        )
                        raise
            
            logger.info(f"Instance counter: {previous_count} -> {new_count}")
            break  # Success, exit retry loop
                
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                logger.warning("Counter already at 0, cannot decrement")
                break
            elif attempt < max_retries - 1:
                logger.warning(f"DynamoDB operation failed, retrying ({attempt + 1}/{max_retries})")
                continue
            else:
                raise

def state_change_response(instance_id):
    logger.info("------- state_change_response: " + instance_id)

    server_info = ec2_utils.list_server_by_id(instance_id)
    
    if not server_info.get('Instances'):
        logger.error(f"No instance data for {instance_id}")
        return None
    
    instance_info = server_info['Instances'][0]
    ec2Status = ec2_utils.describe_instance_status(instance_id)
    launchTime = instance_info["LaunchTime"]
    
    publicIp = "none"
    if instance_info.get("NetworkInterfaces") and len(instance_info["NetworkInterfaces"]) > 0:
        if "Association" in instance_info["NetworkInterfaces"][0]:
            publicIp = instance_info["NetworkInterfaces"][0]["Association"]["PublicIp"]

    tags = {tag['Key']: tag['Value'] for tag in instance_info["Tags"]}
    userEmail = tags.get("Owner", "unknown")
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
        manage_scheduled_rule(increment=True)
    elif state == "stopped":
        manage_scheduled_rule(increment=False)
    
    # Send state change notification
    input_data = state_change_response(instance_id)
    if not input_data:
        logger.error(f"Failed to get state change data for {instance_id}")
        return
    
    payload = {"query": changeServerState, 'variables': {"input": input_data}}
    send_to_appsync(payload)

def handle_scheduled_event():
    """Handle Scheduled Event notifications."""
    input_data = schedule_event_response()
    
    if not input_data:
        logger.warning("No running instances found")
        return
    
    for metrics in input_data:
        payload = {"query": putServerMetric, 'variables': {"input": metrics}}
        send_to_appsync(payload)

def handler(event, context):
    """Main handler for ec2StateHandler Lambda."""
    global _appsync_client
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
    finally:
        # Clean up AppSync client connection
        if _appsync_client is not None:
            _appsync_client.close()
            _appsync_client = None