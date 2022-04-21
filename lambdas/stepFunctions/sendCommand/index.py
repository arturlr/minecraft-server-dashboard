import urllib
import boto3
import logging
import os
import json
import time
from datetime import datetime
from helpers import utils

logger = logging.getLogger()
logger.setLevel(logging.INFO)

utl = utils.Utils()

ssm = boto3.client('ssm')
appValue = os.getenv('appValue')

def handler(event, context):
    try:   
        instanceId = event["instanceId"]

        runCommand = utl.getSsmParam("/amplify/minecraftserverdashboard/" + instanceId + "/runCommand")
        if runCommand == None:
            runCommand = utl.getSsmParam("/amplify/minecraftserverdashboard/default/runCommand")

        workingDir = utl.getSsmParam("/amplify/minecraftserverdashboard/" + instanceId + "/workingDir")
        if workingDir == "":
            workingDir = utl.getSsmParam("/amplify/minecraftserverdashboard/default/workingDir")
        
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