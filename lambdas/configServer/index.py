import boto3
import botocore
from typing import Optional, Dict, Any
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
ec2 = boto3.client('ec2')
appValue = os.getenv('TAG_APP_VALUE')
appName = os.getenv('APP_NAME') 

def packages_installation(instance_id):
    logger.info("------- packages_installation :" + instance_id)

    parameters={
        'commands':[
            """#!/bin/bash
            APT=$(which apt)
            YUM=$(which yum)
            case $APT in /usr*)
            sudo apt-get -y install jq zip unzip net-tools 
            esac
            case $YUM in /usr*)
            sudo yum -y install jq zip unzip
            esac
            if [ ! -f /usr/share/collectd/types.db ]; then
                sudo mkdir -p /usr/share/collectd
                sudo touch /usr/share/collectd/types.db
            fi
            if ! command -v aws >/dev/null 2>&1; then
                curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
                unzip awscliv2.zip
                sudo ./aws/install
                echo "AWS CLI installed successfully"
            else
                echo "AWS CLI is already installed"
            fi"""
        ]
    }
    
     # Installing packages
    ssm_rsp = ssm_exec_commands(
        instance_id,
        "AWS-RunShellScript",
        parameters
    )

    logger.info(ssm_rsp)

def config_cron(instance_id):
    logger.info("------- config_cron : " + instance_id)

    parameters={
        'commands':[
            """#!/bin/bash
            # check if port_count.sh exists.
            if [ ! -f /usr/local/port_count.sh ]; then

            # Get instance metadata
            INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
            REGION=$(curl -s http://169.254.169.254/latest/meta-data/local-hostname | cut -d . -f 2)

            # Count established connections on port 25565
            PORT_COUNT=$(netstat -an | grep ESTABLISHED | grep ':25565' | wc -l)

            # Create the script file
            echo "#!/bin/bash" > /usr/local/port_count.sh
            echo "INSTANCE_ID=\"$INSTANCE_ID\"" >> /usr/local/port_count.sh
            echo "PORT_COUNT=\$(netstat -an | grep ESTABLISHED | grep ':25565' | wc -l)" >> /usr/local/port_count.sh
            echo "REGION=\"$REGION\"" >> /usr/local/port_count.sh
            echo "aws cloudwatch put-metric-data --metric-name UserCount --dimensions InstanceId=\$INSTANCE_ID --namespace 'MinecraftDashboard' --value \$PORT_COUNT --region \$REGION" >> /usr/local/port_count.sh

            # Make the script executable
            chmod +x /usr/local/port_count.sh

            # Schedule the script to run every minute
            (sudo crontab -l 2>/dev/null; echo "* * * * * /usr/local/port_count.sh >/dev/null 2>&1") | crontab -         
            fi      
            """
        ]
    }

     # Installing packages
    ssm_rsp = ssm_exec_commands(
        instance_id,
        "AWS-RunShellScript",
        parameters
    )

    logger.info(ssm_rsp)

def get_nic_information(instance_id):
    logger.info("------- get_nic_information : " + instance_id)

    parameters={
        'commands':[
            "NIC=$(ip route get 1.1.1.1 | awk '{print $5; exit}');aws ssm put-parameter --name '/minecraftserverdashboard/" + instance_id + "/nic' --type 'String' --value $NIC --overwrite"
        ]
    }

    # getting the NIC information
    ssm_rsp = ssm_exec_commands(
        instance_id,
        'AWS-RunShellScript',
        parameters
    )    

    logger.info(ssm_rsp)
 

def minecraft_init(instance_id):
    logger.info(f"------- minecraft_init: {instance_id}")
    instance_attributes = utl.get_instance_attributes(instance_id)

    if not instance_attributes:
        logger.warning("Instance data does not exist")
        return False
    
    if 'runCommand' not in instance_attributes:
        logger.warning("RunCommand or Working Directories are not defined")
        return False
    
    run_command = instance_attributes["runCommand"]
    work_dir = instance_attributes["workDir"]
    
    parameters = {
        'commands':[run_command],                 
        'workingDirectory':[work_dir],
    }

    ssm_rsp = ssm_exec_commands(instance_id, "AWS-RunShellScript", parameters)
    logger.info(ssm_rsp)                    

def cw_agent_status_check(instance_id):
    logger.info("------- cw_agent_status_check : " + instance_id)
    ssm_agent_status = ssm_exec_commands(instance_id,"AmazonCloudWatch-ManageAgent",{"action": ["status"],"mode": ["ec2"]})
    logger.info(ssm_agent_status)
    agent_details=None

    # Checking Agent Status if Success. Failed messages occurs when the CloudWatch Agent is not installed. 
    if ssm_agent_status["Status"] == "Success":
        
        jpexpr = parse("$.pluginsDetails[?(@.Name[:] == 'ControlCloudWatchAgentLinux')].Output")
        for i in jpexpr.find(ssm_agent_status):
            agent_details = i.value
            
        if agent_details:
            agent_details_json = json.loads(agent_details)
            if agent_details_json["status"] == "running": 
                logger.info("Agent is already running. Version :" + agent_details_json["version"])
                logger.info("Agent Status: " + agent_details_json["status"] + " - configuration Status: " + agent_details_json["configstatus"])
                # call cw_agent_config
        else:
            return { "code": 500, "msg": "Detailed information not available"}
    else:
        return { "code": 500, "msg": "Failed" }

