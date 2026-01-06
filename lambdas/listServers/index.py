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

def create_default_config(instance_id):
    """Creates and applies default configuration for an instance."""
    default_config = {
        'id': instance_id,
        'shutdownMethod': 'CPUUtilization',
        'alarmThreshold': 5.0,
        'alarmEvaluationPeriod': 30,
        'runCommand': 'java -Xmx2G -Xms1G -jar server.jar nogui',
        'workDir': '/home/minecraft/server',
        'autoConfigured': True
    }
    
    ddb.put_server_config(default_config)
    ec2_utils.update_alarm(
        instance_id, 
        'CPUUtilization', 
        default_config['alarmThreshold'], 
        default_config['alarmEvaluationPeriod']
    )
    return default_config

def validate_shutdown_config(config, validation_result):
    """Validates shutdown method configuration."""
    shutdown_method = config.get('shutdownMethod', '')
    
    if shutdown_method == 'Schedule':
        stop_schedule = config.get('stopScheduleExpression', '')
        if not stop_schedule:
            validation_result['errors'].append('Schedule shutdown method selected but no stop schedule expression configured')
            validation_result['isValid'] = False
            validation_result['configStatus'] = 'invalid'
        
        start_schedule = config.get('startScheduleExpression', '')
        if stop_schedule and not start_schedule:
            validation_result['warnings'].append('Stop schedule configured but no start schedule - server will need manual start')
            
    elif shutdown_method in ['CPUUtilization', 'Connections']:
        alarm_threshold = config.get('alarmThreshold', 0.0)
        alarm_evaluation_period = config.get('alarmEvaluationPeriod', 0)
        
        if alarm_threshold <= 0:
            validation_result['errors'].append(f'Invalid alarm threshold: {alarm_threshold}. Must be greater than 0')
            validation_result['isValid'] = False
            validation_result['configStatus'] = 'invalid'
            
        if alarm_evaluation_period <= 0:
            validation_result['errors'].append(f'Invalid evaluation period: {alarm_evaluation_period}. Must be greater than 0')
            validation_result['isValid'] = False
            validation_result['configStatus'] = 'invalid'

def apply_minecraft_config(instance_id, config, validation_result):
    """Applies default Minecraft configuration if missing."""
    minecraft_config_updates = {}
    
    if not config.get('runCommand', ''):
        minecraft_config_updates['runCommand'] = 'java -Xmx2G -Xms1G -jar server.jar nogui'
        
    if not config.get('workDir', ''):
        minecraft_config_updates['workDir'] = '/home/minecraft/server'
    
    if minecraft_config_updates:
        minecraft_config_updates['id'] = instance_id
        ddb.update_server_config(minecraft_config_updates)
        
        validation_result['autoConfigured'] = True
        config_items = []
        if 'runCommand' in minecraft_config_updates:
            config_items.append('run command')
        if 'workDir' in minecraft_config_updates:
            config_items.append('working directory')
            
        validation_result['warnings'].append(f'Default Minecraft server configuration applied: {", ".join(config_items)}')
        
        if validation_result['configStatus'] == 'complete':
            validation_result['configStatus'] = 'auto-configured'
            
        logger.info(f"Applied default Minecraft configuration to {instance_id}: {config_items}")

def check_missing_minecraft_config(config, validation_result):
    """Adds warnings for missing Minecraft configuration."""
    if not config.get('runCommand', ''):
        validation_result['warnings'].append('No run command configured for Minecraft server')
        if validation_result['configStatus'] == 'complete':
            validation_result['configStatus'] = 'incomplete'
            
    if not config.get('workDir', ''):
        validation_result['warnings'].append('No working directory configured for Minecraft server')
        if validation_result['configStatus'] == 'complete':
            validation_result['configStatus'] = 'incomplete'

def validate_aws_resources(instance_id, config, validation_result):
    """Validates that AWS resources exist for the configuration."""
    if config.get('shutdownMethod') == 'Schedule':
        rules_status = ec2_utils.check_eventbridge_rules_exist(instance_id)
        if not rules_status['shutdown_rule_exists']:
            validation_result['errors'].append('Shutdown EventBridge rule not found')
            validation_result['isValid'] = False
            if validation_result['configStatus'] == 'complete':
                validation_result['configStatus'] = 'invalid'
        
        start_schedule = config.get('startScheduleExpression', '')
        if start_schedule and not rules_status['start_rule_exists']:
            validation_result['errors'].append('Start EventBridge rule not found')
            validation_result['isValid'] = False
            if validation_result['configStatus'] == 'complete':
                validation_result['configStatus'] = 'invalid'
                
    elif config.get('shutdownMethod') in ['CPUUtilization', 'Connections']:
        if not ec2_utils.check_alarm_exists(instance_id):
            validation_result['errors'].append('CloudWatch alarm not found')
            validation_result['isValid'] = False
            if validation_result['configStatus'] == 'complete':
                validation_result['configStatus'] = 'invalid'

