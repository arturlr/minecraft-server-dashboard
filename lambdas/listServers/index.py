import boto3
import logging
import os
import json
import urllib.request
import time
from jose import jwk, jwt
from jose.utils import base64url_decode
from datetime import date, datetime, timezone, timedelta
import helpers
import pytz

logger = logging.getLogger()
logger.setLevel(logging.INFO)

utl = helpers.Utils()
utc = pytz.utc
pst = pytz.timezone('US/Pacific')

ec2_client = boto3.client('ec2')
ec2 = boto3.resource('ec2')
cw_client = boto3.client('cloudwatch')
ct_client = boto3.client('cloudtrail')
ce_client = boto3.client('ce')
cognito_idp = boto3.client('cognito-idp')
ENCODING = 'utf-8'

appValue = os.getenv('appValue')

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

def extractStateEventTime(evt,previousState,instanceId):
    ctEvent = json.loads(evt['CloudTrailEvent'])
    if 'responseElements' in ctEvent:
        if ctEvent['responseElements'] != None and 'instancesSet' in ctEvent['responseElements']:
            if 'items' in ctEvent['responseElements']['instancesSet']:
                for item in ctEvent['responseElements']['instancesSet']['items']:
                    if item['instanceId'] == instanceId and item['previousState']['name'] == previousState:
                        return ctEvent['eventTime']
    
    return None

def getInstanceHoursFromCloudTailEvents(instanceId):
    totalMinutes = 0

    eventData = []

    paginator = ct_client.get_paginator('lookup_events')
    StartingToken = None
    
    page_iterator = paginator.paginate(
    	LookupAttributes=[{'AttributeKey':'ResourceName','AttributeValue': instanceId}],
    	PaginationConfig={'PageSize':50, 'StartingToken':StartingToken },
        StartTime=datetime.utcnow().replace(day=1,hour=0,minute=0,second=0),
        EndTime=datetime.utcnow()
        )
    for page in page_iterator:
        for evt in page['Events']:
            if evt['EventName'] == "RunInstances":
                ctEvent = json.loads(evt['CloudTrailEvent'])
                eventData.append({'s': 'StartInstances', 'x': ctEvent['eventTime'] })
                
            if evt['EventName'] == "StartInstances":
                startEvent = extractStateEventTime(evt,"stopped",instanceId)
                if startEvent != None:
                    eventData.append({'s': 'StartInstances', 'x': startEvent })

            if evt['EventName'] == "StopInstances":
                stopEvent = extractStateEventTime(evt,"running",instanceId) 
                if stopEvent != None:
                    eventData.append({'s': 'StopInstances', 'x': stopEvent })
 
    data_points = sorted(eventData, key=lambda k : k['x'])
    
    dtStartEvent = None
    dtStopEvent = None
    for point in data_points:
        if point['s'] == "StartInstances":
            dtStartEvent = datetime.fromisoformat(point['x'].replace("Z", "+00:00"))
            continue
        elif point['s'] == "StopInstances":
            if isinstance(dtStartEvent, datetime):
                dtStopEvent = datetime.fromisoformat(point['x'].replace("Z", "+00:00"))
            else:
                # Instance started before the beginning of the month
                dtStartEvent = datetime.now().replace(day=1,hour=0,minute=0,second=0)
                dtStopEvent = datetime.fromisoformat(point['x'].replace("Z", "+00:00")).replace(tzinfo=None)

        if isinstance(dtStartEvent, datetime) and isinstance(dtStopEvent, datetime):
            delta = dtStopEvent.replace(tzinfo=None) - dtStartEvent.replace(tzinfo=None)
            #print(instanceId + ' s:' + dtStartEvent.strftime("%m/%d/%Y - %H:%M:%S") + ' - e:' + dtStopEvent.strftime("%m/%d/%Y - %H:%M:%S") + ' = ' + str(round(delta.total_seconds()/60,2)))
            totalMinutes = totalMinutes + round(delta.total_seconds()/60,2)
            dtStartEvent = None
            dtStopEvent = None

    # in case the instance is still running
    if isinstance(dtStartEvent, datetime) and not isinstance(dtStopEvent, datetime):
            dtStopEvent = datetime.utcnow()
            delta = dtStopEvent.replace(tzinfo=None) - dtStartEvent.replace(tzinfo=None)
            #print(instanceId + ' s:' + dtStartEvent.strftime("%m/%d/%Y - %H:%M:%S") + ' - e:' + dtStopEvent.strftime("%m/%d/%Y - %H:%M:%S") + ' = ' + str(round(delta.total_seconds()/60,2)))
            totalMinutes = totalMinutes + round(delta.total_seconds()/60,2)
            dtStartEvent = None
            dtStopEvent = None                               
                    
    return totalMinutes

