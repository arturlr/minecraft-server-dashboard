import boto3
import logging
import os
import concurrent.futures
import helpers
import pytz

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ec2_client = boto3.client('ec2')
ec2 = boto3.resource('ec2')
cognito_idp = boto3.client('cognito-idp')
ENCODING = 'utf-8'

appValue = os.getenv('TAG_APP_VALUE')
cognito_pool_id = os.getenv('COGNITO_USER_POOL_ID')

auth = helpers.Auth(cognito_pool_id)
utl = helpers.Utils()
utc = pytz.utc
pst = pytz.timezone('US/Pacific')

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

# def extractStateEventTime(evt,previousState,instanceId):
#     ctEvent = json.loads(evt['CloudTrailEvent'])
#     if 'responseElements' in ctEvent:
#         if ctEvent['responseElements'] != None and 'instancesSet' in ctEvent['responseElements']:
#             if 'items' in ctEvent['responseElements']['instancesSet']:
#                 for item in ctEvent['responseElements']['instancesSet']['items']:
#                     if item['instanceId'] == instanceId and item['previousState']['name'] == previousState:
#                         return ctEvent['eventTime']
    
#     return None

# def getInstanceHoursFromCloudTailEvents(instanceId):
#     totalMinutes = 0

#     eventData = []

#     paginator = ct_client.get_paginator('lookup_events')
#     StartingToken = None
    
#     page_iterator = paginator.paginate(
#     	LookupAttributes=[{'AttributeKey':'ResourceName','AttributeValue': instanceId}],
#     	PaginationConfig={'PageSize':50, 'StartingToken':StartingToken },
#         StartTime=datetime.utcnow().replace(day=1,hour=0,minute=0,second=0),
#         EndTime=datetime.utcnow()
#         )
#     for page in page_iterator:
#         for evt in page['Events']:
#             if evt['EventName'] == "RunInstances":
#                 ctEvent = json.loads(evt['CloudTrailEvent'])
#                 eventData.append({'s': 'StartInstances', 'x': ctEvent['eventTime'] })
                
#             if evt['EventName'] == "StartInstances":
#                 startEvent = extractStateEventTime(evt,"stopped",instanceId)
#                 if startEvent is not None:
#                     eventData.append({'s': 'StartInstances', 'x': startEvent })

#             if evt['EventName'] == "StopInstances":
#                 stopEvent = extractStateEventTime(evt,"running",instanceId) 
#                 if stopEvent is not None:
#                     eventData.append({'s': 'StopInstances', 'x': stopEvent })
 
#     data_points = sorted(eventData, key=lambda k : k['x'])
    
#     dtStartEvent = None
#     dtStopEvent = None
#     for point in data_points:
#         if point['s'] == "StartInstances":
#             dtStartEvent = datetime.fromisoformat(point['x'].replace("Z", "+00:00"))
#             continue
#         elif point['s'] == "StopInstances":
#             if isinstance(dtStartEvent, datetime):
#                 dtStopEvent = datetime.fromisoformat(point['x'].replace("Z", "+00:00"))
#             else:
#                 # Instance started before the beginning of the month
#                 dtStartEvent = datetime.now().replace(day=1,hour=0,minute=0,second=0)
#                 dtStopEvent = datetime.fromisoformat(point['x'].replace("Z", "+00:00")).replace(tzinfo=None)

#         if isinstance(dtStartEvent, datetime) and isinstance(dtStopEvent, datetime):
#             delta = dtStopEvent.replace(tzinfo=None) - dtStartEvent.replace(tzinfo=None)
#             #print(instanceId + ' s:' + dtStartEvent.strftime("%m/%d/%Y - %H:%M:%S") + ' - e:' + dtStopEvent.strftime("%m/%d/%Y - %H:%M:%S") + ' = ' + str(round(delta.total_seconds()/60,2)))
#             totalMinutes = totalMinutes + round(delta.total_seconds()/60,2)
#             dtStartEvent = None
#             dtStopEvent = None

