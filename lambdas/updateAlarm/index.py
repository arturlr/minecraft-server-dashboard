import boto3
import logging
import os
import json
import time
import helpers

logger = logging.getLogger()
logger.setLevel(logging.INFO)

botoSession = boto3.session.Session()
awsRegion = botoSession.region_name

cw_client = boto3.client('cloudwatch')

utl = helpers.Utils()
dyn = helpers.Dyn()

def handler(event, context):
    try:   
        instanceId = event["instanceId"]

        logger.info("updateAlarm: " + instanceId)
        instanceInfo = dyn.GetInstanceAttr(instanceId)
        # Default values
        alarmMetric = "CPUUtilization"
        alarmThreshold = "10"

        if instanceInfo != None and instanceInfo['code'] == 200:
            if 'alarmMetric' in instanceInfo['msg']:
                alarmMetric = instanceInfo['msg']['alarmMetric']
                
            if 'alarmThreshold' in instanceInfo['msg']:
                alarmThreshold = instanceInfo['msg']['alarmThreshold']
            
        elif instanceInfo != None and instanceInfo['code'] == 400:
            logger.info("Using Default values for Alarming")

        else:
            logger.error(instanceInfo)
            return False

        dimensions=[]
        statistic="Average"
        namespace="CWAgent"
        dimensions.append({'Name': 'InstanceId','Value': instanceId})
        if alarmMetric == "CPUUtilization":
            alarmMetricName = "cpu_usage_active"        
            dimensions.append({'Name': 'cpu','Value': "cpu-total"})
        elif alarmMetric == "Connections":
            alarmMetricName = "UserCount"
            statistic="Maximum"
            namespace="MinecraftDashboard"
        
        cw_client.put_metric_alarm(
                AlarmName=instanceId + "-" + "minecraft-server",
                ActionsEnabled=True,
                AlarmActions=["arn:aws:automate:" + awsRegion + ":ec2:stop"],
                InsufficientDataActions=[],
                MetricName=alarmMetricName,
                Namespace=namespace,
                Statistic=statistic,
                Dimensions=dimensions,
                Period=60,
                EvaluationPeriods=35,
                DatapointsToAlarm=35,
                Threshold=int(alarmThreshold),
                TreatMissingData="missing",
                ComparisonOperator="LessThanOrEqualToThreshold"   
            )

        logger.info("Alarm configured to " + alarmMetric + " and " + alarmThreshold)
    
    except Exception as e:
        logger.error('Something went wrong: ' + str(e))
        return {'isSuccessful': False, 'msg': str(e)}