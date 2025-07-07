import boto3
import logging
import os
import concurrent.futures
import authHelper
import ec2Helper
import utilHelper
import pytz

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ec2_client = boto3.client('ec2')
ec2 = boto3.resource('ec2')
cognito_idp = boto3.client('cognito-idp')
ENCODING = 'utf-8'

appValue = os.getenv('TAG_APP_VALUE')
cognito_pool_id = os.getenv('COGNITO_USER_POOL_ID')

auth = authHelper.Auth(cognito_pool_id)
ec2_utils = ec2Helper.Ec2Utils()
utl = utilHelper.Utils()
utc = pytz.utc
pst = pytz.timezone('US/Pacific')

def validate_and_configure_instance_tags(instance_id):
    """
    Validates that instance has proper shutdown configuration tags.
    If no shutdown configuration exists, applies default configuration.
    Returns validation status and any missing/invalid configurations.
    """
    try:
        logger.info(f"Validating and configuring tags for instance: {instance_id}")
        
        # Get instance attributes from tags using ec2Helper
        config = ec2_utils.get_instance_attributes_from_tags(instance_id)
        
        validation_result = {
            'instanceId': instance_id,
            'isValid': True,
            'warnings': [],
            'errors': [],
            'configStatus': 'complete',
            'autoConfigured': False
        }
        
        shutdown_method = config.get('shutdownMethod', '')
        
        # Check if shutdown method is configured
        if not shutdown_method:
            logger.info(f"No shutdown method configured for {instance_id}, applying default configuration")
            
            # Apply default shutdown configuration
            default_config = {
                'id': instance_id,
                'shutdownMethod': 'CPUUtilization',
                'alarmThreshold': 5.0,  # 5% CPU threshold
                'alarmEvaluationPeriod': 30,  # 30 minutes
                'alarmType': 'CPUUtilization',
                'runCommand': 'java -Xmx2G -Xms1G -jar server.jar nogui',
                'workDir': '/home/minecraft/server'
            }
            
            try:
                # Set the default configuration using ec2Helper
                ec2_utils.set_instance_attributes_to_tags(default_config)
                
                # Update the alarm configuration
                ec2_utils.update_alarm(
                    instance_id, 
                    'CPUUtilization', 
                    default_config['alarmThreshold'], 
                    default_config['alarmEvaluationPeriod']
                )
                
                validation_result['autoConfigured'] = True
                validation_result['warnings'].append('Default shutdown configuration applied: CPU-based (5% threshold, 30min evaluation)')
                validation_result['configStatus'] = 'auto-configured'
                
                logger.info(f"Successfully applied default configuration to {instance_id}")
                
            except Exception as config_error:
                logger.error(f"Failed to apply default configuration to {instance_id}: {config_error}")
                validation_result['errors'].append(f'Failed to apply default configuration: {str(config_error)}')
                validation_result['isValid'] = False
                validation_result['configStatus'] = 'configuration-failed'
        elif shutdown_method == 'Schedule':
            # Validate schedule-based configuration
            stop_schedule = config.get('stopScheduleExpression', '')
            if not stop_schedule:
                validation_result['errors'].append('Schedule shutdown method selected but no stop schedule expression configured')
                validation_result['isValid'] = False
                validation_result['configStatus'] = 'invalid'
            
            # Check if start schedule is configured when stop schedule exists
            start_schedule = config.get('startScheduleExpression', '')
            if stop_schedule and not start_schedule:
                validation_result['warnings'].append('Stop schedule configured but no start schedule - server will need manual start')
                
        elif shutdown_method in ['CPUUtilization', 'Connections']:
            # Validate metric-based configuration
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
        
        # Check and configure Minecraft server execution if needed
        needs_minecraft_config = False
        minecraft_config_updates = {}
        
        run_command = config.get('runCommand', '')
        work_dir = config.get('workDir', '')
        
        if not run_command:
            minecraft_config_updates['runCommand'] = 'java -Xmx2G -Xms1G -jar server.jar nogui'
            needs_minecraft_config = True
            
        if not work_dir:
            minecraft_config_updates['workDir'] = '/home/minecraft/server'
            needs_minecraft_config = True
        
        # Apply Minecraft server configuration if needed
        if needs_minecraft_config and not validation_result.get('autoConfigured', False):
            try:
                minecraft_config_updates['id'] = instance_id
                ec2_utils.set_instance_attributes_to_tags(minecraft_config_updates)
                
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
                
            except Exception as minecraft_config_error:
                logger.error(f"Failed to apply Minecraft configuration to {instance_id}: {minecraft_config_error}")
                validation_result['warnings'].append(f'Failed to apply default Minecraft configuration: {str(minecraft_config_error)}')
        
        # Add warnings for missing configuration (if not auto-configured)
        elif not validation_result.get('autoConfigured', False):
            if not run_command:
                validation_result['warnings'].append('No run command configured for Minecraft server')
                if validation_result['configStatus'] == 'complete':
                    validation_result['configStatus'] = 'incomplete'
                    
            if not work_dir:
                validation_result['warnings'].append('No working directory configured for Minecraft server')
                if validation_result['configStatus'] == 'complete':
                    validation_result['configStatus'] = 'incomplete'
        
        # Check if actual AWS resources exist
        if shutdown_method == 'Schedule':
            # Check EventBridge rules
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
                    
        elif shutdown_method in ['CPUUtilization', 'Connections']:
            # Check CloudWatch alarm
            if not ec2_utils.check_alarm_exists(instance_id):
                validation_result['errors'].append('CloudWatch alarm not found')
                validation_result['isValid'] = False
                if validation_result['configStatus'] == 'complete':
                    validation_result['configStatus'] = 'invalid'
        
        # Log validation summary
        if validation_result['errors']:
            logger.warning(f"Tag validation for {instance_id} has errors: {validation_result['errors']}")
        elif validation_result['warnings']:
            logger.info(f"Tag validation for {instance_id} has warnings: {validation_result['warnings']}")
        else:
            logger.info(f"Tag validation for {instance_id} completed successfully: {validation_result['configStatus']}")
            
        return validation_result
        
    except Exception as e:
        logger.error(f"Error validating tags for instance {instance_id}: {e}")
        return {
            'instanceId': instance_id,
            'isValid': False,
            'warnings': [],
            'errors': [f'Failed to validate configuration: {str(e)}'],
            'configStatus': 'error'
        }

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
    
    # Get all instances the user has access from token
    cognitoGroups = event["identity"].get("groups", [])
    
    # Use the centralized admin check from utilHelper
    if utl.is_admin_user(cognitoGroups):
        user_instances = ec2_utils.list_instances_by_app_tag(appValue)
        logger.info("Admin user - listing all instances by app tag")
    elif cognitoGroups:
        user_instances = ec2_utils.list_instances_by_user_group(cognitoGroups)
        logger.info(user_instances)
    else:
        logger.error("No Cognito Groups found")
        return []

    if user_instances["TotalInstances"] == 0:
        logger.error("No Servers Found")
        return []  # Return empty array instead of string

    # Fetch instance types, status, and tag validation in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        instance_types = {executor.submit(ec2_client.describe_instance_types, InstanceTypes=[instance['InstanceType']]): instance for instance in [server for server in user_instances["Instances"]]}
        instance_status = {executor.submit(ec2_utils.describe_instance_status, instance['InstanceId']): instance for instance in [server for server in user_instances["Instances"]]}
        tag_validation = {executor.submit(validate_and_configure_instance_tags, instance['InstanceId']): instance for instance in [server for server in user_instances["Instances"]]}

    listServer_result = []
    for server in user_instances["Instances"]:
        instance_id = server['InstanceId']
        logger.info(instance_id)
        launchTime = server["LaunchTime"]
        instance_type_future = next(future for future in instance_types if future.result()['InstanceTypes'][0]['InstanceType'] == server['InstanceType'])
        instance_type = instance_type_future.result()
        instance_status_future = next(future for future in instance_status if future.result()['instanceId'] == instance_id)
        status = instance_status_future.result()
        tag_validation_future = next(future for future in tag_validation if future.result()['instanceId'] == instance_id)
        validation = tag_validation_future.result()

        instance_name = next((tag['Value'] for tag in server['Tags'] if tag['Key'] == 'Name'), 'Undefined')
        public_ip = server['NetworkInterfaces'][0].get('Association', {}).get('PublicIp', 'none')
        vcpus = instance_type['InstanceTypes'][0]['VCpuInfo']['DefaultVCpus']
        memory_info = instance_type['InstanceTypes'][0]['MemoryInfo']['SizeInMiB']
        volume_id = server['BlockDeviceMappings'][0]['Ebs']['VolumeId']
        volume = ec2.Volume(volume_id)

        pstLaunchTime = launchTime.astimezone(pst)        
        runningMinutes = ec2_utils.get_total_hours_running_per_month(instance_id)

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
            'configStatus': validation['configStatus'],
            'configValid': validation['isValid'],
            'configWarnings': validation['warnings'],
            'configErrors': validation['errors'],
            'autoConfigured': validation.get('autoConfigured', False)
        })

    logger.info(listServer_result)
    return listServer_result
