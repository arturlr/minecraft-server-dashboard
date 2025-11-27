import boto3
import logging
import os
import json
from time import sleep
from datetime import date, datetime, timezone, timedelta
from decimal import Decimal
import httpx
from httpx_aws_auth import AwsSigV4Auth, AwsCredentials 
import ec2Helper
import utilHelper
import DynHelper
import ssmHelper
import pytz

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ssm = boto3.client('ssm')
appsync = boto3.client('appsync')
cw_logs = boto3.client('logs')
cw_client = boto3.client('cloudwatch')
eb_client = boto3.client('events')
lambda_client = boto3.client('lambda')

ENCODING = 'utf-8'

appValue = os.getenv('TAG_APP_VALUE')
appName = os.getenv('APP_NAME') 
envName = os.getenv('ENVIRONMENT_NAME')
endpoint = os.getenv('APPSYNC_URL', None) 
cognito_pool_id = os.getenv('COGNITO_USER_POOL_ID', None)
queue_url = os.getenv('SSM_COMMAND_QUEUE_URL')
bootstrap_doc_name = os.getenv('BOOTSTRAP_SSM_DOC_NAME')

utl = utilHelper.Utils()
ec2_utils = ec2Helper.Ec2Utils()
dyn = DynHelper.Dyn()
ssm_helper = ssmHelper.SSMHelper(queue_url,bootstrap_doc_name)
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
    headers={"Content-Type": "application/json"}
    # sending response to AppSync
    response = httpxClient.post(
        endpoint,
        headers=headers,
        json=payload
    )
    logger.info(response.json())
    
def schedule_event_response():
    logger.info("------- schedule_event_response")
    # Check for instances running to update their stats. It can only be a Schedule Event
    instances_running = ec2_utils.list_servers_by_state("running")    

    logger.info(instances_running)

    if instances_running["TotalInstances"] == 0:  
        logger.error("No Instances Found for updating")
        return None

    instances_payload = []
    dt_4_four_hours_before = datetime.now(tz=timezone.utc) - timedelta(hours=4)
    dt_now = datetime.now(tz=timezone.utc)

    for instance in instances_running["Instances"]:
        instance_info = {
            'id': instance["InstanceId"],
            'memStats': get_metrics_data(instance["InstanceId"], 'CWAgent', 'mem_used_percent', 'Percent', 'Average', dt_4_four_hours_before, dt_now, 300),
            'cpuStats': get_metrics_data(instance["InstanceId"], 'CWAgent', 'cpu_usage_active', 'Percent', 'Average', dt_4_four_hours_before, dt_now, 300),
            'networkStats': get_metrics_data(instance["InstanceId"], 'MinecraftDashboard', 'transmit_bandwidth', 'Bytes/Second', 'Sum', dt_4_four_hours_before, dt_now, 300),
            'activeUsers': get_metrics_data(instance["InstanceId"], 'MinecraftDashboard', 'user_count', 'Count', 'Maximum', dt_4_four_hours_before, dt_now, 300),
            #'alertMsg': get_alert(instance["InstanceId"])
        }
        instances_payload.append(instance_info)

    return instances_payload

def get_metrics_data(instance_id, namespace, metric_name, unit, stat_type, start_time, end_time, period):
    logger.info(f"get_metrics_data: {metric_name} - {instance_id}")

    dimensions = [
        {'Name': 'InstanceId', 'Value': instance_id}
    ]

    if metric_name == "cpu_usage_active":
        dimensions.append({'Name': 'cpu', 'Value': "cpu-total"})

    try:
        response = cw_client.get_metric_statistics(
            Namespace=namespace,
            MetricName=metric_name,
            Dimensions=dimensions,
            StartTime=start_time,
            EndTime=end_time,
            Period=period,
            Statistics=[stat_type],
            Unit=unit
        )

        if not response["Datapoints"]:
            logger.warning(f'No Datapoint for namespace: {metric_name} - InstanceId: {instance_id}')
            return "[]"

        data_points = []
        for datapoint in response["Datapoints"]:
            if metric_name == "net_bytes_sent":
                # Converting to Gbit per Second - Divide by 60 to convert from 1 minute to 1 second - Divide by 1024/1024*8 to convert Byte in Mbps.
                data_points.append({
                    'y': round(datapoint[stat_type] / 60 / 1024 / 1024 * 8, 2),
                    'x': datapoint["Timestamp"].strftime("%Y/%m/%dT%H:%M:%S")
                })
            else:
                data_points.append({
                    'y': round(datapoint[stat_type], 2),
                    'x': datapoint["Timestamp"].strftime("%Y/%m/%dT%H:%M:%S")
                })

        return json.dumps(sorted(data_points, key=lambda x: x['x']))

    except Exception as e:
        logger.error(f'Something went wrong: {str(e)}')
        return "[]"

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

