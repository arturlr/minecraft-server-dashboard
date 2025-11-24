import boto3
import logging
import os
import json
from time import sleep
from datetime import date, datetime, timezone, timedelta
import requests
from requests_aws4auth import AWS4Auth
import ec2Helper
import utilHelper
import DynHelper
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
config_server_lambda = os.getenv('CONFIG_SERVER_LAMBDA_NAME',None)

utl = utilHelper.Utils()
ec2_utils = ec2Helper.Ec2Utils()
dyn = DynHelper.Dyn()
utc = pytz.utc
pst = pytz.timezone('US/Pacific')

scheduled_event_bridge_rule = utl.get_ssm_param(f"/{appName}/{envName}/scheduledrule")
logger.info(f"Scheduled EventBridge Rule: {scheduled_event_bridge_rule}")

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

session = requests.Session()
session.auth = auth
session.close()


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
    response = requests.post(
        endpoint,
        auth=auth,
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
            'networkStats': get_metrics_data(instance["InstanceId"], 'CWAgent', 'net_bytes_sent', 'Bytes', 'Sum', dt_4_four_hours_before, dt_now, 300),
            'activeUsers': get_metrics_data(instance["InstanceId"], 'MinecraftDashboard', 'UserCount', 'None', 'Maximum', dt_4_four_hours_before, dt_now, 300),
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
    elif metric_name == "net_bytes_sent":
        nic_name = utl.retrieve_extension_value(f"/{appName}/{envName}/{instance_id}/nic")
        if nic_name is not None:
            dimensions.append({'Name': 'interface', 'Value': nic_name})
        else:
            logger.warning("No NIC parameter store found for instance: " + instance_id)

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
            'alarmThreshold': 5.0,
            'alarmEvaluationPeriod': 30,
            'runCommand': 'java -Xmx1024M -Xms1024M -jar server.jar nogui',
            'workDir': '/home/ec2-user/minecraft',
            'timezone': 'UTC',
            'isBootstrapped': False,
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
    
    userEmail = 'minecraft-dashboard@maildrop.cc'

    userEmail = tags.get("Owner", userEmail)

    instanceName = "Undefined"
    instanceName = tags.get("Name", instanceName)

    # Converting to PST as the logs are in PST        
    pstLaunchTime = launchTime.astimezone(pst)

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
        "runningMinutes": ec2_utils.get_total_hours_running_per_month(instance_id)
    }

    return input
    
def config_server(instance_id):
    """
    Configure server by checking bootstrap status and running SSM document if needed.
    
    Args:
        instance_id (str): EC2 instance ID
    """
    logger.info(f"------- config_server {instance_id}")
    
    try:
        # Get server configuration from DynamoDB
        config = dyn.get_server_config(instance_id)
        
        # Check if server needs bootstrapping
        is_bootstrapped = config.get('isBootstrapped', False)
        
        if not is_bootstrapped:
            logger.info(f"Server {instance_id} is not bootstrapped, running SSM bootstrap document")
            
            # Get SSM document name from environment or construct it
            ssm_doc_name = os.getenv('BOOTSTRAP_SSM_DOC_NAME')
            if not ssm_doc_name:
                # Construct document name from app name and environment
                ssm_doc_name = f"{appName}-{envName}-BootstrapSSMDoc"
                logger.info(f"Using constructed SSM document name: {ssm_doc_name}")
            
            # Get SSM parameter prefix
            ssm_param_prefix = f"/{appName}/{envName}"
            
            # Send SSM command to bootstrap the instance
            try:
                response = ssm.send_command(
                    InstanceIds=[instance_id],
                    DocumentName=ssm_doc_name,
                    Parameters={
                        'SSMParameterPrefix': [ssm_param_prefix]
                    },
                    Comment=f'Bootstrap server {instance_id}'
                )
                
                command_id = response['Command']['CommandId']
                logger.info(f"SSM bootstrap command sent successfully: CommandId={command_id}, Instance={instance_id}")
                
                # Update DynamoDB to mark as bootstrapped
                # Note: This is optimistic - we're marking it as bootstrapped immediately
                # In production, you might want to wait for SSM command completion
                dyn.update_server_config({
                    'id': instance_id,
                    'isBootstrapped': True
                })
                logger.info(f"Server {instance_id} marked as bootstrapped in DynamoDB")
                
            except Exception as ssm_error:
                logger.error(f"Failed to send SSM bootstrap command for {instance_id}: {str(ssm_error)}", exc_info=True)
                # Don't raise - allow the function to continue even if bootstrap fails
        else:
            logger.info(f"Server {instance_id} is already bootstrapped, skipping SSM document execution")
            
    except Exception as e:
        logger.error(f"Error in config_server for {instance_id}: {str(e)}", exc_info=True)
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
                # Check if server config exists
                config = dyn.get_server_config(instance_id)
                if not config.get('shutdownMethod'):
                    ensure_server_in_dynamodb(instance_id)
                config_server(instance_id)
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