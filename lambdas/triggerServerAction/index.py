import urllib
import boto3
import logging
import os
import json
import time
from datetime import datetime, timezone
from jose import jwk, jwt
from jose.utils import base64url_decode
import helpers

logger = logging.getLogger()
logger.setLevel(logging.INFO)
utl = helpers.Utils()
dyn = helpers.Dyn()

appValue = os.getenv('TAG_APP_VALUE')
ec2InstanceProfileName = os.getenv('EC2_INSTANCE_PROFILE_NAME')
ec2InstanceProfileArn = os.getenv('EC2_INSTANCE_PROFILE_ARN')
configServerLambdaName = os.getenv('CONFIG_SERVER_LAMBDA_NAME')

ssm = boto3.client('ssm')
sfn = boto3.client('stepfunctions')
ec2 = boto3.client('ec2')
lambda_client = boto3.client('lambda')
cw_client = boto3.client('cloudwatch')
cognito_idp = boto3.client('cognito-idp')

sftArn = os.getenv('StepFunctionsArn')
botoSession = boto3.session.Session()
awsRegion = botoSession.region_name

adminEmail = utl.getSsmParam('/amplify/minecraftserverdashboard/adminemail')

def is_token_valid(token, keys):
    # https://github.com/awslabs/aws-support-tools/tree/master/Cognito/decode-verify-jwt
    headers = jwt.get_unverified_headers(token)
    kid = headers['kid']
    # search for the kid in the downloaded public keys
    key_index = -1
    for i in range(len(keys)):
        if kid == keys[i]['kid']:
            key_index = i
            break
    if key_index == -1:
        logger.error('Public key not found in jwks.json')
        return None
    # construct the public key
    public_key = jwk.construct(keys[key_index])
    # get the last two sections of the token,
    # message and signature (encoded in base64)
    message, encoded_signature = str(token).rsplit('.', 1)
    # decode the signature
    decoded_signature = base64url_decode(encoded_signature.encode('utf-8'))
    # verify the signature
    if not public_key.verify(message.encode("utf8"), decoded_signature):
        logger.error('Signature verification failed')
        return None
    logger.info('Signature successfully verified')
    # since we passed the verification, we can now safely
    # use the unverified claims
    claims = jwt.get_unverified_claims(token)
    
    # additionally we can verify the token expiration
    if time.time() > claims['exp']:
        logger.error('Token is expired')
        return None
    # now we can use the claims
    return claims

def iamProfileTask(instance):
    loopCount = 0

    iamProfile = utl.describeIamProfile(instance,"associated")
    if iamProfile != None and iamProfile['Arn'] == ec2InstanceProfileArn:
        logger.info("Instance IAM Profile is already: " + iamProfile['Arn'] )
        return True

    if iamProfile != None:
        logger.info("Disassociating Instance IAM Profile: " + iamProfile['Arn'] )
        disassociateIamProfile(iamProfile['AssociationId'])
        while loopCount < 5:
            checkStatusCommand = utl.describeIamProfile(instance,"disassociated")
            time.sleep(10)
            if checkStatusCommand != None:
                loopCount = loopCount + 1
            else:
                attachIamProfile(instance)
                break
        
    else:
        logger.info("Attaching IAM role to the Minecraft Instance")
        attachIamProfile(instance)
        return { "msg": "Attached IAM role to the Minecraft Instance" }
        
    if loopCount > 5:
        logger.warn("Profile timeout during disassociating")
        return { "err": "Profile timeout during disassociating" }

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

def group_exists(instanceId, poolId):
    try:
        grpRsp = cognito_idp.get_group(
                GroupName=instanceId,
                UserPoolId=poolId
            )
            
        return True
        
    except cognito_idp.exceptions.ResourceNotFoundException:
        logger.warning("Group does not exist.")
        return False
            
def create_group(instanceId, poolId):    
    try:
        grpRsp = cognito_idp.create_group(
            GroupName=instanceId,
            UserPoolId=poolId,
            Description='Minecraft Dashboard'
        )

        return True

    except Exception as e:
            logger.info("Exception create_group")
            logger.error(str(e))
            return False
        
def add_user_to_group(instanceId,poolId,userEmail):
        try:
            user = cognito_idp.list_users(
                UserPoolId=poolId,
                Filter="email = '" + userEmail + "'"
            )

            if len(user['Users']) == 0:
                logger.error("Unable to find user: " + userEmail + ". User has to create a profile by login in this website")
                return {"err": "Unable to find user: " + userEmail + ". User has to create a profile by login in this website" }

            userRsp = cognito_idp.admin_add_user_to_group(
                UserPoolId=poolId,
                Username=user['Users'][0]["Username"],
                GroupName=instanceId
            )

            return {"msg": "User added to the group"}
    
        except Exception as e:
            logger.info("Exception admin_add_user_to_group")
            logger.warning(str(e))
            return { "err": str(e) } 

def updateAlarm(instanceId):
    logger.info("updateAlarm: " + instanceId)
    instanceInfo = dyn.GetInstanceAttr(instanceId)
    # Default values
    alarmMetric = "CPUUtilization"
    alarmThreshold = "10"

    print(instanceInfo)

    if instanceInfo != None and instanceInfo['code'] == 200:
        if 'alarmMetric' in instanceInfo['msg']:
            alarmMetric = instanceInfo['msg']['alarmMetric']
            
        if 'alarmThreshold' in instanceInfo['msg']:
            alarmThreshold = instanceInfo['msg']['alarmThreshold']
        
    elif instanceInfo != None and instanceInfo['code'] == 400:
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
            DatapointsToAlarm=30,
            Threshold=int(alarmThreshold),
            TreatMissingData="missing",
            ComparisonOperator="LessThanOrEqualToThreshold"   
        )

    logger.info("Alarm configured to " + alarmMetric + " and " + alarmThreshold)
            
