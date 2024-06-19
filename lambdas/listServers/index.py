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
            'runningMinutes': runningMinutes
        })

    logger.info(listServer_result)
    return listServer_result
