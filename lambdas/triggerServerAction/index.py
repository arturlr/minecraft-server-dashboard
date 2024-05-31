import boto3
import logging
import os
import json
import time
import helpers

logger = logging.getLogger()
logger.setLevel(logging.INFO)
utl = helpers.Utils()
dyn = helpers.Dyn()

appValue = os.getenv('TAG_APP_VALUE')
ec2_instance_profile_name = os.getenv('EC2_INSTANCE_PROFILE_NAME')
ec2_instance_profile_arn = os.getenv('EC2_INSTANCE_PROFILE_ARN')
config_server_lambda_name = os.getenv('CONFIG_SERVER_LAMBDA_NAME')
cognito_pool_id = os.getenv('COGNITO_USER_POOL_ID')

ssm = boto3.client('ssm')
sfn = boto3.client('stepfunctions')
ec2 = boto3.client('ec2')
lambda_client = boto3.client('lambda')
cw_client = boto3.client('cloudwatch')
auth = helpers.Auth(cognito_pool_id)

sftArn = os.getenv('StepFunctionsArn')
botoSession = boto3.session.Session()
awsRegion = botoSession.region_name

def manage_iam_profile(instance_id):
    iam_profile = utl.describe_iam_profile(instance_id, "associated")
    logger.info(iam_profile)

    if iam_profile and iam_profile['Arn'] == ec2_instance_profile_arn:
        logger.info(f"Instance IAM Profile is already valid: {iam_profile['Arn']}")
        return True
    elif iam_profile:
        logger.info(f"Instance IAM Profile is invalid: {iam_profile['Arn']}")
        rsp = disassociate_iam_profile(instance_id, iam_profile['AssociationId'])
        if not rsp:
            return False

    logger.info("Attaching IAM role to the Minecraft Instance")
    return attach_iam_profile(instance_id)

def disassociate_iam_profile(instance_id, association_id):
    logger.info(f"Disassociating IAM profile: {association_id}")
    ec2.disassociate_iam_instance_profile(AssociationId=association_id)

    def check_disassociated_status():
        return utl.describe_iam_profile(instance_id, "disassociated", association_id) is not None

    if not retry_operation(check_disassociated_status, max_retries=30, delay=5):
        logger.warn("Profile timeout during disassociating")
        return False

    return True

def attach_iam_profile(instance_id):
    logger.info(f"Attaching IAM profile: {ec2_instance_profile_name}")
    response = ec2.associate_iam_instance_profile(
        IamInstanceProfile={"Name": ec2_instance_profile_name},
        InstanceId=instance_id
    )

    def check_associated_status():
        iam_profile = utl.describe_iam_profile(instance_id, "associated")
        logger.info(iam_profile)
        return iam_profile and iam_profile['Arn'] == ec2_instance_profile_arn

    if not retry_operation(check_associated_status, max_retries=30, delay=5):
        logger.warn("Profile timeout during association")
        return False

    return True

def retry_operation(operation, max_retries, delay):
    retries = 0
    while retries < max_retries:
        if operation():
            return True
        retries += 1
        time.sleep(delay)
    return False

def update_alarm(instanceId):
    logger.info("updateAlarm: " + instanceId)
    instanceInfo = dyn.GetInstanceAttr(instanceId)
    # Default values
    alarmMetric = "CPUUtilization"
    alarmThreshold = "10"
    
    if instanceInfo and instanceInfo['code'] == 200:
        alarmMetric = instanceInfo['msg'].get('alarmMetric')
        alarmThreshold = instanceInfo['msg'].get('alarmThreshold')

    elif instanceInfo and instanceInfo['code'] == 400:
        logger.info("Using Default values for Alarming")

    else:
        logger.error(instanceInfo)
        return False

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
            AlarmActions=["arn:aws:automate:" + awsRegion + ":ec2:stop"],
            InsufficientDataActions=[],
            MetricName=alarmMetricName,
            Namespace=namespace,
            Statistic=statistic,
            Dimensions=dimensions,
            Period=60,
            EvaluationPeriods=35,
            DatapointsToAlarm=35,
            Threshold=int(alarmThreshold),
            TreatMissingData="missing",
            ComparisonOperator="LessThanOrEqualToThreshold"   
        )

    logger.info("Alarm configured to " + alarmMetric + " and " + alarmThreshold)

def invoke_step_functions(instanceId,action):
    # Invoking Step-Functions to change EC2 Stage
    sfn_rsp = sfn.start_execution(
        stateMachineArn=sftArn,
        input='{\"instanceId\" : \"' + instanceId + '\", \"action\" : \"' + action + '\"}'
    )
    #resp = {"msg" : sfn_rsp["executionArn"]}

    return True

