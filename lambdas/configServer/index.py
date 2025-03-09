import boto3
import botocore
import logging
import os
import json
import time
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

app_name = os.getenv('APP_NAME') 
environment_name = os.getenv('ENVIRONMENT_NAME')
event_response_lambda = os.getenv('EVENT_RESPONSE_LAMBDA')
ssm_doc_name = os.getenv('SSM_DOC_NAME')

def minecraft_init(instance_id):
    logger.info(f"------- minecraft_init: {instance_id}")
    instance_attributes = ec2_utils.get_instance_attributes_from_tags(instance_id)

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
    agent_details=None

    # Checking Agent Status if Success. Failed messages occurs when the CloudWatch Agent is not installed. 
    if ssm_agent_status:
        jpexpr = parse("$.pluginsDetails[?(@.Name[:] == 'ControlCloudWatchAgentLinux')].Output")
        for i in jpexpr.find(ssm_agent_status):
            agent_details = i.value
            
        if agent_details:
            agent_details_json = json.loads(agent_details)
            if agent_details_json["status"] == "running": 
                logger.info("Agent is already running. Version :" + agent_details_json["version"])
                logger.info("Agent Status: " + agent_details_json["status"] + " - configuration Status: " + agent_details_json["configstatus"])
                return True
        else:
            return True
    else:
        return False
        
def wait_for_instance_ready(instance_id):
    try:
        logger.info("------- wait_for_instance_ready : " + instance_id)
        waiter = ec2.get_waiter('instance_running')
        waiter.wait(InstanceIds=[instance_id])
        
        # Then wait for the instance status checks to pass
        waiter = ec2.get_waiter('instance_status_ok')
        waiter.wait(InstanceIds=[instance_id])

        return True
        
    except Exception as e:
        print(f"Error waiting for instance: {str(e)}")
        return False
 
