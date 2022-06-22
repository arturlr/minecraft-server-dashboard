import urllib
import boto3
import logging
import os
import json
import time
from datetime import datetime, timezone, timedelta

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ec2_client = boto3.client('ec2')
ssm = boto3.client('ssm')
cw_client = boto3.client('cloudwatch')
appValue = os.getenv('appValue')

session = boto3.session.Session()
awsRegion = session.region_name

class Utils:
    def __init__(self):
        logger.info("Utils initialized")

    def updateAlarm(self, instanceId):
        logger.info("updateAlarm: " + instanceId)

        alarmMetric = self.getSsmParam("/amplify/minecraftserverdashboard/" + instanceId + "/alarmMetric")
        if alarmMetric == None:
            alarmMetric = "CPUUtilization"

        alarmThreshold = self.getSsmParam("/amplify/minecraftserverdashboard/" + instanceId + "/alarmThreshold")
        if alarmThreshold == None:
            alarmThreshold = "10"

        cw_client.put_metric_alarm(
            AlarmName=instanceId + "-" + "minecraft-server",
            ActionsEnabled=True,
            AlarmActions=["arn:aws:automate:" + awsRegion + ":ec2:stop"],
            InsufficientDataActions=[],
            MetricName=alarmMetric,
            Namespace="AWS/EC2",
            Statistic="Average",
            Dimensions=[
                {
                'Name': 'InstanceId',
                'Value': instanceId
                },
            ],
            Period=300,
            EvaluationPeriods=7,
            DatapointsToAlarm=7,
            Threshold=int(alarmThreshold),
            TreatMissingData="missing",
            ComparisonOperator="LessThanOrEqualToThreshold"   
    )
        
    def getSsmParam(self, paramKey, isEncrypted=False):
        try:
            ssmResult = ssm.get_parameter(
                Name=paramKey,
                WithDecryption=isEncrypted
            )

            if (ssmResult["ResponseMetadata"]["HTTPStatusCode"] == 200):
                return ssmResult["Parameter"]["Value"]
            else:
                return None

        except Exception as e:
            logger.warning(str(e) + " for " + paramKey)
            return None

    def getSsmParameters(self, paramKeys, isEncrypted=False):
        try:
            paramArray=paramKeys.split(",")
            print(paramArray)
            ssmResult = ssm.get_parameters(
                Names=paramArray,
                WithDecryption=isEncrypted
            )
            print(ssmResult["Parameters"])
            if (len(ssmResult["Parameters"]) > 0):
                return ssmResult["Parameters"]
            else:
                return None

        except Exception as e:
            logger.warning(str(e) + " for " + paramKeys)
            return None

    def putSsmParam(self, paramKey, paramValue, paramType):
        try:
            ssmResult = ssm.put_parameter(
                Name=paramKey,
                Value=paramValue,
                Type=paramType,
                Overwrite=True
            )

            return ssmResult

        except Exception as e:
            logger.warning(str(e) + " for " + paramKey)
            return None

    def describeInstances(self,name,value):
        if name == 'id':
            response = ec2_client.describe_instances(
                    InstanceIds=[value]
                        )
        elif name == 'email':
            filters = [
                {"Name":"tag:App", "Values":[ appValue ]},
                {"Name":"instance-state-name", "Values":["pending","running","stopping","stopped"]}
                
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
        logger.info("for " + name + ": " + value + " found " + str(len(response["Reservations"])) + " instances")
        if (len(response["Reservations"])) == 0:
            return []
        else:
            return response["Reservations"]
                
    def describeInstanceStatus(self, instanceId):
        statusRsp = ec2_client.describe_instance_status(InstanceIds=[instanceId])

        if (len(statusRsp["InstanceStatuses"])) == 0:
            return { 'instanceStatus': "Fail", 'systemStatus': "Fail" }
        
        instanceStatus = statusRsp["InstanceStatuses"][0]["InstanceStatus"]["Status"]
        systemStatus = statusRsp["InstanceStatuses"][0]["SystemStatus"]["Status"]
            
        return { 'instanceStatus': instanceStatus, 'systemStatus': systemStatus }
