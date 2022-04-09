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

dt_1st_day_of_the_month=date.today().replace(day=1)
dt_14_days_past_today=datetime.utcnow() - timedelta(days=14)
dt_4_four_hours_before=datetime.utcnow() - timedelta(hours=4)
dt_now = datetime.utcnow()

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

def getUsageCost(instanceId,granularity,startDate,endDate):
    try:
        usageQuantity = 0
        unblendedCost = 0
        request = {
                "TimePeriod": {
                    "Start": startDate,
                    "End": endDate
                },
                "Filter": {
                    "And": [
                        {
                            "Dimensions": {
                                "Key": "USAGE_TYPE_GROUP",
                                "Values": [
                                    "EC2: Running Hours"
                                ]
                            },
                            
                        },
                        {
                            "Tags": {
                                "Key": "InstanceId",
                                "Values": [ instanceId
                                ]
                            }
                        }
                    ]
                },
                "Granularity": granularity,
                "Metrics": [
                    "UnblendedCost",
                    "UsageQuantity"
                ]
            }
        response = ce_client.get_cost_and_usage(**request)

        if granularity == "MONTHLY":
            for results in response['ResultsByTime']:              
                unblendedCost = float(results['Total']['UnblendedCost']['Amount'])
                usageQuantity = float(results['Total']['UsageQuantity']['Amount'])

            return { "date": endDate, "unblendedCost": round(unblendedCost,1), "usageQuantity": round(usageQuantity,1) }

        else:
            usageDays = []
            for results in response['ResultsByTime']:
                usageDays.append({
                    "date": results['TimePeriod']['Start'],
                    "unblendedCost": float(results['Total']['UnblendedCost']['Amount']),
                    "usageQuantity": float(results['Total']['UsageQuantity']['Amount'])
                })
            return usageDays
                
    except Exception as e:
        logger.error(str(e))
        return { "unblendedCost": 0, "usageQuantity": 0 }

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

def getCloudTailEvents(instanceId, eventValue):
    eventList = []

    paginator = ct_client.get_paginator('lookup_events')
    
    StartingToken = None
    
    page_iterator = paginator.paginate(
    	LookupAttributes=[{'AttributeKey':'EventName','AttributeValue': eventValue}],
    	PaginationConfig={'PageSize':50, 'StartingToken':StartingToken })
    for page in page_iterator:
        for event in page['Events']:
            if event['Resources'][0]["ResourceName"] == instanceId:
                eventList.append(event['EventTime'].strftime("%m/%d/%Y - %H:%M:%S") + '#' + event['Username'] + '#' + eventValue)
                
    return eventList

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

        dt_1st_day_of_the_month=date.today().replace(day=1)
        dt_14_days_past_today=datetime.utcnow() - timedelta(days=14)
        dt_4_four_hours_before=datetime.utcnow() - timedelta(hours=4)
        dt_now = datetime.utcnow()
        
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

        instanceArray.append({
            "id": instanceId,
            "name": instanceName,
            "type": instance["Instances"][0]["InstanceType"],
            "vCpus": vCpus,
            "userEmail": userEmail,
            "memSize": memoryInfo,
            "diskSize": volume.size,
            "publicIp": publicIp,
            "launchTime": launchTime.strftime("%m/%d/%Y - %H:%M:%S"),
            "instanceStatus": instanceStatus["instanceStatus"].lower(),
            "systemStatus": instanceStatus["systemStatus"].lower(),
            "state": instance["Instances"][0]["State"]["Name"].lower(),
            "monthlyTotalUsage": getUsageCost(instanceId,"MONTHLY",dt_1st_day_of_the_month.strftime("%Y-%m-%d"),dt_now.strftime("%Y-%m-%d")),
            "dailyUsage": getUsageCost(instanceId,"DAILY",dt_14_days_past_today.strftime("%Y-%m-%d"),dt_now.strftime("%Y-%m-%d")),
            "runCommand": runCommand,
            "workingDir": workingDir
        })
        #startEvents = getCloudTailEvents(instanceId, "StartInstances")
        #stopEvents = getCloudTailEvents(instanceId, "StopInstances")
        #payload["timeLine"] = sorted(startEvents + stopEvents, reverse = True)

    #print(instanceArray)
    return instanceArray 

