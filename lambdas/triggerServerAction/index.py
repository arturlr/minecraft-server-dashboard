import urllib
import boto3
import logging
import os
import json
import time
from jose import jwk, jwt
from jose.utils import base64url_decode
from datetime import datetime, timezone
import helpers

logger = logging.getLogger()
logger.setLevel(logging.INFO)
utl = helpers.Utils()
dyn = helpers.Dyn()

appValue = os.getenv('TAG_APP_VALUE')

ssm = boto3.client('ssm')
sfn = boto3.client('stepfunctions')
cognito_idp = boto3.client('cognito-idp')

sftArn = os.getenv('StepFunctionsArn')
botoSession = boto3.session.Session()
awsRegion = botoSession.region_name

adminEmail = utl.getSsmParam('/amplify/minecraftserverdashboard/adminemail')

def _response(status_code, body, headers={}):
    if bool(headers): # Return True if dictionary is not empty # use json.dumps for body when using with API GW
        return {"statusCode": status_code, "body": body, "headers": headers}
    else:
        return {"statusCode": status_code, "body": body }

def _is_token_valid(token, keys):
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

def _group_exists(instanceId, poolId):
    try:
        grpRsp = cognito_idp.get_group(
                GroupName=instanceId,
                UserPoolId=poolId
            )
            
        return True
        
    except cognito_idp.exceptions.ResourceNotFoundException:
        logger.warning("Group does not exist.")
        return False
            
def _create_group(instanceId, poolId):    
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
        
def _add_user_to_group(instanceId,poolId,userEmail):
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
            

def handler(event, context):
    if not 'identity' in event:
        logger.error("No Identity found")
        resp = {"err": "No Identity found" }
        return _response(401,resp)

    iss = event["identity"]["claims"]["iss"] 
    token = event["request"]["headers"]["authorization"] 
    keys_url = iss + '/.well-known/jwks.json'
    # download the key
    with urllib.request.urlopen(keys_url) as f:
        response = f.read()
    keys = json.loads(response.decode('utf-8'))['keys']

    token_claims = _is_token_valid(token,keys)

    if token_claims == None:
        logger.error("Invalid Token")
        resp = {"err": "Invalid Token" }
        return _response(401,resp)        

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
            return _response(401,resp)

        #
        # Group Checking and Creation
        #
        cogGrp = _group_exists(instanceId,iss.split("/")[3])
        if cogGrp == False:
            # Create Group
            logger.warning("Group " + instanceId + " does not exit. Creating one.")
            crtGrp = _create_group(instanceId,iss.split("/")[3])
            if crtGrp:
                # adding Admin Account to the group
                logger.info("Group created. Now adding admin user to it.")
                resp = _add_user_to_group(instanceId,iss.split("/")[3],adminEmail)
            else:
                return _response(401,{"err": 'Cognito group creation failed'})

        #
        # Action Processing
        #
        if action == "adduser":
            # get only prefix if user provided @ accidently and add the gmail suffix
            gmailAccount = paramValue.split("@")[0] + '@gmail.com'
            resp = _add_user_to_group(instanceId,iss.split("/")[3],gmailAccount)
            if 'msg' in  resp:
                return _response(200,resp)
            else:
                return _response(500,resp)

        # ADD SSM PARAMETER
        elif action == "addparameter":
            response = utl.putSsmParam(paramKey,paramValue,'String')
            keyName=paramKey.split('/')
            if (keyName[-1]=="alarmThreshold"):
                utl.updateAlarm(keyName[-1])
            resp = {"msg" : "Parameter saved"}
            return _response(200,resp)

        # GET INSTANCE INFO
        elif action == "getintanceinfo":
            response = dyn.GetInstanceInfo(instanceId)
            return _response(response["code"],response["entry"])

        
        # GET INSTANCE INFO
        elif action == "setintanceinfo":
            response = dyn.SetInstanceAttr(instanceId,params)
            return _response(response["code"],response["entry"])


        # GET SSM PARAMETERS
        elif action == "getparameters":
            response = utl.getSsmParameters(paramKey)
            if response != None:
                return _response(200,response)
            else:
                return _response(500,"No parameters")

        # GET SSM PARAMETER
        elif action == "getparameter":
            response = utl.getSsmParam(paramKey)
            if response != None:
                return _response(200,response)
            else:
                return _response(500,"No parameters")

        else:
            # Invoking Step-Functions to change EC2 Stage
            sfn_rsp = sfn.start_execution(
                stateMachineArn=sftArn,
                input='{\"instanceId\" : \"' + instanceId + '\", \"action\" : \"' + action + '\"}'
            )
            resp = {"msg" : sfn_rsp["executionArn"]}

            return _response(200,resp)
            
    except Exception as e:
        resp = {"err": str(e)}
        logger.error(str(e))
        return _response(500,resp)
            