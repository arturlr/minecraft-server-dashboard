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
import helpers
import pytz

logger = logging.getLogger()
logger.setLevel(logging.INFO)

utl = helpers.Utils()
utc = pytz.utc
pst = pytz.timezone('US/Pacific')

ssm = boto3.client('ssm')
appsync = boto3.client('appsync')
ec2_client = boto3.client('ec2')
cw_logs = boto3.client('logs')
cw_client = boto3.client('cloudwatch')
eb_client = boto3.client('events')
cognito_idp = boto3.client('cognito-idp')
ENCODING = 'utf-8'

appValue = os.getenv('TAG_APP_VALUE')
endpoint = os.environ.get('APPSYNC_URL', None)
userPoolId = os.environ.get('USERPOOL_ID', None)

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

headers={"Content-Type": "application/json"}

session = requests.Session()
session.auth = auth

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
      instanceStatus
      systemStatus
      runningMinutes
      groupMembers
    }
}
"""

def _group_exists(instanceId, poolId):
    try:
        grpRsp = cognito_idp.get_group(
                GroupName=instanceId,
                UserPoolId=poolId
            )
            
        return True
        
    except cognito_idp.exceptions.ResourceNotFoundException:
        logger.warning("Group does not exist.")
        return False

def getConnectUsers(instanceId,startTime):
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
                    if len(data['results']) > 0:
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

def getMetricData(instanceId,nameSpace,metricName,unit,statType,startTime,endTime,period):
    cdata = []
    dimensions=[]
    dimensions.append({'Name': 'InstanceId','Value': instanceId})
    if metricName == "cpu_usage_active":
        dimensions.append({'Name': 'cpu','Value': "cpu-total"})
    elif metricName == "net_bytes_sent":
        dimensions.append({'Name': 'interface','Value': "eth0"})

    try:
        rsp = cw_client.get_metric_statistics(
            Namespace=nameSpace,
            MetricName=metricName,
            Dimensions=dimensions,
            StartTime=startTime,
            EndTime=endTime,
            Period=period,
            Statistics=[statType],
            Unit=unit
        )

        if len(rsp["Datapoints"]) == 0:
            logger.warning('No Datapoint for namespace:' + nameSpace + ' - metricName: ' + metricName + ' - InstanceId: ' + instanceId)
            logger.info("startTime: " + startTime.strftime("%Y/%m/%dT%H:%M:%S") + " endTime: " + endTime.strftime("%Y/%m/%dT%H:%M:%S") + " Period: " + str(period))
            return "[]"
        else:
            for rec in rsp["Datapoints"]:
                if metricName == "net_bytes_sent":
                    # converting to Gbit per Second - Divide by 60 to convert from 1 minute to 1 second - Divide by 1024/1024*8 to convert Byte in Mbps.
                    cdata.append({'y': round(rec[statType]/60/1024/1024*8, 2), 'x': rec["Timestamp"].strftime("%Y/%m/%dT%H:%M:%S")})
                else:
                    cdata.append({'y': round(rec[statType], 2), 'x': rec["Timestamp"].strftime("%Y/%m/%dT%H:%M:%S")})

            data_points = sorted(cdata, key=lambda k : k['x'])            
            return json.dumps(data_points)

    except Exception as e:
        logger.error('Something went wrong: ' + str(e))
        return "[]"

def handler(event, context):     
    dt_4_four_hours_before=datetime.utcnow() - timedelta(hours=4)
    dt_now = datetime.utcnow()  
    instancesInfo = []
    # Event Brigde
    if 'detail-type' in event:
        logger.info(event['detail-type'])
        if event['detail-type'] == "EC2 Instance State-change Notification":   
            logger.info("Found InstanceId: " + event['detail']['instance-id'] + ' at ' + event['detail']['state'] + ' state')
            instancesInfo = utl.describeInstances("id",event['detail']['instance-id'])
            scheduledEventBridgeRuleName = utl.getSsmParam("/amplify/minecraftserverdashboard/scheduledrule")
            if scheduledEventBridgeRuleName == None:
                logger.error("Scheduled Event Name not registered")
                return "No Scheduled Event"         

            instancesRunning = utl.describeInstances("state","running")
            if len(instancesRunning) == 0:
                eb_client.disable_rule(Name=scheduledEventBridgeRuleName)
                logger.info("Disabled Evt Bridge Rule")
            else:
                evtRule = eb_client.describe_rule(Name=scheduledEventBridgeRuleName)
                if evtRule["State"] == "DISABLED":                    
                    eb_client.enable_rule(Name=scheduledEventBridgeRuleName)
                    logger.info("Enabled Evt Bridge Rule")

        elif event['detail-type'] == "Scheduled Event":
                # Check for instances running to update their stats. It can only be a Schedule Event
                instancesInfo = utl.describeInstances("state","running")
                if len(instancesInfo) == 0:  
                    logger.error("No Instances Found for updating")
                    return "No Instances Found for updating"


    for instance in instancesInfo:
        instanceId = instance["Instances"][0]["InstanceId"]

        #
        # Group Checking and Creation
        #
        groupMembers = []
        cogGrp = _group_exists(instanceId,userPoolId)
        if cogGrp:
            response = cognito_idp.list_users_in_group(
                UserPoolId=userPoolId,
                GroupName=instanceId
            )            
            if len(response["Users"]) > 0:
                for user in response["Users"]:            
                    for att in user["Attributes"]:
                        if att["Name"] == "email":
                            email = att["Value"]
                        elif att["Name"] == "sub":
                            id = att["Value"]
                        elif att["Name"] == "given_name":
                            given_name = att["Value"]
                        elif att["Name"] == "family_name":
                            family_name = att["Value"]
                    groupMembers.append({
                        "id": id,
                        "email": email,
                        "fullname": given_name + ' ' + family_name                        
                    }) 
            
        ec2Status = utl.describeInstanceStatus(instanceId)
        guid = str(uuid4())
        launchTime = instance["Instances"][0]["LaunchTime"]
        if "Association" in instance["Instances"][0]["NetworkInterfaces"][0]:
            publicIp = instance["Instances"][0]["NetworkInterfaces"][0]["Association"]["PublicIp"]
        else:
            publicIp = "none"

        userEmail = 'minecraft-dashboard@maildrop.cc'
        for tag in instance["Instances"][0]["Tags"]:
            if tag["Key"] == "User":
                userEmail = tag["Value"]

        instanceName = "Undefined"
        for tag in instance["Instances"][0]["Tags"]:
            if tag["Key"] == "Name":
               instanceName = tag["Value"]

        input = { "id": instanceId }

        # Converting to PST as the logs are in PST        
        pstLaunchTime = launchTime.astimezone(pst)
        #activeUsers = getConnectUsers(instanceId, datetime.utcfromtimestamp(pstLaunchTime.timestamp()))

        if event['detail-type'] == "EC2 Instance State-change Notification":
            input["userEmail"] = userEmail
            input["name"] = instanceName
            input["type"] = instance["Instances"][0]["InstanceType"]
            input["state"] = instance["Instances"][0]["State"]["Name"].lower()
            input["systemStatus"] = ec2Status["systemStatus"].lower()
            input["instanceStatus"] = ec2Status["instanceStatus"].lower()
            input["launchTime"] = pstLaunchTime.strftime("%m/%d/%Y - %H:%M:%S")
            input["publicIp"] = publicIp
            input["runningMinutes"] = ""
            input["groupMembers"] = json.dumps(groupMembers)
            payload={"query": changeServerState, 'variables': { "input": input }}

        if event['detail-type'] == "Scheduled Event":
            input['activeUsers'] = getMetricData(instanceId,'MinecraftDashboard','UserCount','None','Maximum',dt_4_four_hours_before,dt_now,300)
            # input["cpuStats"] = getMetricData(instanceId,'AWS/EC2','CPUUtilization','Percent','Average',dt_4_four_hours_before,dt_now,300)
            # input["networkStats"] = getMetricData(instanceId,'AWS/EC2','NetworkOut','Bytes','Average',dt_4_four_hours_before,dt_now,300)
            input["cpuStats"] = getMetricData(instanceId,'CWAgent','cpu_usage_active','Percent','Average',dt_4_four_hours_before,dt_now,300)
            input["networkStats"] = getMetricData(instanceId,'CWAgent','net_bytes_sent','Bytes','Sum',dt_4_four_hours_before,dt_now,300)
            input["memStats"] = getMetricData(instanceId,'CWAgent','mem_used_percent','Percent','Average',dt_4_four_hours_before,dt_now,300)
            payload={"query": putServerMetric, 'variables': { "input": input }}
        
        response = requests.post(
            endpoint,
            auth=auth,
            headers=headers,
            json=payload
        )
        logger.info(response.json())

    return response.json()

