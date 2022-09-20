import urllib
import boto3
import logging
import os
import json
import time
from jose import jwk, jwt
from jose.utils import base64url_decode
from datetime import datetime, timezone, timedelta

from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key, Attr

logger = logging.getLogger()
logger.setLevel(logging.INFO)

session = boto3.session.Session()
awsRegion = session.region_name

class Dyn:
    def __init__(self):
        logger.info("------- Dyn Class Initialization")
        dynamodb = boto3.resource('dynamodb', region_name=awsRegion)
        instancesTable = os.getenv('INSTANCES_TABLE_NAME')
        self.table = dynamodb.Table(instancesTable)

    def GetInstanceAttr(self,instanceId):
        try:
            logger.info("GetInstanceAttr: " + instanceId)
            response = self.table.query(
                KeyConditionExpression=Key('instanceId').eq(instanceId) 
                    # For future implementation
                    # Key('region').eq(region_name)
            )
            if 'Items' in response and len(response['Items']) > 0:
                return {'code': 200, 'msg': response['Items'][0] } 
            else:
                return {'code': 400, 'msg': "Instance not found" } 

        except ClientError as e:
            logger.error(e.response['Error']['Message'])
            return {'code': 500, 'msg': e.response['Error']['Message'] }

    def SetInstanceAttr(self,instanceId,params):
        try:
            logger.info("SetInstanceAttr: " + instanceId)

            dynExpression = "set "               
            valuesMap = {}

            if 'rc' in params:
                dynExpression = dynExpression + "runCommand = :rc,"     
                valuesMap[':rc'] = params["rc"]
            if 'wd' in params:
                dynExpression = dynExpression + "workingDir = :wd,"     
                valuesMap[':wd'] = params["wd"]
            if 'am' in params:
                dynExpression = dynExpression + "alarmMetric = :am,"     
                valuesMap[':am'] = params["am"]
            if 'at' in params:
                dynExpression = dynExpression + "alarmThreshold = :at,"     
                valuesMap[':at'] = params["at"]
        
            entry = self.GetInstanceAttr(instanceId)

            if entry['code'] == 200:
                logger.info("Updating Instance " + instanceId)
            elif entry['code'] == 400:
                logger.info("Creating Instance " + instanceId)
            else:
                logger.error("GetInstance failed")
                return {'code': 500, 'msg': "GetInstance failed" }

            resp = self.table.update_item(
                    Key={ 
                        'instanceId': instanceId, 
                        'region': awsRegion 
                    },
                    UpdateExpression=dynExpression[:-1],
                    ExpressionAttributeValues=valuesMap,
                    ReturnValues="UPDATED_NEW"
                )

            return {'code': 200, 'msg': "Item Saved" }

                        
        except ClientError as e:
            logger.error(e.response['Error']['Message'])
            return {'code': 500, 'msg': e.response['Error']['Message'] }

class Utils:
    def __init__(self):
        logger.info("------- Utils Class Initialization")
        self.ec2_client = boto3.client('ec2')
        self.ssm = boto3.client('ssm')        
        self.appValue = os.getenv('TAG_APP_VALUE')
        self.ec2InstanceProfileArn = os.getenv('EC2_INSTANCE_PROFILE_ARN')

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
        
    def getSsmParam(self, paramKey, isEncrypted=False):
        try:
            ssmResult = self.ssm.get_parameter(
                Name=paramKey,
                WithDecryption=isEncrypted
            )

            if (ssmResult["ResponseMetadata"]["HTTPStatusCode"] == 200):
                return ssmResult["Parameter"]["Value"]
            else:
                return None

        except Exception as e:
            logger.warning(str(e) + " for " + paramKey)
            return None

    def getSsmParameters(self, paramKeys, isEncrypted=False):
        try:
            resp=[]
            paramArray=paramKeys.split(",")            
            ssmResult = self.ssm.get_parameters(
                Names=paramArray,
                WithDecryption=isEncrypted
            )           
            if (len(ssmResult["Parameters"]) > 0):      
                for entry in ssmResult["Parameters"]:
                    resp.append({
                        "Name":entry["Name"],
                        "Value":entry["Value"]
                    })

                return resp
            else:
                return None

        except Exception as e:
            logger.warning(str(e) + " for " + paramKeys)
            return None

    def putSsmParam(self, paramKey, paramValue, paramType):
        try:
            ssmResult = self.ssm.put_parameter(
                Name=paramKey,
                Value=paramValue,
                Type=paramType,
                Overwrite=True
            )

            return ssmResult

        except Exception as e:
            logger.warning(str(e) + " for " + paramKey)
            return None

    def describeInstances(self,name,value):
        if name == 'id':
            response = self.ec2_client.describe_instances(
                    InstanceIds=[value]
                        )
        elif name == 'email':
            filters = [
                {"Name":"tag:App", "Values":[ self.appValue ]},
                {"Name":"instance-state-name", "Values":["pending","running","stopping","stopped"]}
                
                # {"Name":"tag:User", "Values":[ value ]}
            ]
            response =  self.ec2_client.describe_instances(
                Filters=filters            
            )
        elif name == 'state':
            filters = [
                {"Name":"tag:App", "Values":[ self.appValue ]},
                {"Name":"instance-state-name", "Values":[ value ]}
            ]
            response =  self.ec2_client.describe_instances(
                Filters=filters            
            )

        # checking response
        logger.info("for " + name + ": " + value + " found " + str(len(response["Reservations"])) + " instances")
        if (len(response["Reservations"])) == 0:
            return []
        else:
            return response["Reservations"]

    def describeIamProfile(self, instance, status):
        descResp = self.ec2_client.describe_iam_instance_profile_associations(
            Filters=[
                {
                    'Name': 'instance-id',
                    'Values': [
                        instance
                    ]
                },
            ])

        if len(descResp['IamInstanceProfileAssociations']) > 0:        
            for rec in descResp['IamInstanceProfileAssociations']:
                if rec['State'] == status:
                    return { "AssociationId": rec['AssociationId'], "Arn": rec['IamInstanceProfile']['Arn'] }

        return None
                
    def describeInstanceStatus(self, instanceId):
        iamStatus = 'Fail'
        initStatus = 'Fail'

        statusRsp = self.ec2_client.describe_instance_status(InstanceIds=[instanceId])

        if (len(statusRsp["InstanceStatuses"])) == 0:
            return { 'instanceStatus': "Fail", 'systemStatus': "Fail" }
        
        instanceStatus = statusRsp["InstanceStatuses"][0]["InstanceStatus"]["Status"]
        systemStatus = statusRsp["InstanceStatuses"][0]["SystemStatus"]["Status"]

        if instanceStatus == 'ok' and  systemStatus == 'ok':
            initStatus = 'ok'
        
        iamProfile = self.describeIamProfile(instanceId,"associated")
        if iamProfile != None and iamProfile['Arn'] == self.ec2InstanceProfileArn:
            iamStatus = 'ok'
        
        return { 'initStatus': initStatus, 'iamStatus': iamStatus }
