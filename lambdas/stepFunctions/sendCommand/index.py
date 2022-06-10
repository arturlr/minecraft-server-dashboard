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


#aws ssm send-command --document-name "AWS-RunRemoteScript" --instance-ids i-0aef4c52b2acd58a2 \
#--parameters '{"sourceType":["GitHub"],"sourceInfo":["{\"owner\":\"arturlr\", \"repository\": \"minecraft-server-dashboard\", \"path\": \"scripts/adding_cron.sh\", \"getOptions\": \"branch:dev\" }"],"commandLine": ["bash adding_cron.sh"]}'

def handler(event, context):
    try:   
        instanceId = event["instanceId"]
        runCommand = utl.getSsmParam("/amplify/minecraftserverdashboard/" + instanceId + "/runCommand")
        workingDir = utl.getSsmParam("/amplify/minecraftserverdashboard/" + instanceId + "/workingDir")

        if runCommand != None and workingDir != None:
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
        else:
            logger.warning("RunCommand or Working Directories are not defined")
            return { 'result': 'Failed', 'err': 'RunCommand or Working Directories are not defined' }

        # Save CommandID in a DDb table to submit the result via websocket

        return { 'result': 'Succeed', 'id': ssm_rsp["Command"]["CommandId"] }

    except Exception as e:
        logger.error('Something went wrong: ' + str(e))
        return {'result': 'Fail', 'msg': str(e)}