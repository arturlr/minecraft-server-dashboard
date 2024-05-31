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
appName = os.getenv('APP_NAME') 

def get_nic_information(instance):
    logger.info(instance + "- get_nic_information")

    ssm_rsp = ssm.send_command(
            InstanceIds=[instance],
            DocumentName='AWS-RunShellScript',
            TimeoutSeconds=30,
            Parameters={
                'commands':[
                     "NIC=$(ifconfig -a | grep UP,BROADCAST | awk '{print substr($1, 1, length($1)-1)}');aws ssm put-parameter --name '/amplify/minecraftserverdashboard/" + instance + "/nic' --type 'String' --value $NIC"
                ]
            },
        )    
    resp = check_execution_loop(instance,ssm_rsp["Command"]["CommandId"])
    logger.info(resp)   

def minecraft_init(instance):
    logger.info(instance + " - minecraft_init")
    instanceInfo = dyn.GetInstanceAttr(instance)
    logger.info(instanceInfo)

    if instanceInfo['code'] != 200:
        logger.warning("Instance data does not exist")
        return False
    
    if 'runCommand' in instanceInfo['msg'] and 'workingDir' in instanceInfo['msg']:                    
        script = os.path.join(instanceInfo['msg']['workingDir'],instanceInfo['msg']['runCommand'])
        #script = instanceInfo['msg']['runCommand']     

        ssm_rsp = ssm.send_command(
            InstanceIds=[instance],
            DocumentName='AWS-RunShellScript',
            TimeoutSeconds=30,
            Parameters={
                'commands':[
                     script
                ],                 
                'workingDirectory':[
                    instanceInfo['msg']['workingDir']
                ],
            },
        )    
        logger.info(ssm_rsp)                    

    else:
        logger.warning("RunCommand or Working Directories are not defined")
        return False

def cw_agent_status_check(instance):
    logger.info(instance + " - cw_agent_status_check")
    ssmAgentStatus = ssm_exec_commands(instance,"AmazonCloudWatch-ManageAgent",{"action": ["status"],"mode": ["ec2"]})
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
                logger.info("Agent is already running. Version :" + agentDetailsJson["version"])
                # AmazonCloudWatch Agent configuration  
                logger.info("Configuring agent")
                ssmAgentConfig = ssm_exec_commands(instance,"AmazonCloudWatch-ManageAgent",{"action": ["configure"],"mode": ["ec2"],"optionalConfigurationLocation": ["/amplify/minecraftserverdashboard/amazoncloudwatch-linux"],"optionalConfigurationSource": ["ssm"],"optionalRestart": ["yes"]})
                logger.info(ssmAgentConfig)
                return { "code": 200, "msg": "Agent is already running. Version :" + agentDetailsJson["version"] }
            else:
                logger.info("Agent Status: " + agentDetailsJson["status"] + " - configuration Status: " + agentDetailsJson["configstatus"])
                return { "code": 400, "msg":"Agent Status: " + agentDetailsJson["status"] + " - configuration Status: " + agentDetailsJson["configstatus"] }
        else:
            logger.warning(agentDetailsJson)
            return { "code": 500, "msg": "Detailed information not available"}
    else:
        return { "code": 500, "msg": "Failed" }

def cw_agent_install(instance):
    ssmInstallAgent = ssm_exec_commands(instance,"AWS-ConfigureAWSPackage",{"action": ["Install"],"name": ["AmazonCloudWatchAgent"]})
    #logger.info(ssmInstallAgent)

    # Checking Agent Status if Success. Failed messages occurs when the CloudWatch Agent is not installed. 
    if ssmInstallAgent["Status"] == "Success":
        # AmazonCloudWatch Agent installation 
        jpexpr = parse("$.pluginsDetails[?(@.Name[:] == 'configurePackage')].Output")
        for i in jpexpr.find(ssmInstallAgent):
            agentDetails = i.value
            logger.info(agentDetails)
        # AmazonCloudWatch Agent configuration 
        logger.info("Configuring agent") 
        ssmAgentConfig = ssm_exec_commands(instance,"AmazonCloudWatch-ManageAgent",{"action": ["configure"],"mode": ["ec2"],"optionalConfigurationLocation": ["/amplify/minecraftserverdashboard/amazoncloudwatch-linux"],"optionalConfigurationSource": ["ssm"],"optionalRestart": ["yes"]})
        logger.info(ssmAgentConfig)