#     # in case the instance is still running
#     if isinstance(dtStartEvent, datetime) and not isinstance(dtStopEvent, datetime):
#             dtStopEvent = datetime.utcnow()
#             delta = dtStopEvent.replace(tzinfo=None) - dtStartEvent.replace(tzinfo=None)
#             #print(instanceId + ' s:' + dtStartEvent.strftime("%m/%d/%Y - %H:%M:%S") + ' - e:' + dtStopEvent.strftime("%m/%d/%Y - %H:%M:%S") + ' = ' + str(round(delta.total_seconds()/60,2)))
#             totalMinutes = totalMinutes + round(delta.total_seconds()/60,2)
#             dtStartEvent = None
#             dtStopEvent = None                               
                    
#     return totalMinutes

def handler(event, context):
      
    try:
        if 'request' in event:
            if 'headers' in event['request']:
                if 'authorization' in event['request']['headers']:
                    # Get JWT token from header
                    token = event['request']['headers']['authorization']
                else:
                    logger.error("No Authorization header found")
                    return "No Authorization header found"
            else:
                logger.error("No headers found in request")
                return "No headers found in request"
        else:
            logger.error("No request found in event")
            return "No request found in event"
    except Exception as e:
        logger.error(f"Error processing request: {e}")
        return f"Error processing request: {e}"

    # Get user info
    user_attributes = auth.process_token(token)

    # Check if claims are valid
    if user_attributes is None:
        logger.error("Invalid Token")
        return "Invalid Token"

    # Get all servers in a single API call
    all_servers = utl.list_all_servers()  
    reservations = all_servers["Reservations"]

    if not reservations["Instances"]:
        logger.error("No Instances Found")
        return "No Instances Found"

    # Fetch instance types and status in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        instance_types = {executor.submit(ec2_client.describe_instance_types, InstanceTypes=[instance['InstanceType']]): instance for instance in [server for server in reservations["Instances"]]}
        instance_status = {executor.submit(utl.describe_instance_status, instance['InstanceId']): instance for instance in [server for server in reservations["Instances"]]}

    listServer_result = []
    for server in reservations["Instances"]:
        instance_id = server['InstanceId']
        logger.info(instance_id)
        launchTime = server["LaunchTime"]
        instance_type_future = next(future for future in instance_types if future.result()['InstanceTypes'][0]['InstanceType'] == server['InstanceType'])
        instance_type = instance_type_future.result()
        instance_status_future = next(future for future in instance_status if future.result()['instanceId'] == instance_id)
        status = instance_status_future.result()

        instance_name = next((tag['Value'] for tag in server['Tags'] if tag['Key'] == 'Name'), 'Undefined')
        public_ip = server['NetworkInterfaces'][0].get('Association', {}).get('PublicIp', 'none')
        vcpus = instance_type['InstanceTypes'][0]['VCpuInfo']['DefaultVCpus']
        memory_info = instance_type['InstanceTypes'][0]['MemoryInfo']['SizeInMiB']
        volume_id = server['BlockDeviceMappings'][0]['Ebs']['VolumeId']
        volume = ec2.Volume(volume_id)

        pstLaunchTime = launchTime.astimezone(pst)        
        runningMinutes = utl.get_total_hours_running_per_month(instance_id)
        groupMembers = []

        listServer_result.append({
            'id': instance_id,
            'name': instance_name,
            'userEmail': user_attributes['email'],
            'type': server['InstanceType'],
            'state': server['State']['Name'].lower(),
            'vCpus': vcpus,
            'memSize': memory_info,
            'diskSize': volume.size,
            'publicIp': public_ip,
            'initStatus': status['initStatus'].lower(),
            'iamStatus': status['iamStatus'].lower(),
            'launchTime': pstLaunchTime.strftime("%m/%d/%Y - %H:%M:%S"),
            'runningMinutes': runningMinutes,
            'groupMembers': groupMembers
        })

    logger.info(listServer_result)
    return listServer_result
