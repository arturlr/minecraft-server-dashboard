import boto3
import logging
import os
from datetime import datetime, timezone
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key, Attr

logger = logging.getLogger()
logger.setLevel(logging.INFO)

session = boto3.session.Session()
aws_region = session.region_name

class Dyn:
    def __init__(self):
        logger.info("------- Dyn Class Initialization")
        dynamodb = boto3.resource('dynamodb', region_name=aws_region)
        serversTable = os.getenv('SERVERS_TABLE_NAME')
        self.table = dynamodb.Table(serversTable)

    def get_server_config(self, instance_id):
        """
        Get server configuration from DynamoDB.
        
        Args:
            instance_id (str): The EC2 instance ID
            
        Returns:
            dict: Server configuration matching ServerConfig GraphQL type
        """
        try:
            logger.info(f"get_server_config: {instance_id}")
            response = self.table.get_item(Key={'id': instance_id})
            
            if 'Item' in response:
                item = response['Item']
                # Return config matching GraphQL ServerConfig schema
                return {
                    'id': instance_id,
                    'shutdownMethod': item.get('shutdownMethod', ''),
                    'stopScheduleExpression': item.get('stopScheduleExpression', ''),
                    'startScheduleExpression': item.get('startScheduleExpression', ''),
                    'alarmThreshold': float(item.get('alarmThreshold', 0.0)) if item.get('alarmThreshold') else 0.0,
                    'alarmEvaluationPeriod': int(item.get('alarmEvaluationPeriod', 0)) if item.get('alarmEvaluationPeriod') else 0,
                    'runCommand': item.get('runCommand', ''),
                    'workDir': item.get('workDir', ''),
                    'timezone': item.get('timezone', 'UTC'),
                    'isBootstrapped': bool(item.get('isBootstrapped', False)),
                    'minecraftVersion': item.get('minecraftVersion', ''),
                    'latestPatchUpdate': item.get('latestPatchUpdate', '')
                }
            else:
                logger.info(f"Server config not found for {instance_id}")
                return None

        except ClientError as e:
            logger.error(f"Error getting server config: {e.response['Error']['Message']}")
            raise

    def put_server_config(self, config):
        """
        Save complete server configuration to DynamoDB.
        
        Args:
            config (dict): Server configuration matching ServerConfigInput GraphQL type
            
        Returns:
            dict: Saved configuration
        """
        try:
            instance_id = config.get('id')
            if not instance_id:
                raise ValueError("Instance ID is required")
                
            logger.info(f"put_server_config: {instance_id}")
            
            # Build item with all fields
            item = {
                'id': instance_id,
                'shutdownMethod': config.get('shutdownMethod', ''),
                'stopScheduleExpression': config.get('stopScheduleExpression', ''),
                'startScheduleExpression': config.get('startScheduleExpression', ''),
                'alarmThreshold': config.get('alarmThreshold', 0.0),
                'alarmEvaluationPeriod': config.get('alarmEvaluationPeriod', 0),
                'runCommand': config.get('runCommand', ''),
                'workDir': config.get('workDir', ''),
                'timezone': config.get('timezone', 'UTC'),
                'isBootstrapped': config.get('isBootstrapped', False),
                'minecraftVersion': config.get('minecraftVersion', ''),
                'latestPatchUpdate': config.get('latestPatchUpdate', ''),
                'updatedAt': datetime.now(timezone.utc).isoformat()
            }
            
            # Preserve createdAt if it exists, otherwise set it
            if 'createdAt' in config:
                item['createdAt'] = config['createdAt']
            else:
                item['createdAt'] = datetime.now(timezone.utc).isoformat()
            
            # Preserve autoConfigured flag if it exists
            if 'autoConfigured' in config:
                item['autoConfigured'] = config['autoConfigured']
            
            # Remove empty strings to keep table clean (but keep timestamps and booleans)
            item = {k: v for k, v in item.items() if v != '' or k in ['createdAt', 'updatedAt', 'isBootstrapped', 'autoConfigured']}
            
            self.table.put_item(Item=item)
            logger.info(f"Server config saved for {instance_id}")
            
            return config

        except ClientError as e:
            logger.error(f"Error saving server config: {e.response['Error']['Message']}")
            raise

    def update_server_config(self, config):
        """
        Update specific fields in server configuration.
        
        Args:
            config (dict): Partial server configuration with id and fields to update
            
        Returns:
            dict: Updated configuration
        """
        try:
            instance_id = config.get('id')
            if not instance_id:
                raise ValueError("Instance ID is required")
                
            logger.info(f"update_server_config: {instance_id}")
            
            # Build update expression dynamically
            update_parts = []
            expression_values = {}
            expression_names = {}
            
            field_mapping = {
                'shutdownMethod': 'shutdownMethod',
                'stopScheduleExpression': 'stopScheduleExpression',
                'startScheduleExpression': 'startScheduleExpression',
                'alarmThreshold': 'alarmThreshold',
                'alarmEvaluationPeriod': 'alarmEvaluationPeriod',
                'runCommand': 'runCommand',
                'workDir': 'workDir',
                'timezone': 'timezone',
                'isBootstrapped': 'isBootstrapped',
                'minecraftVersion': 'minecraftVersion',
                'latestPatchUpdate': 'latestPatchUpdate',
                'autoConfigured': 'autoConfigured'
            }
            
            for key, attr_name in field_mapping.items():
                if key in config and config[key] is not None:
                    placeholder = f":{key}"
                    name_placeholder = f"#{key}"
                    update_parts.append(f"{name_placeholder} = {placeholder}")
                    expression_values[placeholder] = config[key]
                    expression_names[name_placeholder] = attr_name
            
            # Always update timestamp
            update_parts.append("#updatedAt = :updatedAt")
            expression_values[':updatedAt'] = datetime.now(timezone.utc).isoformat()
            expression_names['#updatedAt'] = 'updatedAt'
            
            # Set createdAt if it doesn't exist (for legacy records)
            update_parts.append("#createdAt = if_not_exists(#createdAt, :createdAt)")
            expression_values[':createdAt'] = datetime.now(timezone.utc).isoformat()
            expression_names['#createdAt'] = 'createdAt'
            
            if not update_parts:
                logger.warning("No fields to update")
                return self.get_server_config(instance_id)
            
            update_expression = "SET " + ", ".join(update_parts)
            
            response = self.table.update_item(
                Key={'id': instance_id},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values,
                ExpressionAttributeNames=expression_names,
                ReturnValues="ALL_NEW"
            )
            
            logger.info(f"Server config updated for {instance_id}")
            return self.get_server_config(instance_id)

        except ClientError as e:
            logger.error(f"Error updating server config: {e.response['Error']['Message']}")
            raise