def scriptExec(instance):
    ssmRunScript = ssm_exec_commands(instance,"AWS-RunRemoteScript",{"sourceType": ["GitHub"],"sourceInfo": ["{\"owner\":\"arturlr\", \"repository\": \"minecraft-server-dashboard\", \"path\": \"scripts/adding_cron.sh\", \"getOptions\": \"branch:dev\" }"],"commandLine": ["bash adding_cron.sh"]})
    logger.info(ssmRunScript)

def send_command(instance, param, docName):    
    ssm_rsp = ssm.send_command(
                InstanceIds=[instance],
                DocumentName=docName,
                TimeoutSeconds=30,
                Parameters=param
            )

    # logger.info("send_command " + instance + " - " + ssm_rsp["Command"]["Status"])
    return { "CommandId": ssm_rsp["Command"]["CommandId"], "Status": ssm_rsp["Command"]["Status"] }

def listCommand(instance, commandId):
    ssm_rsp = ssm.list_commands(
            CommandId=commandId,
            InstanceId=instance,
    )

    logger.info("listCommand " + instance + " - " + ssm_rsp["Commands"][0]["Status"])
    return { "Status": ssm_rsp["Commands"][0]["Status"] }

def get_command_details(instance, commandId):
    ssm_rsp = ssm.list_command_invocations(
            CommandId=commandId,
            InstanceId=instance,
            Details=True
    )

    if 'CommandPlugins' in  ssm_rsp["CommandInvocations"][0]:
        pluginsDetails = ssm_rsp["CommandInvocations"][0]["CommandPlugins"]
       
    logger.info("getCommandDetails " + instance + " - " + ssm_rsp["CommandInvocations"][0]["Status"])
    return { "Status": ssm_rsp["CommandInvocations"][0]["Status"], "pluginsDetails": pluginsDetails }

def check_execution_loop(instanceId, commandId, sleepTime=5):

    loopCount = 0
    
    while True:
        checkStatusCommand = listCommand(instanceId, commandId)
        logger.info(instanceId + " - " + commandId + " - " + checkStatusCommand["Status"])
        if checkStatusCommand["Status"] == "Success":
            getStatusDetails = get_command_details(instanceId, commandId)
            return getStatusDetails
        elif checkStatusCommand["Status"] == "Failed":
            return "Failed"
        elif loopCount > 5:
            logger.error("Timeout - Cancelling the Command")
            logger.error(checkStatusCommand)
            ssm.cancel_command(
                CommandId=commandId,
                InstanceIds=[instanceId]
            )
            return "Cancelled"
        else:
            loopCount = loopCount + 1
            time.sleep(sleepTime)


def ssm_exec_commands(instanceId, docName, params):
    logger.info("ssm_exec_commands " + instanceId + " - " + docName)

    command = send_command(instanceId, params, docName)
    response = check_execution_loop(instanceId,command["CommandId"])

    return response

def handler(event, context):
    try:
        instanceId = event["instanceId"]

        # Execute minecraft initialization
        minecraft_init(instanceId)

        # Nic Value
        get_nic_information(instanceId)

        ## CloudWatch Agent Steps 
        cwAgentStatus = cw_agent_status_check(instanceId)
        if cwAgentStatus['code'] != 200:
            cw_agent_install(instanceId)
            scriptExec(instanceId)
            return { "code": 200, "msg": "CW Agent installed and Script executed"}
        else:
            return cwAgentStatus

    except Exception as e:
        logger.error('Something went wrong: ' + str(e))
        return { "code": 500, "msg": str(e) }