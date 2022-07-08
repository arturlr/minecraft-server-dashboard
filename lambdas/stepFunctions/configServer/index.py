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
dyn = helpers.Dyn()

ssm = boto3.client('ssm')
ec2 = boto3.client('ec2')
appValue = os.getenv('TAG_APP_VALUE')
ec2InstanceProfileName = os.getenv('EC2_INSTANCE_PROFILE_NAME')
ec2InstanceProfileArn = os.getenv('EC2_INSTANCE_PROFILE_ARN')

def minecraftInit(instance):

    instanceInfo = dyn.GetInstanceAttr(instance)
        
    if 'runCommand' in instanceInfo:
        runCommand = instanceInfo['runCommand']
    else:
        runCommand = None

    if 'workingDir' in instanceInfo:
        workingDir = instanceInfo['workingDir']
    else:
        workingDir = None

    if runCommand != None or workingDir != None:
        ssm_rsp = ssm.send_command(
            InstanceIds=[instance],
            DocumentName='AWS-RunShellScript',
            TimeoutSeconds=30,
            Parameters={
                'commands': [runCommand],
                'workingDirectory': [workingDir]
            }
        )
        logger.info(ssm_rsp)
        return True
    else:
        logger.warning("RunCommand or Working Directories are not defined")
        return False

def iamProfileTask(instance):
    loopCount = 0

    iamProfile = describeIamProfile(instance,"associated")
    if iamProfile != None and iamProfile['Arn'] == ec2InstanceProfileArn:
        logger.info("Instance IAM Profile is already: " + iamProfile['Arn'] )
        return True

    if iamProfile != None:
        logger.info("Disassociating Instance IAM Profile: " + iamProfile['Arn'] )
        disassociateIamProfile(iamProfile)
        while loopCount < 5:
            checkStatusCommand = describeIamProfile(instance,"disassociated")
            time.sleep(10)
            if checkStatusCommand != None:
                loopCount = loopCount + 1
            else:
                attachIamProfile(instance)
                break
        
    else:
        logger.info("Attaching Minecraft Instance IAM Profile")
        attachIamProfile(instance)
        return True
        
    if loopCount > 5:
        logger.warn("Profile timeout during disassociating")
        return False

def describeIamProfile(instance, status):
    descResp = ec2.describe_iam_instance_profile_associations(
        Filters=[
            {
                'Name': 'instance-id',
                'Values': [
                    instance
                ]
            },
        ])
    print(descResp)
    if len(descResp['IamInstanceProfileAssociations']) > 0:        
        for rec in descResp['IamInstanceProfileAssociations']:
            if rec['State'] == status:
               return { "AssociationId": rec['AssociationId'], "Arn": rec['AssociationId']['Arn'] }

    return None

def disassociateIamProfile(id):
     ec2.disassociate_iam_instance_profile(
        AssociationId=id
     )

def attachIamProfile(instance):        
    # Associating the IAM Profile to the Instance
    ec2.associate_iam_instance_profile(
        IamInstanceProfile={
            'Name': ec2InstanceProfileName
        },
        InstanceId=instance
    )

def cwAgentStatusCheck(instance):
    ssmAgentStatus = ssmExecCommands(instance,"AmazonCloudWatch-ManageAgent",{"action": ["status"],"mode": ["ec2"]})
    #logger.info(ssmAgentStatus)

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
                return { "code": 200, "msg": "Agent is already running. Version :" + agentDetailsJson["version"] }
            else:
                logger.info("Agent Status: " + agentDetailsJson["status"] + " - configuration Status: " + agentDetailsJson["configstatus"])
                return { "code": 400, "msg": "Agent is already running. Version :" + agentDetailsJson["version"] }
        else:
            logger.warning(agentDetailsJson)
            return { "code": 500, "msg": "Detailed information not available"}

def cwAgentInstall(instance):
    ssmInstallAgent = ssmExecCommands(instance,"AWS-ConfigureAWSPackage",{"action": ["Install"],"name": ["AmazonCloudWatchAgent"]})
    #logger.info(ssmInstallAgent)

    # AmazonCloudWatch Agent installation 
    jpexpr = parse("$.pluginsDetails[?(@.Name[:] == 'configurePackage')].Output")
    for i in jpexpr.find(ssmInstallAgent):
        agentDetails = i.value
        logger.info(agentDetails)
    # AmazonCloudWatch Agent configuration  
    ssmAgentConfig = ssmExecCommands(instance,"AmazonCloudWatch-ManageAgent",{"action": ["configure"],"mode": ["ec2"],"optionalConfigurationLocation": ["/amplify/minecraftserverdashboard/amazoncloudwatch-linux"],"optionalConfigurationSource": ["ssm"],"optionalRestart": ["yes"]})
    logger.info(ssmAgentConfig)

def scriptExec(instance):
    ssmRunScript = ssmExecCommands(instance,"AWS-RunRemoteScript",{"sourceType": ["GitHub"],"sourceInfo": ["{\"owner\":\"arturlr\", \"repository\": \"minecraft-server-dashboard\", \"path\": \"scripts/adding_cron.sh\", \"getOptions\": \"branch:dev\" }"],"commandLine": ["bash adding_cron.sh"]})
    logger.info(ssmRunScript)

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


def ssmExecCommands(instanceId, docName, params):
    logger.info("ssmExecCommands " + instanceId + " - " + docName)

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

        # attach the IAM Profile to the EC2 Instance
        iamProfileTask(instanceId)
        # Execute minecraft initialization
        minecraftInit(instanceId)

        ## CloudWatch Agent Steps 
        cwAgentStatus = cwAgentStatusCheck(instanceId)
        if cwAgentStatus['code'] != 200:
            cwAgentInstall(instanceId)
            scriptExec(instanceId)
            return { "code": 200, "msg": "CW Agent installed and Script executed"}
        else:
            return cwAgentStatus

    except Exception as e:
        logger.error('Something went wrong: ' + str(e))
        return { "code": 500, "msg": str(e) }