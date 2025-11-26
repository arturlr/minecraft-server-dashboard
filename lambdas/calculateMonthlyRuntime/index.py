import boto3
import logging
import os
import json
from datetime import datetime, timezone
from decimal import Decimal
import ec2Helper
import DynHelper

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ec2_utils = ec2Helper.Ec2Utils()
dyn = DynHelper.Dyn()

appValue = os.getenv('TAG_APP_VALUE')

def handler(event, context):
    """
    Calculate and cache monthly runtime hours for all servers.
    Triggered by EventBridge on a schedule (e.g., every hour).
    """
    logger.info("------- calculateMonthlyRuntime Lambda started")
    
    try:
        # Get all servers with the app tag
        servers = ec2_utils.list_instances_by_app_tag(appValue)
        
        if servers["TotalInstances"] == 0:
            logger.info("No servers found to process")
            return {
                'statusCode': 200,
                'body': json.dumps({'message': 'No servers found', 'processed': 0})
            }
        
        processed_count = 0
        error_count = 0
        
        for instance in servers["Instances"]:
            instance_id = instance["InstanceId"]
            
            try:
                logger.info(f"Calculating runtime for {instance_id}")
                
                # Calculate total running minutes for the month
                runtime_data = ec2_utils.get_total_hours_running_per_month(instance_id)
                running_minutes = runtime_data['minutes']
                
                # Get current timestamp
                cache_timestamp = datetime.now(timezone.utc).isoformat()
                
                # Update DynamoDB with cached value
                dyn.update_server_config({
                    'id': instance_id,
                    'runningMinutesCache': Decimal(str(running_minutes)),
                    'runningMinutesCacheTimestamp': cache_timestamp
                })
                
                logger.info(f"Cached runtime for {instance_id}: {running_minutes} minutes at {cache_timestamp}")
                processed_count += 1
                
            except Exception as e:
                logger.error(f"Error processing {instance_id}: {str(e)}", exc_info=True)
                error_count += 1
                # Continue processing other instances
        
        result = {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Monthly runtime calculation completed',
                'total_servers': servers["TotalInstances"],
                'processed': processed_count,
                'errors': error_count
            })
        }
        
        logger.info(f"Completed: {processed_count} processed, {error_count} errors")
        return result
        
    except Exception as e:
        logger.error(f"Fatal error in calculateMonthlyRuntime: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