def ssm_exec_commands(instance_id: str, doc_name: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Execute an SSM command on an EC2 instance and wait for its completion.
    Includes retry logic for InvalidInstanceId exceptions.

    Args:
        instance_id (str): The ID of the EC2 instance.
        doc_name (str): The name of the SSM document.
        params (Dict[str, Any]): The parameters for the SSM command.
        max_retries (int): The maximum number of retries for the waiter.
        sleep_time (int): The delay (in seconds) between retries.

    Returns:
        Optional[Dict[str, Any]]: The command invocation details if successful, None otherwise.
    """
    logger.info(f"------- ssm_exec_commands : {doc_name} - {instance_id}")

    is_instance_ready = wait_for_instance_ready(instance_id)

    if not is_instance_ready:
        logger.error(f"Instance {instance_id} is not in a ready state.") 
        return False

    try:
        response = ssm.send_command(
            InstanceIds=[instance_id],
            DocumentName=doc_name,
            Parameters=params
        )

    except botocore.exceptions.ClientError as error:
        error_code = error.response['Error']['Code']
        command_id = response.get('Command', {}).get('CommandId', None) #response['Command']['CommandId']

        if error_code == 'InvalidInstanceId':
            logger.error(f"Instance {instance_id} not in valid state.")
            return False
        else:
            # If it's a different error, raise it
            logger.error(f"Unexpected error: {error}")
            return False
        

    command_id = response.get('Command', {}).get('CommandId', None) #response['Command']['CommandId']       
    # Wait for completion
    command_result = wait_for_command_execution(command_id, instance_id)
    if command_result:
        return command_result

    return False

def wait_for_command_execution(command_id, instance_id, max_retries: int = 5, wait_time: int = 10):
    logger.info(f"------- wait_for_command_execution : {command_id}")
    if command_id is None:
        logger.error("Command ID is None. Unable to wait for command execution.")   
        return False
    try:
        retries = 0
        
        while True:
            try:
                result = ssm.get_command_invocation(
                    CommandId=command_id,
                    InstanceId=instance_id
                )
                
                status = result['Status']
                
                if status == 'Success':
                    return True
                elif status in ['Failed', 'Cancelled', 'TimedOut']:
                    print(f"Command failed with status: {status}")
                    print(f"Error message: {result.get('StandardErrorContent', 'No error message')}")
                    return False
                
                if retries >= max_retries:
                    print(f"Max retries ({max_retries}) reached while waiting for command completion")
                    return False
                    
                time.sleep(wait_time)
                retries += 1
                
            except ssm.exceptions.InvocationDoesNotExist:
                if retries >= max_retries:
                    print("Max retries reached waiting for command invocation")
                    return False
                time.sleep(wait_time)
                retries += 1
                continue

            except Exception as e:
                print(f"Unexpected error while waiting for command: {str(e)}")

    except Exception as e:
        print(f"Error while waiting for command: {str(e)}")
        return False
 
def remove_shutdown_schedule(instance_id):
    """
    Removes an EventBridge rule that schedules server shutdown
    """
    logger.info(f"------- remove_shutdown_schedule: {instance_id}")
    
    # Create EventBridge client
    events = boto3.client('events')
    
    rule_name = f"minecraft-shutdown-{instance_id}"
    
    try:
        # Remove targets from the rule
        events.remove_targets(
            Rule=rule_name,
            Ids=[f'ShutdownTarget-{instance_id}']
        )
        
        # Delete the rule
        events.delete_rule(
            Name=rule_name
        )
        
        logger.info(f"Shutdown schedule removed for instance {instance_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error removing shutdown schedule: {str(e)}")
        return False   

def create_shutdown_schedule(instance_id, schedule):
    """
    Creates an EventBridge rule to schedule server shutdown
    """
    logger.info(f"------- create_shutdown_schedule: {instance_id}")
    
    # Create EventBridge client
    events = boto3.client('events')
    
    rule_name = f"minecraft-shutdown-{instance_id}"
    
    try:
        # Create the EventBridge rule
        response = events.put_rule(
            Name=rule_name,
            ScheduleExpression=f"cron({schedule})",
            State='ENABLED',
            Description=f'Scheduled shutdown for Minecraft server {instance_id}'
        )
        
        # Create the target for the Lambda function
        target = {
            'Id': f'ShutdownTarget-{instance_id}',
            'Arn': event_response_lambda,
            'Input': json.dumps({
                'action': 'stop',
                'instanceId': instance_id
            })
        }
        
        # Add the target to the rule
        events.put_targets(
            Rule=rule_name,
            Targets=[target]
        )
        
        logger.info(f"Shutdown schedule created for {schedule}")
        return True
        
    except Exception as e:
        logger.error(f"Error creating shutdown schedule: {str(e)}")
        return False

def update_alarm(instanceId, alarmMetric, alarmThreshold, alarmEvaluationPeriod):
    logger.info("------- update_alarm : " + instanceId)

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
        EvaluationPeriods=int(alarmEvaluationPeriod),
        DatapointsToAlarm=int(alarmEvaluationPeriod),
        Threshold=int(alarmThreshold),
        TreatMissingData="missing",
        ComparisonOperator="LessThanOrEqualToThreshold"   
    )

    logger.info("Alarm configured to " + alarmMetric + " and " + alarmThreshold)

def remove_alarm(instance_id):
    logger.info("------- remove_alarm : " + instance_id)

    alarm_name = instance_id + "-" + "minecraft-server"
    cw_client.delete_alarms(
        AlarmNames=[
            alarm_name
        ]
    )

def handler(event, context):

    instance_id = event["instanceId"]
    logger.info("Configuring Server: " + instance_id)
    server_info = ec2_utils.list_server_by_id(instance_id)
    
    if server_info["TotalInstances"] == 0:
        logger.warning("Instance not found")
        return False
    
    instance_info = server_info['Instances'][0]

    tags = {tag['Key']: tag['Value'] for tag in instance_info["Tags"]}
    bootstraped = tags.get("Boostraped", False)
    if not bootstraped:
        ssm_param_prefix = "/" + app_name + "/" + environment_name 
        parameters = {
            'SSMParameterPrefix': [ssm_param_prefix]   
        }
        ssm_exec_commands(instance_id,ssm_doc_name,parameters)
    else:
        logger.info("Instance already boostraped")
        
    # Execute minecraft initialization
    minecraft_init(instance_id)

    # making sure the alarm is on
    alarmMetric = tags.get("AlarmMetric", 'CPUUtilization')
    alarmThreshold = tags.get('AlarmThreshold','25')
    alarmEvaluationPeriod = tags.get('AlarmEvaluationPeriod', '35')

    update_alarm(instance_id,alarmMetric,alarmThreshold,alarmEvaluationPeriod)

    cwAgentStatus = cw_agent_status_check(instance_id)
    if not cwAgentStatus:
        logger.error("CloudWatch Agent is not running")
 

