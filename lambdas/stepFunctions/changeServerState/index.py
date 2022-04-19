import urllib
import boto3
import logging
import os
import json
import time
from base64 import b64encode
from datetime import datetime, timezone, timedelta

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ec2_client = boto3.client('ec2')
cw_client = boto3.client('cloudwatch')
appValue = os.getenv('appValue')

session = boto3.session.Session()
awsRegion = session.region_name

def describeInstances(name,value):
    if name == 'id':
         response = ec2_client.describe_instances(
                InstanceIds=[value]
                    )
    elif name == 'email':
        filters = [
            {"Name":"tag:App", "Values":[ appValue ]}
            #{"Name":"tag:User", "Values":[ value ]}
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


def updateAlarm(instanceId):
    logger.info("updateAlarm: " + instanceId )
    cw_client.put_metric_alarm(
        AlarmName=instanceId + "-" + "Minecraft-NetworkUtilization",
        ActionsEnabled=True,
        AlarmActions=["arn:aws:automate:" + awsRegion + ":ec2:stop"],
        InsufficientDataActions=[],
        MetricName="NetworkOut",
        Namespace="AWS/EC2",
        Statistic="Average",
        Dimensions=[
            {
            'Name': 'InstanceId',
            'Value': instanceId
            },
        ],
        Period=300,
        EvaluationPeriods=10,
        DatapointsToAlarm=10,
        Threshold=20000,
        TreatMissingData="missing",
        ComparisonOperator="LessThanOrEqualToThreshold"   
    )

def handler(event, context):
    try:   
        instanceId = event["instanceId"]
        action = event["action"]
        if 'steps' in event:
            steps = event['steps']
        else:
            steps = 0

        instanceInfo = describeInstances('id',instanceId)

        launchTime = instanceInfo[0]["Instances"][0]["LaunchTime"]            
        state = instanceInfo[0]["Instances"][0]["State"]["Name"]

        if action == "start":
            instanceStatus = describeInstanceStatus(instanceId)
            IsInstanceReady = False
            if instanceStatus["instanceStatus"] == "ok" and instanceStatus["systemStatus"] == "ok":
                IsInstanceReady = True

            if (state == "stopped"):
                updateAlarm(instanceId)
                rsp = ec2_client.start_instances(
                    InstanceIds=[ instanceId ]
                )
                # check for Cognito Group for instanceId
                # add group if does not exit with the admin user                

            if steps > 5 :
                logger.error('max steps reached')
                return {'isSuccessful': False, 'err': 'Timeout', 'state': state, 'isInstanceReady': IsInstanceReady,}
            else:
                steps = steps + 1

            return { 
                        'isSuccessful': True, 
                        'action': action,
                        'instanceId': instanceId, 
                        'isInstanceReady': IsInstanceReady,
                        'launchTime': launchTime.strftime("%m/%d/%Y - %H:%M:%S"),
                        'state': state, 
                        'steps': steps
                    }

        elif action == "stop":
            if (state == "running"):
                rsp = ec2_client.stop_instances(
                    InstanceIds=[ instanceId ]
                )
            else:
                logger.error('Stop instance ' + instanceId + ' was not possible as the instance status was ' + state)

        elif action == "restart":
            if (state == "running"):
                rsp = ec2_client.reboot_instances(
                    InstanceIds=[ instanceId ]
                )
            else:
                logger.error('Restart instance ' + instanceId + ' was not possible as the instance status was ' + state)
        
        return { 
                 'isSuccessful': True, 
                 'action': action,
                 'instanceId': instanceId                
                }
            
    except Exception as e:
        logger.error('Something went wrong: ' + str(e))
        return {'isSuccessful': False, 'msg': str(e)}