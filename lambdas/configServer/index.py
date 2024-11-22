import boto3
import botocore
from typing import Optional, Dict, Any
import logging
import os
import json
import time
import uuid
from datetime import datetime, timezone
from jsonpath_ng.ext import parse
import ec2Helper
import utilHelper

logger = logging.getLogger()
logger.setLevel(logging.INFO)

aws_region = os.getenv('AWS_REGION_NAME', 'us-east-1')  # Provides a default fallback
sts = boto3.client('sts')
aws_account_id = sts.get_caller_identity()['Account']

ec2_utils = ec2Helper.Ec2Utils()
utl = utilHelper.Utils()

ssm = boto3.client('ssm')
ec2 = boto3.client('ec2')
cw_client = boto3.client('cloudwatch')
lambda_client = boto3.client('lambda')

appValue = os.getenv('TAG_APP_VALUE')
appName = os.getenv('APP_NAME') 
event_response_lambda = os.getenv('EVENT_RESPONSE_LAMBDA')
ssm_doc_name = os.getenv('SSM_DOC_NAME')

# def event_response_payload(instance_id):
#     logger.info("------- event_response_payload : " + instance_id)

#     # create a uuid
#     event_id = str(uuid.uuid4())

#     payload = {
#         "id": event_id,
#         "detail-type": "EC2 Instance State-change Notification", 
#         "source": "aws.ec2",
#         "account": aws_account_id,
#         "time": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
#         "region": aws_region,
#         "resources": [
#             "arn:aws:ec2:" + aws_region + ":" + aws_account_id + ":instance/" + instance_id
#         ],
#         "detail": {
#             "instance-id": instance_id,
#             "state": "fake"
#         }
#     }

#     return payload

def minecraft_init(instance_id):
    logger.info(f"------- minecraft_init: {instance_id}")
    instance_attributes = ec2_utils.get_instance_attributes(instance_id)

    if not instance_attributes:
        logger.warning("Instance data does not exist")
        return False
    
    if 'runCommand' not in instance_attributes or len(instance_attributes["runCommand"]) < 2:
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
        
def ssm_exec_commands(instance_id: str, doc_name: str, params: Dict[str, Any] = None, max_retries: int = 10, sleep_time: int = 5) -> Optional[Dict[str, Any]]:
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
        instance_ids = [instance_id]
        response = ssm.send_command(
            InstanceIds=instance_ids,
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

        # Get the command output
        output = ssm.get_command_invocation(
            CommandId=command_id,
            InstanceId=instance_id
        )

        # logger.info(output)
        return output
    
    except botocore.exceptions.ClientError as e:
        logger.error(f"Unexpected error: {e}")
        raise botocore.exceptions.ClientError(f"Unexpected error: {e}") from e
    
    except botocore.exceptions.WaiterError as e:
        logger.error(f"Command failed: {e.last_response['Status']}")
        return {"Status": e.last_response['Status']}
    
def update_alarm(instanceId,alarmMetric,alarmThreshold,alarmEvaluationPeriod):
    logger.info("updateAlarm: " + instanceId)

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
            AlarmActions=["arn:aws:automate:" + aws_region + ":ec2:stop"],
            InsufficientDataActions=[],
            MetricName=alarmMetricName,
            Namespace=namespace,
            Statistic=statistic,
            Dimensions=dimensions,
            Period=60,
            EvaluationPeriods=alarmEvaluationPeriod,
            DatapointsToAlarm=alarmEvaluationPeriod,
            Threshold=int(alarmThreshold),
            TreatMissingData="missing",
            ComparisonOperator="LessThanOrEqualToThreshold"   
        )

    logger.info("Alarm configured to " + alarmMetric + " and " + alarmThreshold)
    
def handler(event, context):

    instance_id = event["instanceId"]
    logger.info("Configuring Server: " + instance_id)
    server_info = ec2_utils.list_server_by_id(instance_id)
    
    logger.info(server_info)

    if server_info["TotalInstances"] == 0:
        logger.warning("Instance not found")
        return False
    
    instance_info = server_info['Instances'][0]

    tags = {tag['Key']: tag['Value'] for tag in instance_info["Tags"]}
    bootstraped = tags.get("Boostraped", False)
    if not bootstraped:
        ssm_exec_commands(instance_id,ssm_doc_name)
        
    # Execute minecraft initialization
    minecraft_init(instance_id)

    # making sure the alarm is on
    alarmMetric = tags.get("AlarmMetric", 'CPUUtilization')
    alarmThreshold = tags.get('AlarmThreshold','25')
    alarmEvaluationPeriod = tags.get('AlarmEvaluationPeriod', '35')

    update_alarm(instance_id,alarmMetric,alarmThreshold,alarmEvaluationPeriod)

    # # invoke event_response_lambda to force iamstatus update
    # payload = event_response_payload(instance_id)
    # response = lambda_client.invoke(
    #     FunctionName=event_response_lambda,
    #     InvocationType='RequestResponse', # 'Event' for asynchronous invocation
    #     Payload=bytes(json.dumps(payload), encoding='utf-8')
    # )

    # # Get the response payload
    # payload = response.get('Payload').read()

    # # Print the response
    # print(payload)

    ## CloudWatch Agent Steps 
    cwAgentStatus = cw_agent_status_check(instance_id)
    if cwAgentStatus['code'] != 200:
        logger.warning("CloudWatch Agent is not running")
    else:
        return cwAgentStatus

