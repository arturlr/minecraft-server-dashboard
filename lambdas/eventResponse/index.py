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
    logger.info(f"------- config_server {instance_id}")

    payload = {
        "instanceId": instance_id
    }

    lambda_client.invoke(
        FunctionName=config_server_lambda,
        InvocationType='Event',
        Payload=json.dumps(payload)
    )  

def handler(event, context):     
    
    # Event Brigde
    if 'detail-type' in event:
        logger.info(event['detail-type'])
        if event['detail-type'] == "EC2 Instance State-change Notification":   
            logger.info("Found InstanceId: " + event['detail']['instance-id'] + ' at ' + event['detail']['state'] + ' state')            
            if not scheduled_event_bridge_rule:
                logger.error("Scheduled Event Name not registered")
                return "No Scheduled Event"         
            
            if event['detail']['state'] == "running":
                enable_scheduled_rule()
                config_server(event['detail']['instance-id'])
            elif event['detail']['state'] == "stopped":
                disable_scheduled_rule()

            input = state_change_response(event['detail']['instance-id'])
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