# function to create a DynamoDb
def create_dynamodb(instanceId):
    logger.info("create_dynamodb: " + instanceId)
    dyn.CreateTable(instanceId)


def action_process(action,instance_id):

    action = action.lower()

    if action == "startserver":
        #update_alarm(instance_id)
        invoke_step_functions(instance_id,"start")
        return utl.response(200,"Start command submitted")
    elif action == "restartserver":
        invoke_step_functions(instance_id,"restart")
        return utl.response(200,"Restart command submitted")
    elif action == "stopserver":
        invoke_step_functions(instance_id, "stop")
        return utl.response(200,"Stop command submitted")
    elif action == "fixserverrole":
        # attach the IAM Profile to the EC2 Instance
        resp = manage_iam_profile(instance_id)
        print(resp)
        # Execute Config Server Lambda to configure EC2 SSM
        if resp:
            msg = { "msg" : "Successfuly attached IAM role to the Minecraft Instance" }
            return utl.response(200,msg)
        else:
            error = { "err" :"Attaching IAM role failed" }
            logger.error("Attaching IAM role failed")
            return utl.response(500,error)
    else:
        return utl.response(400, {"err": f"Invalid action: {action}"})
    

    # # GET INSTANCE INFO
    # elif action == "get_instance_attr":
    #     response = dyn.GetInstanceAttr(instance_id)
    #     return utl.response(response["code"],response["msg"])

    
    # # GET INSTANCE INFO
    # elif action == "set_instance_attr":            
    #     response = dyn.SetInstanceAttr(instance_id,params)
    #     if 'at' in params:
    #         updateAlarm(instance_id)
    #     return utl.response(response["code"],response["msg"])            

    # except KeyError:
    #     logger.error("Invalid input data format")
    #     resp = {"err": "Invalid input data format"}
    #     return utl.response(500, resp)

    # except Exception as e:
    #     resp = {"err": str(e)}
    #     logger.error(str(e))
    #     return utl.response(500,resp)
            

def handle_local_invocation(event, context):
    # Handle local invocations here
    return action_process(event["action"], event["instanceId"])

def handler(event, context):
    try:
        if 'request' in event:
            if 'headers' in event['request']:
                if 'authorization' in event['request']['headers']:
                    # Get JWT token from header
                    token = event['request']['headers']['authorization']
                else:
                    logger.error("No Authorization header found")
                    return utl.response(401,{"err": "No Authorization header found" })
            else:
                logger.error("No headers found in request")
                return utl.response(401,{"err": "No headers found in request" })
        else:
            # Local invocation
            return handle_local_invocation(event, context)            
            #logger.error("No request found in event")
            #return utl.response(401,{"err": "No request found in event" })
    except Exception as e:
        logger.error(f"Error processing request: {e}")
        return utl.response(401,{"err": e })

    # Get user info
    user_attributes = auth.process_token(token)    

    # Check if claims are valid
    if user_attributes is None:
        logger.error("Invalid Token")
        return "Invalid Token"

    #try:
    instance_id = event["arguments"]["instanceId"]
    if instance_id:
        logger.info(f"Received instanceId: {instance_id}")
    else:
        logger.warning("No instanceId provided in the input data")

    #
    # Autorization Begin
    #
    authorized = False
    cognitoGroups = event["identity"].get("groups") 
    if cognitoGroups:       
        for group in cognitoGroups:
            if (group == instance_id):   
                logger.info("Authorized server action for email %s on instance %s", user_attributes["email"], instance_id) 
                authorized = True
                break         

    server_info = utl.list_server_by_id(instance_id)
  
    server_admin_email = ""
    tags = server_info["Reservations"]["Instances"][0]["Tags"]
    for tag in tags:
        if tag['Key'] == 'Owner':
            server_admin_email = tag['Value']

    if server_admin_email == user_attributes["email"]:
        logger.info("Authorized as server owner")
        authorized = True
    
    if not authorized:
        resp = {"err": "User not authorized"}
        logger.error(user_attributes["email"] + " is not authorized as Server Owner")
        return utl.response(401, resp)

    #
    # Group Checking and Creation
    #
    cogGrp = auth.group_exists(instance_id)
    if not cogGrp:
        # Create Group
        logger.warning(f"Group {instance_id} does not exit. Creating one.")
        crtGrp = auth.create_group(instance_id)
        if crtGrp:
            # adding Admin Account to the group
            logger.info("Group created. Now adding admin user to it.")
            # resp = add_user_to_group(instance_id,cognito_pool_id,adminEmail)
        else:
            return utl.response(401,{"err": 'Cognito group creation failed'})

    # Calling action_process function to process the action with the mutation name
    mutation_name = event["info"]["fieldName"]
    return action_process(mutation_name,instance_id)
    