def validate_and_configure_instance_config(instance_id):
    """
    Validates that instance has proper shutdown configuration in DynamoDB.
    If no shutdown configuration exists, applies default configuration.
    Returns validation status and any missing/invalid configurations.
    """
    try:
        logger.info(f"Validating and configuring DynamoDB config for instance: {instance_id}")
        
        config = ddb.get_server_config(instance_id)
        
        validation_result = {
            'instanceId': instance_id,
            'isValid': True,
            'warnings': [],
            'errors': [],
            'configStatus': 'complete',
            'autoConfigured': False
        }
        
        if not config:
            logger.info(f"No configuration found for {instance_id}, creating default configuration")
            try:
                create_default_config(instance_id)
                validation_result['autoConfigured'] = True
                validation_result['warnings'].append('Default shutdown configuration applied: CPU-based (5% threshold, 30min evaluation)')
                validation_result['configStatus'] = 'auto-configured'
                logger.info(f"Successfully applied default configuration to {instance_id}")
            except Exception as config_error:
                logger.error(f"Failed to apply default configuration to {instance_id}: {config_error}")
                validation_result['errors'].append(f'Failed to apply default configuration: {str(config_error)}')
                validation_result['isValid'] = False
                validation_result['configStatus'] = 'configuration-failed'
        else:
            validate_shutdown_config(config, validation_result)
            
            try:
                apply_minecraft_config(instance_id, config, validation_result)
            except Exception as minecraft_config_error:
                logger.error(f"Failed to apply Minecraft configuration to {instance_id}: {minecraft_config_error}")
                validation_result['warnings'].append(f'Failed to apply default Minecraft configuration: {str(minecraft_config_error)}')
            
            if not validation_result.get('autoConfigured', False):
                check_missing_minecraft_config(config, validation_result)
        
        if config:
            validate_aws_resources(instance_id, config, validation_result)
        
        # Log validation summary
        if validation_result['errors']:
            logger.warning(f"Config validation for {instance_id} has errors: {validation_result['errors']}")
        elif validation_result['warnings']:
            logger.info(f"Config validation for {instance_id} has warnings: {validation_result['warnings']}")
        else:
            logger.info(f"Config validation for {instance_id} completed successfully: {validation_result['configStatus']}")
            
        return validation_result
        
    except Exception as e:
        logger.error(f"Error validating configuration for instance {instance_id}: {e}")
        return {
            'instanceId': instance_id,
            'isValid': False,
            'warnings': [],
            'errors': [f'Failed to validate configuration: {str(e)}'],
            'configStatus': 'error'
        }

def extract_auth_token(event):
    """Extract authorization token from event with proper error handling."""
    try:
        return event['request']['headers']['authorization']
    except KeyError as e:
        if 'request' not in event:
            raise ValueError("No request found in event")
        elif 'headers' not in event['request']:
            raise ValueError("No headers found in request")
        else:
            raise ValueError("No Authorization header found")

def get_user_instances(cognito_groups, app_value):
    """Get instances based on user permissions."""
    if utl.is_admin_user(cognito_groups):
        logger.info(f"Admin user - listing all instances by app tag: {app_value}")
        user_instances = ec2_utils.list_instances_by_app_tag(app_value)
        logger.info(f"Found {user_instances['TotalInstances']} instances with App={app_value}")
        return user_instances
    elif cognito_groups:
        user_instances = ec2_utils.list_instances_by_user_group(cognito_groups)
        logger.info(user_instances)
        return user_instances
    else:
        raise ValueError("No Cognito Groups found")

def fetch_parallel_data(instances):
    """Fetch instance data in parallel using ThreadPoolExecutor."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        instance_types = {executor.submit(ec2_client.describe_instance_types, InstanceTypes=[instance['InstanceType']]): instance for instance in instances}
        instance_status = {executor.submit(ec2_utils.describe_instance_status, instance['InstanceId']): instance for instance in instances}
        tag_validation = {executor.submit(validate_and_configure_instance_config, instance['InstanceId']): instance for instance in instances}
    
    return instance_types, instance_status, tag_validation

def build_server_response(server, instance_types, instance_status, tag_validation, user_email):
    """Build individual server response object."""
    instance_id = server['InstanceId']
    
    # Get parallel execution results
    instance_type_future = next(future for future in instance_types if future.result()['InstanceTypes'][0]['InstanceType'] == server['InstanceType'])
    instance_type = instance_type_future.result()
    instance_status_future = next(future for future in instance_status if future.result()['instanceId'] == instance_id)
    status = instance_status_future.result()
    tag_validation_future = next(future for future in tag_validation if future.result()['instanceId'] == instance_id)
    validation = tag_validation_future.result()

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
        token = authHelper.extract_auth_token(event)
        user_attributes = authHelper.validate_user_token(token, auth)
        
        # Get user instances
        cognito_groups = event["identity"].get("groups", [])
        user_instances = get_user_instances(cognito_groups, appValue)
        
        if user_instances["TotalInstances"] == 0:
            logger.error(f"No Servers Found with App={appValue}")
            return []
        
        # Fetch data in parallel
        instances = user_instances["Instances"]
        instance_types, instance_status, tag_validation = fetch_parallel_data(instances)
        
        # Build response
        result = []
        for server in instances:
            server_data = build_server_response(server, instance_types, instance_status, tag_validation, user_attributes['email'])
            result.append(server_data)
        
        logger.info(result)
        return result
        
    except ValueError as e:
        logger.error(str(e))
        return str(e)
    except Exception as e:
        logger.error(f"Error processing request: {e}")
        return f"Error processing request: {e}"
