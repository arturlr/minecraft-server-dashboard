import boto3
import logging
import os
import json
import urllib.request
import time
from jose import jwk, jwt
from jose.utils import base64url_decode
from datetime import date, datetime, timezone, timedelta

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ec2_client = boto3.client('ec2')
ec2 = boto3.resource('ec2')
ssm = boto3.client('ssm')
cw_client = boto3.client('cloudwatch')
ct_client = boto3.client('cloudtrail')
ce_client = boto3.client('ce')
cognito_idp = boto3.client('cognito-idp')
ENCODING = 'utf-8'

dt_now = datetime.utcnow()
dt_1st_day_of_the_month=datetime.utcnow().replace(day=1,hour=0,minute=0,second=0)
dt_14_days_past_today=datetime.utcnow() - timedelta(days=14)
dt_4_four_hours_before=datetime.utcnow() - timedelta(hours=4)

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

def describeInstances(name,value):
    if name == 'id':
         response = ec2_client.describe_instances(
                InstanceIds=[value]
                    )
    elif name == 'email':
        filters = [
            {"Name":"tag:App", "Values":[ appValue ]}
            #{"Name":"tag:User", "Values":[ value ]}
        ]
        response =  ec2_client.describe_instances(
            Filters=filters            
        )

    # checking response
    if (len(response["Reservations"])) == 0:
        logger.error("No Instances Found")
        return []
    else:
        return response["Reservations"]
            
def describeInstanceStatus(instanceId):
    statusRsp = ec2_client.describe_instance_status(InstanceIds=[instanceId])

    if (len(statusRsp["InstanceStatuses"])) == 0:
        return { 'instanceStatus': "Fail", 'systemStatus': "Fail" }
    
    instanceStatus = statusRsp["InstanceStatuses"][0]["InstanceStatus"]["Status"]
    systemStatus = statusRsp["InstanceStatuses"][0]["SystemStatus"]["Status"]
        
    return { 'instanceStatus': instanceStatus, 'systemStatus': systemStatus }

def getSsmParam(paramKey, isEncrypted=False):
    try:
        ssmResult = ssm.get_parameter(
            Name=paramKey,
            WithDecryption=isEncrypted
        )

        if (ssmResult["ResponseMetadata"]["HTTPStatusCode"] == 200):
            return ssmResult["Parameter"]["Value"]
        else:
            return ""

    except Exception as e:
        logger.warning(str(e) + " for " + paramKey)
        return ""

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
        StartTime=dt_1st_day_of_the_month,
        EndTime=dt_now
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
            delta = dtStopEvent - dtStartEvent
            #print(instanceId + ' s:' + dtStartEvent.strftime("%m/%d/%Y - %H:%M:%S") + ' - e:' + dtStopEvent.strftime("%m/%d/%Y - %H:%M:%S") + ' = ' + str(round(delta.total_seconds()/60,2)))
            totalMinutes = totalMinutes + round(delta.total_seconds()/60,2)
            dtStartEvent = None
            dtStopEvent = None

    # in case the instance is still running
    if isinstance(dtStartEvent, datetime) and not isinstance(dtStopEvent, datetime):
            dtStopEvent = dt_now
            delta = dtStopEvent - dtStartEvent
            #print(instanceId + ' s:' + dtStartEvent.strftime("%m/%d/%Y - %H:%M:%S") + ' - e:' + dtStopEvent.strftime("%m/%d/%Y - %H:%M:%S") + ' = ' + str(round(delta.total_seconds()/60,2)))
            totalMinutes = totalMinutes + round(delta.total_seconds()/60,2)
            dtStartEvent = None
            dtStopEvent = None                               
                    
    return totalMinutes

def handler(event, context):
    #print(event)
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

    instancesInfo = describeInstances('email',userEmail)

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

        instanceStatus = describeInstanceStatus(instanceId)

        runCommand = getSsmParam("/minecraft/" + instanceId + "/runCommand")
        if runCommand == "":
            runCommand = getSsmParam("/minecraft/default/runCommand")

        workingDir = getSsmParam("/minecraft/" + instanceId + "/workingDir")
        if workingDir == "":
            workingDir = getSsmParam("/minecraft/default/workingDir")

        runningMinutes = getInstanceHoursFromCloudTailEvents(instanceId)

        instanceArray.append({
            "id": instanceId,
            "name": instanceName,
            "type": instance["Instances"][0]["InstanceType"],            
            "userEmail": userEmail,
            "state": instance["Instances"][0]["State"]["Name"].lower(),
            "vCpus": vCpus,            
            "memSize": memoryInfo,
            "diskSize": volume.size,
            "launchTime": launchTime.strftime("%m/%d/%Y - %H:%M:%S"),
            "publicIp": publicIp,            
            "instanceStatus": instanceStatus["instanceStatus"].lower(),
            "systemStatus": instanceStatus["systemStatus"].lower(),
            "runCommand": runCommand,
            "workingDir": workingDir,
            "runningMinutes": runningMinutes
        })

    return instanceArray 