def handler(event, context):

    instanceArray = []

    # validate query type
    # validate jwt token

    if not 'identity' in event:
        logger.error("No Identity found")
        return "No Identity found"

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
        return "Invalid Token"

    if 'cognito:username' in token_claims:
        userName=token_claims["cognito:username"]
    else:
        userName=token_claims["username"]

    # Get User Email from Cognito
    cog_user = cognito_idp.admin_get_user(
        UserPoolId=iss.split("/")[3],
        Username=userName
    )

    userEmail=""
    for att in cog_user["UserAttributes"]:
        if att["Name"] == "email":
            userEmail = att["Value"]
            break

    instancesInfo = utl.describeInstances('email',userEmail)

    if len(instancesInfo) == 0:
        logger.error("No Instances Found")
        return "No Instances Found"

    
    for instance in instancesInfo:
        instanceId = instance["Instances"][0]["InstanceId"] 

        launchTime = instance["Instances"][0]["LaunchTime"]
        if "Association" in instance["Instances"][0]["NetworkInterfaces"][0]:
            publicIp = instance["Instances"][0]["NetworkInterfaces"][0]["Association"]["PublicIp"]
        else:
            publicIp = "none"

        instanceName = "Undefined"
        for tag in instance["Instances"][0]["Tags"]:
            if tag["Key"] == "Name":
               instanceName = tag["Value"]

        instanceId = instance["Instances"][0]["InstanceId"]
        instanceType = ec2_client.describe_instance_types(InstanceTypes=[instance["Instances"][0]["InstanceType"]])
        vCpus = instanceType["InstanceTypes"][0]["VCpuInfo"]["DefaultVCpus"]
        memoryInfo = instanceType["InstanceTypes"][0]["MemoryInfo"]["SizeInMiB"]
        volume = ec2.Volume(instance["Instances"][0]["BlockDeviceMappings"][0]["Ebs"]["VolumeId"])

        instanceStatus = utl.describeInstanceStatus(instanceId)

        pstLaunchTime = launchTime.astimezone(pst)
        
        runningMinutes = getInstanceHoursFromCloudTailEvents(instanceId)

        groupMembers = []

        cogGrp = _group_exists(instanceId,iss.split("/")[3])
        if cogGrp:
            response = cognito_idp.list_users_in_group(
                UserPoolId=iss.split("/")[3],
                GroupName=instanceId
            )            
            if len(response["Users"]) > 0:
                for user in response["Users"]:            
                    for att in user["Attributes"]:
                        if att["Name"] == "email":
                            email = att["Value"]
                        elif att["Name"] == "sub":
                            id = att["Value"]
                        elif att["Name"] == "given_name":
                            given_name = att["Value"]
                        elif att["Name"] == "family_name":
                            family_name = att["Value"]
                    groupMembers.append({
                        "id": id,
                        "email": email,
                        "fullname": given_name + ' ' + family_name                        
                    })                        

        instanceArray.append({
            "id": instanceId,
            "name": instanceName,
            "type": instance["Instances"][0]["InstanceType"],            
            "userEmail": userEmail,
            "state": instance["Instances"][0]["State"]["Name"].lower(),
            "vCpus": vCpus,            
            "memSize": memoryInfo,
            "diskSize": volume.size,
            "launchTime": pstLaunchTime.strftime("%m/%d/%Y - %H:%M:%S"),
            "publicIp": publicIp,            
            "instanceStatus": instanceStatus["instanceStatus"].lower(),
            "systemStatus": instanceStatus["systemStatus"].lower(),
            "runningMinutes": runningMinutes,
            "groupMembers": groupMembers
        })

    return instanceArray 

