import urllib
import boto3
import logging
import os
import json
import time
from datetime import datetime
import helpers

logger = logging.getLogger()
logger.setLevel(logging.INFO)

utl = helpers.Utils()

ssm = boto3.client('ssm')
appValue = os.getenv('appValue')

def handler(event, context):
    try:
        instanceId = event["instanceId"]

        # ssm_script = ssm.send_command(
        #     InstanceIds=[instanceId],
        #     DocumentName='AWS-RunRemoteScript',
        #     TimeoutSeconds=30,
        #     Parameters={
        #         "sourceType": ["GitHub"],
        #         "sourceInfo": [
        #             "{\"owner\":\"arturlr\", \"repository\": \"minecraft-server-dashboard\", \"path\": \"scripts/adding_cron.sh\", \"getOptions\": \"branch:dev\" }"
        #             ],
        #         "commandLine": ["bash adding_cron.sh"]
        #     }
        # )
        # logger.info(ssm_script)

        
        runCommand = utl.getSsmParam(
            "/amplify/minecraftserverdashboard/" + instanceId + "/runCommand")
        workingDir = utl.getSsmParam(
            "/amplify/minecraftserverdashboard/" + instanceId + "/workingDir")

        if runCommand != None and workingDir != None:
            ssm_rsp = ssm.send_command(
                InstanceIds=[instanceId],
                DocumentName='AWS-RunShellScript',
                TimeoutSeconds=30,
                Parameters={
                    'commands': [runCommand],
                    'workingDirectory': [workingDir]
                }
            )
            logger.info(ssm_rsp)
        else:
            logger.warning("RunCommand or Working Directories are not defined")
            return {'result': 'Failed', 'err': 'RunCommand or Working Directories are not defined'}

        # Save CommandID in a DDb table to submit the result via websocket

        return {'result': 'Succeed', 'id': ssm_rsp["Command"]["CommandId"]}

    except Exception as e:
        logger.error('Something went wrong: ' + str(e))
        return {'result': 'Fail', 'msg': str(e)}