def handler(event, context):
    if not 'identity' in event:
        logger.error("No Identity found")
        resp = {"err": "No Identity found" }
        return utl.response(401,resp)

    iss = event["identity"]["claims"]["iss"] 
    token = event["request"]["headers"]["authorization"] 
    keys_url = iss + '/.well-known/jwks.json'
    # download the key
    with urllib.request.urlopen(keys_url) as f:
        response = f.read()
    keys = json.loads(response.decode('utf-8'))['keys']

    token_claims = is_token_valid(token,keys)

    if token_claims == None:
        logger.error("Invalid Token")
        resp = {"err": "Invalid Token" }
        return utl.response(401,resp)        

    if 'cognito:username' in token_claims:
        userName=token_claims["cognito:username"]
    else:
        userName=token_claims["username"]

    # Get User Email from Cognito
    cog_user = cognito_idp.admin_get_user(
        UserPoolId=iss.split("/")[3],
        Username=userName
    )

    invokerEmail=""
    for att in cog_user["UserAttributes"]:
        if att["Name"] == "email":
            invokerEmail = att["Value"]
            break

    try:                 
        logger.info(event["arguments"]["input"])
        instanceId = event["arguments"]["input"]["instanceId"]
        action = event["arguments"]["input"]["action"]

        if 'params' in event["arguments"]["input"]:
            params = event["arguments"]["input"]['params']
        else:
            params = None

        if 'paramKey' in event["arguments"]["input"]:
            paramKey = event["arguments"]["input"]['paramKey']
        else:
            paramKey = None

        if 'paramValue' in event["arguments"]["input"]:
            paramValue = event["arguments"]["input"]['paramValue']
        else:
            paramValue = None

        #
        # Autorization Begin
        #
        authorized = False
        cognitoGroups = event["identity"]["groups"] 
        if cognitoGroups != None:       
            for group in cognitoGroups:
                if (group == instanceId):    
                    authorized = True
                    break
       
        if invokerEmail == adminEmail:
            logger.info("Authorized as Admin")
            authorized = True
        
        if authorized == False:
            resp = {"err": 'User not authorized'}
            return utl.response(401,resp)

        #
        # Group Checking and Creation
        #
        cogGrp = group_exists(instanceId,iss.split("/")[3])
        if cogGrp == False:
            # Create Group
            logger.warning("Group " + instanceId + " does not exit. Creating one.")
            crtGrp = create_group(instanceId,iss.split("/")[3])
            if crtGrp:
                # adding Admin Account to the group
                logger.info("Group created. Now adding admin user to it.")
                resp = add_user_to_group(instanceId,iss.split("/")[3],adminEmail)
            else:
                return utl.response(401,{"err": 'Cognito group creation failed'})

        #
        # Action Processing
        #
        if action == "add_user":
            # get only prefix if user provided @ accidently and add the gmail suffix
            gmailAccount = paramValue.split("@")[0] + '@gmail.com'
            resp = add_user_to_group(instanceId,iss.split("/")[3],gmailAccount)
            if 'msg' in  resp:
                return utl.response(200,resp)
            else:
                return utl.response(500,resp)

        if action == "config_iam":
            # attach the IAM Profile to the EC2 Instance
            resp = iamProfileTask(instanceId)
            # Execute Config Server Lambda to configure EC2 SSM
            if 'msg' in resp:
                params['instanceId'] = instanceId 
                response = lambda_client.invoke(
                FunctionName=str(configServerLambdaName),
                InvocationType='Event',
                Payload=json.dumps(params)
            )
                return utl.response(200,response["msg"])
            else:
                return utl.response(500,response["err"])
            

        # ADD SSM PARAMETER
        elif action == "add_parameter":
            dynResp = dyn.SetInstanceAttr(instanceId,)
            response = utl.putSsmParam(paramKey,paramValue,'String')
            resp = {"msg" : "Parameter saved"}
            return utl.response(200,resp)

        # GET INSTANCE INFO
        elif action == "get_instance_attr":
            response = dyn.GetInstanceAttr(instanceId)
            return utl.response(response["code"],response["msg"])

        
        # GET INSTANCE INFO
        elif action == "set_instance_attr":            
            response = dyn.SetInstanceAttr(instanceId,params)
            if 'at' in params:
                updateAlarm(instanceId)
            return utl.response(response["code"],response["msg"])


        # GET SSM PARAMETERS
        elif action == "get_parameters":
            response = utl.getSsmParameters(paramKey)
            if response != None:
                return utl.response(200,response)
            else:
                return utl.response(500,"No parameters")

        # GET SSM PARAMETER
        elif action == "get_parameter":
            response = utl.getSsmParam(paramKey)
            if response != None:
                return utl.response(200,response)
            else:
                return utl.response(500,"No parameters")

        else:
            # Updating Alarm
            updateAlarm(instanceId)
            # Invoking Step-Functions to change EC2 Stage
            sfn_rsp = sfn.start_execution(
                stateMachineArn=sftArn,
                input='{\"instanceId\" : \"' + instanceId + '\", \"action\" : \"' + action + '\"}'
            )
            resp = {"msg" : sfn_rsp["executionArn"]}

            return utl.response(200,resp)
            
    except Exception as e:
        resp = {"err": str(e)}
        logger.error(str(e))
        return utl.response(500,resp)
            