def ensure_server_has_cognito_group(instance_id):
    """
    Ensure Cognito group exists for the server instance.
    Creates group if it doesn't exist and updates DynamoDB flag.
    
    Args:
        instance_id (str): EC2 instance ID
    """
    logger.info(f"------- ensure_server_has_cognito_group: {instance_id}")
    
    try:
        # Import authHelper
        import authHelper
        auth = authHelper.Auth(cognito_pool_id)
        
        # Check if group already exists
        if auth.group_exists(instance_id):
            logger.info(f"Cognito group already exists for {instance_id}")
            
            # Update DynamoDB to mark that group exists (in case flag wasn't set)
            dyn.update_server_config({
                'id': instance_id,
                'hasCognitoGroup': True
            })
            return True
        
        # Group doesn't exist, create it
        logger.info(f"Cognito group does not exist for {instance_id}, creating it now")
        if auth.create_group(instance_id):
            logger.info(f"Cognito group created successfully for {instance_id}")
                        
            # Update DynamoDB to mark that group exists
            dyn.update_server_config({
                'id': instance_id,
                'hasCognitoGroup': True
            })
            return True
        else:
            logger.error(f"Failed to create Cognito group for {instance_id}")
            # Don't update DynamoDB flag since creation failed
            return False
            
    except Exception as e:
        logger.error(f"Error ensuring Cognito group for {instance_id}: {str(e)}", exc_info=True)
        return False

def ensure_server_in_dynamodb(instance_id):
    """
    Ensure server exists in DynamoDB ServersTable with default configuration.
    Creates entry with timestamps if it doesn't exist.
    
    Args:
        instance_id (str): EC2 instance ID
    """
    logger.info(f"------- ensure_server_in_dynamodb: {instance_id}")
    
    try:
        # Get current timestamp in ISO format
        now = datetime.now(timezone.utc).isoformat()
        
        # Create default configuration with timestamps and metadata
        default_config = {
            'id': instance_id,
            'shutdownMethod': 'CPUUtilization',
            'alarmThreshold': Decimal('5.0'),
            'alarmEvaluationPeriod': 30,
            'runCommand': 'java -Xmx1024M -Xms1024M -jar server.jar nogui',
            'workDir': '/home/ec2-user/minecraft',
            'timezone': 'UTC',
            'isBootstrapComplete': False,
            'minecraftVersion': '',
            'latestPatchUpdate': '',
            'createdAt': now,
            'updatedAt': now,
            'autoConfigured': True  # Flag to indicate this was auto-configured
        }
        
        dyn.put_server_config(default_config)
        logger.info(f"Default configuration created for server {instance_id} at {now}")

    except Exception as e:
        logger.error(f"Error ensuring server in DynamoDB: {str(e)}", exc_info=True)

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
    
def queue_bootstrap_server(instance_id):
    """
    Queue bootstrap SSM command for asynchronous execution.
    The SSMCommandProcessor Lambda will handle retries and execution.
    
    Args:
        instance_id (str): EC2 instance ID
    """
    logger.info(f"------- queue_bootstrap_server {instance_id}")
    
    try:        
        # Queue the bootstrap command for asynchronous execution
        result = ssm_helper.queue_bootstrap_command(instance_id)
        
        if result['success']:
            logger.info(f"Bootstrap command queued for {instance_id}: MessageId={result['messageId']}")
        else:
            logger.error(f"Failed to queue bootstrap command for {instance_id}: {result['message']}")

    except Exception as e:
        logger.error(f"Error in bootstrap_server for {instance_id}: {str(e)}", exc_info=True)
        # Don't raise - allow the event handler to continue

def handler(event, context):     
    
    # Event Brigde
    if 'detail-type' in event:
        logger.info(event['detail-type'])
        if event['detail-type'] == "EC2 Instance State-change Notification":   
            logger.info("Found InstanceId: " + event['detail']['instance-id'] + ' at ' + event['detail']['state'] + ' state')            
            if not scheduled_event_bridge_rule:
                logger.error("Scheduled Event Name not registered")
                return "No Scheduled Event"
            
            instance_id = event['detail']['instance-id']
                                
            if event['detail']['state'] == "running":                
                enable_scheduled_rule()
                
                # Ensure server exists in DynamoDB
                config = dyn.get_server_config(instance_id)
                if not config or not config.get('shutdownMethod'):
                    logger.warning(f"Server {instance_id} has not record. Creating one")    
                    ensure_server_in_dynamodb(instance_id)
                    config = dyn.get_server_config(instance_id)
                
                # Ensure Cognito group exists for the server (only if config exists)
                if config and not config.get('hasCognitoGroup'):
                    ensure_server_has_cognito_group(instance_id)
                
                # Check if server needs bootstrapping
                if config and not config.get('isBootstrapComplete')
                    logger.warning(f"Server {instance_id} is not bootstrapped, queueing bootstrap command")            
                    queue_bootstrap_server(instance_id)

            elif event['detail']['state'] == "stopped":
                disable_scheduled_rule()

            input = state_change_response(instance_id)
            payload={"query": changeServerState, 'variables': { "input": input }}

            send_to_appsync(payload)

        elif event['detail-type'] == "Scheduled Event":
            input = schedule_event_response()
            
            for metrics in input:
                payload={"query": putServerMetric, 'variables': { "input": metrics }}
                send_to_appsync(payload)
                   
        else:
            logger.error("No Event Found")
            return "No Event Found"

    return "Event Successful processed"