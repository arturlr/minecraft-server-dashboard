import boto3
import logging
import os
import concurrent.futures
import authHelper
import ec2Helper
import utilHelper
import ddbHelper
import pytz

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ec2_client = boto3.client('ec2')
ec2 = boto3.resource('ec2')
cognito_idp = boto3.client('cognito-idp')
ENCODING = 'utf-8'

appValue = os.getenv('TAG_APP_VALUE')
cognito_pool_id = os.getenv('COGNITO_USER_POOL_ID')
servers_table_name = os.getenv('SERVERS_TABLE_NAME')

auth = authHelper.Auth(cognito_pool_id)
ec2_utils = ec2Helper.Ec2Utils()
utl = utilHelper.Utils()
ddb = ddbHelper.Dyn(servers_table_name)
utc = pytz.utc
pst = pytz.timezone('US/Pacific')

# Import error handling utilities
try:
    from utilHelper.errorHandler import ErrorHandler
except ImportError:
    # Fallback for local testing
    import sys
    sys.path.insert(0, '../utilHelper')
    from errorHandler import ErrorHandler


def get_user_instances(user_sub, app_value):
    """Get instances based on user permissions using DynamoDB membership."""
    try:
        from ddbHelper import CoreTableDyn
        
        core_dyn = CoreTableDyn()
        
        # Check if user has global admin role
        if core_dyn.check_global_admin(user_sub):
            logger.info(f"Global admin user - listing all instances by app tag: {app_value}")
            user_instances = ec2_utils.list_instances_by_app_tag(app_value)
            logger.info(f"Found {user_instances['TotalInstances']} instances with App={app_value}")
            return user_instances
        
        # Get user server memberships
        user_data = core_dyn.get_user_permissions(user_sub)
        user_memberships = user_data.get('server_roles', [])
        
        if not user_memberships:
            logger.info(f"User has no server memberships: {user_sub}")
            return {
                "Instances": [],
                "TotalInstances": 0
            }

        # Get instances for servers where user has membership
        server_ids = [membership['serverId'] for membership in user_memberships]
        logger.info(f"User has membership for servers: {server_ids}")
        
        # Get instance details for each server the user has access to
        user_instances = []
        for server_id in server_ids:
            try:
                response = ec2_client.describe_instances(InstanceIds=[server_id])
                if response["Reservations"]:
                    for reservation in response["Reservations"]:
                        for instance in reservation["Instances"]:
                            # Verify instance has the correct app tag
                            tags = instance.get('Tags', [])
                            app_tag = next((tag['Value'] for tag in tags if tag['Key'] == 'App'), None)
                            if app_tag == app_value:
                                user_instances.append(instance)
                            else:
                                logger.warning(f"Instance {server_id} does not have App={app_value} tag")
            except Exception as e:
                logger.error(f"Error getting instance {server_id}: {str(e)}")
                continue
        
        total_instances = len(user_instances)
        logger.info(f"Found {total_instances} instances for user memberships")
        
        return {
            "Instances": user_instances,
            "TotalInstances": total_instances
        }
            
    except Exception as e:
        logger.error(f"Error retrieving user instances: {str(e)}")
        raise ValueError(f"Error retrieving user instances: {str(e)}")

def get_server_validation(instance_id):
    """Get stored server configuration validation from DynamoDB."""
    try:
        from ddbHelper import CoreTableDyn
        
        core_dyn = CoreTableDyn()
        # Get stored validation results from serverBootProcessor
        server_info = core_dyn.get_server_info(instance_id)
        
        if server_info:
            return {
                'instanceId': instance_id,
                'configStatus': server_info.get('configStatus', 'unknown'),
                'isValid': server_info.get('configValid', False),
                'warnings': server_info.get('configWarnings', []),
                'errors': server_info.get('configErrors', []),
                'autoConfigured': server_info.get('autoConfigured', False)
            }
        
        # Fallback if no server info found (server not processed by serverBootProcessor yet)
        return {
            'instanceId': instance_id,
            'configStatus': 'pending',
            'isValid': False,
            'warnings': ['Server validation pending'],
            'errors': [],
            'autoConfigured': False
        }
        
    except Exception as e:
        logger.error(f"Error retrieving server validation for {instance_id}: {str(e)}")
        return {
            'instanceId': instance_id,
            'configStatus': 'error',
            'isValid': False,
            'warnings': [],
            'errors': [f"Validation retrieval error: {str(e)}"],
            'autoConfigured': False
        }

