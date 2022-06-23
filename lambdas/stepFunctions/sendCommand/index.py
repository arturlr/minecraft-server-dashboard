import urllib
import boto3
import logging
import os
import json
import time
from datetime import datetime
from jsonpath_ng.ext import parse
import helpers

logger = logging.getLogger()
logger.setLevel(logging.INFO)

utl = helpers.Utils()

ssm = boto3.client('ssm')
appValue = os.getenv('TAG_APP_VALUE')

def sendCommand(instance, param, docName):
    
    ssm_rsp = ssm.send_command(
                InstanceIds=[instance],
                DocumentName=docName,
                TimeoutSeconds=30,
                Parameters=param
            )

    logger.info("sendCommand " + instance + " - " + ssm_rsp["Command"]["Status"])
    return { "CommandId": ssm_rsp["Command"]["CommandId"], "Status": ssm_rsp["Command"]["Status"] }


def listCommand(instance, commandId):

    ssm_rsp = ssm.list_commands(
            CommandId=commandId,
            InstanceId=instance,
    )

    logger.info("listCommand " + instance + " - " + ssm_rsp["Commands"][0]["Status"])
    return { "Status": ssm_rsp["Commands"][0]["Status"] }


def getCommandDetails(instance, commandId):

    ssm_rsp = ssm.list_command_invocations(
            CommandId=commandId,
            InstanceId=instance,
            Details=True
    )

    if 'CommandPlugins' in  ssm_rsp["CommandInvocations"][0]:
        pluginsDetails = ssm_rsp["CommandInvocations"][0]["CommandPlugins"]
       
    logger.info("getCommandDetails " + instance + " - " + ssm_rsp["CommandInvocations"][0]["Status"])
    return { "Status": ssm_rsp["CommandInvocations"][0]["Status"], "pluginsDetails": pluginsDetails }


def ssmAgentCommands(instanceId, docName, params):
    logger.info("ssmAgentCommands " + instanceId + " - " + docName)

    loopCount = 0

    command = sendCommand(instanceId, params, docName)
    
    while loopCount < 5:
        checkStatusCommand = listCommand(instanceId, command["CommandId"])
        time.sleep(5)
        if checkStatusCommand["Status"] != "Success" and checkStatusCommand["Status"] != "Failed":
            loopCount = loopCount + 1
        else:
            loopCount = 0
            break

    # Something went wrong
    if loopCount > 0:
        logger.error(checkStatusCommand)
        return None

    getStatusDetails = getCommandDetails(instanceId, command["CommandId"])
    return getStatusDetails

def handler(event, context):
    try:
        instanceId = event["instanceId"]
        
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


        ## CloudWatch Agent Steps 

        ssmAgentStatus = ssmAgentCommands(instanceId,"AmazonCloudWatch-ManageAgent",{"action": ["status"],"mode": ["ec2"]})
        logger.info(ssmAgentStatus)

        # Checking Agent Status if Success. Failed messages occurs when the CloudWatch Agent is not installed. 
        if ssmAgentStatus["Status"] == "Success":
            agentDetails=""
            jpexpr = parse("$.pluginsDetails[?(@.Name[:] == 'ControlCloudWatchAgentLinux')].Output")
            for i in jpexpr.find(ssmAgentStatus):
                agentDetails = i.value
                
            if len(agentDetails) > 5:
                agentDetailsJson = json.loads(agentDetails)
                if agentDetailsJson["status"] == "running": 
                    logger.warning("Agent is already running. Version :" + agentDetailsJson["version"])
                    return { "msg": "Agent is already running. Version :" + agentDetailsJson["version"] }
                else:
                    logger.info("Agent Status: " + agentDetailsJson["status"] + " - configuration Status: " + agentDetailsJson["configstatus"])
            else:
                logger.warning(agentDetailsJson)
                return { "msg": "Detailed informatio not available"}
        
        if ssmAgentStatus != None:
            ssmInstallAgent = ssmAgentCommands(instanceId,"AWS-ConfigureAWSPackage",{"action": ["Install"],"name": ["AmazonCloudWatchAgent"]})
            logger.info(ssmInstallAgent)

            # Checking Agent installation 
            jpexpr = parse("$.pluginsDetails[?(@.Name[:] == 'configurePackage')].Output")
            for i in jpexpr.find(ssmInstallAgent):
                agentDetails = i.value
                print(agentDetails)
            
        if ssmInstallAgent != None and ssmAgentStatus != None: 
            ssmRunScript = ssmAgentCommands(instanceId,"AWS-RunRemoteScript",{"sourceType": ["GitHub"],"sourceInfo": ["{\"owner\":\"arturlr\", \"repository\": \"minecraft-server-dashboard\", \"path\": \"scripts/adding_cron.sh\", \"getOptions\": \"branch:dev\" }"],"commandLine": ["bash adding_cron.sh"]})
            logger.info(ssmRunScript)
            
        if ssmRunScript != None and ssmInstallAgent != None and ssmAgentStatus != None: 
            ssmAgentConfig = ssmAgentCommands(instanceId,"AmazonCloudWatch-ManageAgent",{"action": ["configure"],"mode": ["ec2"],"optionalConfigurationLocation": ["/amplify/minecraftserverdashboard/amazoncloudwatch-linux"],"optionalConfigurationSource": ["ssm"],"optionalRestart": ["yes"]})
            logger.info(ssmAgentConfig)

        return { "msg": "CloudWatch Agent configured"}

    except Exception as e:
        logger.error('Something went wrong: ' + str(e))
        return str(e)