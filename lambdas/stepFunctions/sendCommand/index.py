import urllib
import boto3
import logging
import os
import json
import time
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ec2_client = boto3.client('ec2')
ssm = boto3.client('ssm')
appValue = os.getenv('appValue')

def getSsmParam(paramKey, isEncrypted=False):
    try:
        ssmResult = ssm.get_parameter(
            Name=paramKey,
            WithDecryption=isEncrypted
        )

        if (ssmResult["ResponseMetadata"]["HTTPStatusCode"] == 200):
            return ssmResult["Parameter"]["Value"]
        else:
            return ""

    except Exception as e:
        logger.warning(str(e) + " for " + paramKey)
        return ""

def handler(event, context):
    try:   
        instanceId = event["instanceId"]

        runCommand = getSsmParam("/amplify/minecraftserverdashboard/" + instanceId + "/runCommand")
        if runCommand == "":
            runCommand = getSsmParam("/amplify/minecraftserverdashboard/default/runCommand")

        workingDir = getSsmParam("/amplify/minecraftserverdashboard/" + instanceId + "/workingDir")
        if workingDir == "":
            workingDir = getSsmParam("/amplify/minecraftserverdashboard/default/workingDir")
        
        ssm_rsp = ssm.send_command(
            InstanceIds=[instanceId],
            DocumentName='AWS-RunShellScript',
            TimeoutSeconds=30,
            Parameters={
                'commands': [ runCommand ],
                'workingDirectory': [ workingDir ]
            }
        )
        
        logger.info(ssm_rsp)

        # Save CommandID in a DDb table to submit the result via websocket

        return { 'result': 'Succeed', 'id': ssm_rsp["Command"]["CommandId"] }

    except Exception as e:
        logger.error('Something went wrong: ' + str(e))
        return {'result': 'Fail', 'msg': str(e)}