def fetch_parallel_data(instances):
    """Fetch instance data in parallel using ThreadPoolExecutor."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        instance_types = {executor.submit(ec2_client.describe_instance_types, InstanceTypes=[instance['InstanceType']]): instance for instance in instances}
        instance_status = {executor.submit(ec2_utils.describe_instance_status, instance['InstanceId']): instance for instance in instances}
        config_validation = {executor.submit(get_server_validation, instance['InstanceId']): instance for instance in instances}
    
    return instance_types, instance_status, config_validation

def build_server_response(server, instance_types, instance_status, config_validation, user_email):
    """Build individual server response object."""
    instance_id = server['InstanceId']
    
    # Get parallel execution results
    instance_type_future = next(future for future in instance_types if future.result()['InstanceTypes'][0]['InstanceType'] == server['InstanceType'])
    instance_type = instance_type_future.result()
    instance_status_future = next(future for future in instance_status if future.result()['instanceId'] == instance_id)
    status = instance_status_future.result()
    config_validation_future = next(future for future in config_validation if future.result()['instanceId'] == instance_id)
    validation = config_validation_future.result()

    # Extract server details
    instance_name = next((tag['Value'] for tag in server['Tags'] if tag['Key'] == 'Name'), 'Undefined')
    public_ip = server['NetworkInterfaces'][0].get('Association', {}).get('PublicIp', 'none')
    vcpus = instance_type['InstanceTypes'][0]['VCpuInfo']['DefaultVCpus']
    memory_info = instance_type['InstanceTypes'][0]['MemoryInfo']['SizeInMiB']
    volume_id = server['BlockDeviceMappings'][0]['Ebs']['VolumeId']
    volume = ec2.Volume(volume_id)
    
    pst_launch_time = server["LaunchTime"].astimezone(pst)
    running_time_data = ec2_utils.get_cached_running_minutes(instance_id)

    return {
        'id': instance_id,
        'name': instance_name,
        'userEmail': user_email,
        'type': server['InstanceType'],
        'state': server['State']['Name'].lower(),
        'vCpus': vcpus,
        'memSize': memory_info,
        'diskSize': volume.size,
        'publicIp': public_ip,
        'initStatus': status['initStatus'].lower(),
        'iamStatus': status['iamStatus'].lower(),
        'launchTime': pst_launch_time.strftime("%m/%d/%Y - %H:%M:%S"),
        'runningMinutes': str(running_time_data['minutes']),
        'runningMinutesCacheTimestamp': running_time_data['timestamp'] or '',
        'configStatus': validation['configStatus'],
        'configValid': validation['isValid'],
        'configWarnings': validation['warnings'],
        'configErrors': validation['errors'],
        'autoConfigured': validation.get('autoConfigured', False)
    }

def handler(event, context): 
    try:
        # Extract and validate token
        token = utl.extract_auth_token(event)
        user_attributes = auth.process_token(token)
        
        # Get user sub for DynamoDB membership queries
        user_sub = user_attributes.get('sub')
        if not user_sub:
            ErrorHandler.log_error('VALIDATION_ERROR',
                                 context={'operation': 'handler'},
                                 error='No user sub found in token')
            return "Invalid user token - missing sub"
        
        # Get user instances using DynamoDB membership
        user_instances = get_user_instances(user_sub, appValue)
        
        if user_instances["TotalInstances"] == 0:
            logger.info(f"No servers found for user {user_sub}")
            return []
        
        # Fetch data in parallel
        instances = user_instances["Instances"]
        instance_types, instance_status, config_validation = fetch_parallel_data(instances)
        
        # Build response
        result = []
        for server in instances:
            try:
                server_data = build_server_response(server, instance_types, instance_status, config_validation, user_attributes['email'])
                result.append(server_data)
            except Exception as e:
                # Log error but continue processing other servers
                ErrorHandler.log_error('INTERNAL_ERROR',
                                     context={'operation': 'build_server_response', 'instance_id': server.get('InstanceId', 'unknown')},
                                     exception=e, error=str(e))
                continue
        
        logger.info(result)
        return result
        
    except ValueError as e:
        ErrorHandler.log_error('VALIDATION_ERROR',
                             context={'operation': 'handler'},
                             exception=e, error=str(e))
        return str(e)
    except Exception as e:
        ErrorHandler.log_error('INTERNAL_ERROR',
                             context={'operation': 'handler'},
                             exception=e, error=str(e))
        return f"Error processing request: {e}"
