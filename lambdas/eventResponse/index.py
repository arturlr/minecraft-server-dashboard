from nis import match
import urllib
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

logger = logging.getLogger()
logger.setLevel(logging.INFO)

appsync = boto3.client('appsync')
ec2_client = boto3.client('ec2')
cw_client = boto3.client('cloudwatch')
eb_client = boto3.client('events')
ENCODING = 'utf-8'

scheduledEventBridgeRuleName=os.environ.get('EVTBRIDGE_RULE_NAME', None)

appValue = os.getenv('appValue')

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
endpoint = os.environ.get('APPSYNC_URL', None)
headers={"Content-Type": "application/json"}

session = requests.Session()
session.auth = auth

dt_1st_day_of_the_month=date.today().replace(day=1)
dt_14_days_past_today=datetime.utcnow() - timedelta(days=14)
dt_4_four_hours_before=datetime.utcnow() - timedelta(hours=4)
dt_now = datetime.utcnow()

putServerMetric = """
mutation PutServerMetric($input: ServerMetricInput!) {
    putServerMetric(input: $input) {
        id
        monthlyUsage
        dailyUsage
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
      instanceStatus
      systemStatus
    }
}
"""

def describeInstances(name,value):
    if name == 'id':
         response = ec2_client.describe_instances(
                InstanceIds=[value]
                    )
    elif name == 'email':
        filters = [
            {"Name":"tag:App", "Values":[ appValue ]}
            # {"Name":"tag:User", "Values":[ value ]}
        ]
        response =  ec2_client.describe_instances(
            Filters=filters            
        )
    elif name == 'state':
        filters = [
            {"Name":"tag:App", "Values":[ appValue ]},
            {"Name":"instance-state-name", "Values":[ value ]}
        ]
        response =  ec2_client.describe_instances(
            Filters=filters            
        )

    # checking response
    if (len(response["Reservations"])) == 0:
        logger.error("No Instances Found")
        return []
    else:
        return response["Reservations"]
            

def describeInstanceStatus(instanceId):
    statusRsp = ec2_client.describe_instance_status(InstanceIds=[instanceId])

    if (len(statusRsp["InstanceStatuses"])) == 0:
        return { 'instanceStatus': "Fail", 'systemStatus': "Fail" }
    
    instanceStatus = statusRsp["InstanceStatuses"][0]["InstanceStatus"]["Status"]
    systemStatus = statusRsp["InstanceStatuses"][0]["SystemStatus"]["Status"]
        
    return { 'instanceStatus': instanceStatus, 'systemStatus': systemStatus }



def getMetricData(instanceId,metricName,unit,statType,startTime,EndTime,period):
    cdata = []
    four_hours_before=datetime.utcnow() - timedelta(hours=4)

    rsp = cw_client.get_metric_statistics(
        Namespace="AWS/EC2",
        MetricName=metricName,
        Dimensions=[
            {
            'Name': 'InstanceId',
            'Value': instanceId
            }
        ],
        StartTime=startTime,
        EndTime=EndTime,
        Period=period,
        Statistics=[statType],
        Unit=unit
    )

    if len(rsp["Datapoints"]) == 0:
        return None
    else:
        for rec in rsp["Datapoints"]:
            if metricName == "NetworkOut":
                cdata.append({'y': round(rec[statType]/10000, 2), 'x': rec["Timestamp"].strftime("%Y/%m/%dT%H:%M:%S")})
            else:
                cdata.append({'y': round(rec[statType], 2), 'x': rec["Timestamp"].strftime("%Y/%m/%dT%H:%M:%S")})

        data_points = sorted(cdata, key=lambda k : k['x'])
        
        return json.dumps(data_points)


def handler(event, context):        

    instancesInfo = []
    
    # Event Brigde
    if 'detail' in event:    
        logger.info(event['detail-type'])    
        if 'instance-id' in event['detail']:
            logger.info("Found InstanceId: " + event['detail']['instance-id'] + ' at ' + event['detail']['state'] + ' state')
            instancesInfo = describeInstances("id",event['detail']['instance-id'])
        elif 'detail-type' in event:
            if event['detail-type'] == "Scheduled Event":
                instancesInfo = describeInstances("state","running")

    if 'detail-type' in event:
        if event['detail-type'] == "EC2 Instance State-change Notification":            
            instancesRunning = describeInstances("state","running")
            if len(instancesRunning) == 0:
                eb_client.disable_rule(Name=scheduledEventBridgeRuleName)
                logger.info("Disabled Evt Bridge Rule")
            else:
                evtRule = eb_client.describe_rule(Name=scheduledEventBridgeRuleName)
                if evtRule["State"] == "DISABLED":                    
                    eb_client.enable_rule(Name=scheduledEventBridgeRuleName)
                    logger.info("Enabled Evt Bridge Rule")

    if len(instancesInfo) == 0:        
        logger.error("No Instances Found")
        return "No Instances Found"

    for instance in instancesInfo:
        instanceId = instance["Instances"][0]["InstanceId"]
        
        ec2Status = describeInstanceStatus(instanceId)
        guid = str(uuid4())

        launchTime = instance["Instances"][0]["LaunchTime"]
        if "Association" in instance["Instances"][0]["NetworkInterfaces"][0]:
            publicIp = instance["Instances"][0]["NetworkInterfaces"][0]["Association"]["PublicIp"]
        else:
            publicIp = "none"

        userEmail = 'unknown'
        for tag in instance["Instances"][0]["Tags"]:
            if tag["Key"] == "User":
                userEmail = tag["Value"]

        instanceName = "Undefined"
        for tag in instance["Instances"][0]["Tags"]:
            if tag["Key"] == "Name":
               instanceName = tag["Value"]

        input = { "id": instanceId }

        if event['detail-type'] == "EC2 Instance State-change Notification":
            input["userEmail"] = userEmail
            input["name"] = instanceName
            input["state"] = instance["Instances"][0]["State"]["Name"].lower()
            input["systemStatus"] = ec2Status["systemStatus"].lower()
            input["instanceStatus"] = ec2Status["instanceStatus"].lower()
            input["launchTime"] = launchTime.strftime("%m/%d/%Y - %H:%M:%S")
            input["publicIp"] = publicIp
            payload={"query": changeServerState, 'variables': { "input": input }}

        if event['detail-type'] == "Scheduled Event":
            input["cpuStats"] = getMetricData(instanceId,'CPUUtilization','Percent','Average',dt_4_four_hours_before,dt_now,300)
            input["networkStats"] = getMetricData(instanceId,'NetworkOut','Bytes','Average',dt_4_four_hours_before,dt_now,300)
            payload={"query": putServerMetric, 'variables': { "input": input }}

                
        response = requests.post(
            endpoint,
            auth=auth,
            headers=headers,
            json=payload
        )

    return response.json()

