import boto3
import logging
import os
import json
from time import sleep
from uuid import uuid4
from base64 import b64encode
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
ENCODING = 'utf-8'

appValue = os.getenv('TAG_APP_VALUE')
appName = os.getenv('APP_NAME') 
envName = os.getenv('ENVIRONMENT_NAME')
endpoint = os.environ.get('APPSYNC_URL', None) 
cognito_pool_id = os.environ.get('COGNITO_USER_POOL_ID', None)

utl = utilHelper.Utils()
ec2_utils = ec2Helper.Ec2Utils()
utc = pytz.utc
pst = pytz.timezone('US/Pacific')

scheduled_event_bridge_rule = utl.get_ssm_param(appName + "/" + envName + "/" + "scheduledrule")

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

queryString="""
fields @message  
| parse @message ": * joined the game" as @userjoin
| parse @message ": * left the game" as @userleft
| parse @message "logged in with entity id *" as @userlogged
| stats count(@userjoin) as userjoin, count(@userleft) as userleft, count(@userlogged) as userlogged by bin(5m) as t
"""

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
    
def get_connect_minecraft_users(instanceId,startTime):
    try:
        queryRsp = cw_logs.start_query(
            logGroupName='/minecraft/serverlog/' + instanceId,
            startTime=int(round(startTime.timestamp())),
            endTime=int(round(datetime.now().timestamp())),
            queryString=queryString
        )

        if 'queryId' in queryRsp:
            timeCount = 0
            while timeCount < 4:
                data = cw_logs.get_query_results(
                    queryId=queryRsp['queryId']
                )
                dtY = 0
                dtX = ""
                cdata = []
                if data['status'] == 'Complete':
                    if data['results']:
                        for rec in data['results']:
                            for dt in rec:
                                if dt['field'] == 'bin(5m)':
                                    dtX = dt['value']
                                    continue
                                elif dt['field'] == 't':
                                    dtY = dt['value']
                            cdata.append({'y':dtY, 'x':dtX})
                        data_points = sorted(cdata, key=lambda k : k['x'])
                        print(data_points)                    
                        return data_points
                    else:
                        return "[]"
                elif data['status'] == 'Scheduled' or data['status'] == 'Running':
                    sleep(5)
                    timeCount = timeCount + 1
                    continue
                elif data['status'] == 'Failed':
                    raise Exception("Query status: Failed")                    
                else:
                    sleep(5)
                    timeCount = timeCount + 1

            if timeCount >= 4:
                raise Exception("Query status: Timeout")
            else:
                logger.error("start_query: No Data.")
                return "[]"


    except Exception as e:
        logger.error("start_query: " + str(e) + " occurred.")
        return "[]"
    
def send_to_appsync(payload):
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

    # Check for instances running to update their stats. It can only be a Schedule Event
    instances_running = ec2_utils.list_servers_by_state("running")
    
    if not instances_running["Instances"]:  
        logger.error("No Instances Found for updating")
        eb_client.disable_rule(Name=scheduled_event_bridge_rule)
        logger.info("Disabled Evt Bridge Rule")
        return "No Instances Found for updating"

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
        dimensions.append({'Name': 'interface', 'Value': 'nic'})

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
    evtRule = eb_client.describe_rule(Name=scheduled_event_bridge_rule)
    if evtRule["State"] == "DISABLED":                    
        eb_client.enable_rule(Name=scheduled_event_bridge_rule)
        logger.info("Enabled Evt Bridge Rule")

def state_change_response(instance_id):

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
    

def handler(event, context):     
    
    # Event Brigde
    if 'detail-type' in event:
        logger.info(event['detail-type'])
        if event['detail-type'] == "EC2 Instance State-change Notification":   
            logger.info("Found InstanceId: " + event['detail']['instance-id'] + ' at ' + event['detail']['state'] + ' state')            
            if not scheduled_event_bridge_rule:
                logger.error("Scheduled Event Name not registered")
                return "No Scheduled Event"         
            
            if event['detail']['state'] == "running" or event['detail']['state'] == "pending":
                enable_scheduled_rule()

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