def cw_agent_install(instance_id):
    logger.info("------- cw_agent_install : " + instance_id)

    ssm_install_agent = ssm_exec_commands(instance_id,"AWS-ConfigureAWSPackage",
        {'action': ['Install'],
            'installationType': ['Uninstall and reinstall'],
            'name': ['AmazonCloudWatchAgent']
        })
    logger.info(ssm_install_agent)

    # Checking Agent Status if Success. Failed messages occurs when the CloudWatch Agent is not installed. 
    if ssm_install_agent["Status"] == "Success":
        # AmazonCloudWatch Agent installation 
        jpexpr = parse("$.pluginsDetails[?(@.Name[:] == 'configurePackage')].Output")
        for i in jpexpr.find(ssm_install_agent):
            agent_details = i.value
            logger.info(agent_details)
        # AmazonCloudWatch Agent configuration 
        cw_agent_config(instance_id)

def cw_agent_config(instance_id):
    # AmazonCloudWatch Agent configuration  
    logger.info("------- cw_agent_config :" + instance_id)

    ssm_agent_config = ssm_exec_commands(instance_id,"AmazonCloudWatch-ManageAgent",{"action": ["configure"],"mode": ["ec2"],"optionalConfigurationLocation": ["/minecraftserverdashboard/amazoncloudwatch-linux"],"optionalConfigurationSource": ["ssm"],"optionalRestart": ["yes"]})
    logger.info(ssm_agent_config)
    if ssm_agent_config["Status"] == "Success":
        logger.info("Agent is configured successfully")
    else:
        logger.warning("Agent configuration failed")
         
# def scriptExec(instance):
#     ssmRunScript = ssm_exec_commands(instance,"AWS-RunRemoteScript",{"sourceType": ["GitHub"],"sourceInfo": ["{\"owner\":\"arturlr\", \"repository\": \"minecraft-server-dashboard\", \"path\": \"scripts/adding_cron.sh\", \"getOptions\": \"branch:dev\" }"],"commandLine": ["bash adding_cron.sh"]})
#     logger.info(ssmRunScript)

def ssm_exec_commands(instance_id: str, doc_name: str, params: Dict[str, Any], max_retries: int = 10, sleep_time: int = 5) -> Optional[Dict[str, Any]]:
    """
    Execute an SSM command on an EC2 instance and wait for its completion.

    Args:
        instance_id (str): The ID of the EC2 instance.
        doc_name (str): The name of the SSM document.
        params (Dict[str, Any]): The parameters for the SSM command.
        max_retries (int): The maximum number of retries for the waiter.
        sleep_time (int): The delay (in seconds) between retries.

    Returns:
        Optional[Dict[str, Any]]: The command invocation details if successful, None otherwise.
    """
    logger.info(f"Executing SSM command {doc_name} on instance {instance_id}")
    try:
        response = ssm.send_command(
            InstanceIds=[instance_id],
            DocumentName=doc_name,
            Parameters=params
        )
        command_id = response['Command']['CommandId']

        waiter = ssm.get_waiter('command_executed')
        waiter.wait(
            CommandId=command_id,
            InstanceId=instance_id,
            WaiterConfig={
                'MaxAttempts': max_retries,
                'DelaySeconds': sleep_time
            }
        )

    except botocore.exceptions.WaiterError as e:
        logger.error(f"Command failed: {e.last_response['Status']}")
        return { "Status": e.last_response['Status'] }
    
    except botocore.exceptions.ClientError as e:
        logger.error(f"Unexpected error: {e}")
        return { "Status": e.last_response['Status'] }

    # Get the command output
    output = ssm.get_command_invocation(
        CommandId=command_id,
        InstanceId=instance_id
    )

    # logger.info(output)
    return output


def handler(event, context):

    instance_id = event["instanceId"]

    # Execute minecraft initialization
    minecraft_init(instance_id)

    # Nic Value
    get_nic_information(instance_id)

    # install packages
    packages_installation(instance_id)

    # Adding Cron Jobs
    config_cron(instance_id)

    ## CloudWatch Agent Steps 
    cwAgentStatus = cw_agent_status_check(instance_id)
    if cwAgentStatus['code'] != 200:
        cw_agent_install(instance_id)
        return { "code": 200, "msg": "CW Agent installed and Script executed"}
    else:
        return cwAgentStatus

    # except Exception as e:
    #     logger.error('Something went wrong: ' + str(e))
    #     return { "code": 500, "msg": str(e) }