import boto3
import logging
import os
from datetime import datetime, timezone
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key, Attr
from decimal import Decimal

logger = logging.getLogger()
logger.setLevel(logging.INFO)

session = boto3.session.Session()
aws_region = session.region_name

class Dyn:

    def __init__(self, table_name=None):
        logger.info("------- DynamoDb Class Initialization")
        dynamodb = boto3.resource('dynamodb', region_name=aws_region)
        serversTable = table_name
        if not serversTable:
            # fallback to the oldwway
            serversTable = os.getenv('SERVERS_TABLE_NAME')
            if not serversTable:
                raise ValueError("SERVERS_TABLE_NAME environment variable not set")
        
        self.table = dynamodb.Table(serversTable)

    @staticmethod
    def _to_decimal(value):
        """
        Convert numeric values to Decimal for DynamoDB storage.
        
        Args:
            value: Numeric value or None
            
        Returns:
            Decimal: Converted value or None
        """
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return Decimal(str(value))
        return value

    @staticmethod
    def _safe_float(value, default=0.0):
        """
        Safely convert value to float, handling Decimal and None.
        
        Args:
            value: Value to convert (can be Decimal, int, float, or None)
            default: Default value if conversion fails or value is None
            
        Returns:
            float: Converted value or default
        """
        if value is None:
            return None if default is None else default
        try:
            return float(value)
        except (ValueError, TypeError):
            logger.warning(f"Could not convert {value} to float, using default {default}")
            return default

    @staticmethod
    def _safe_int(value, default=0):
        """
        Safely convert value to int, handling Decimal and None.
        
        Args:
            value: Value to convert (can be Decimal, int, float, or None)
            default: Default value if conversion fails or value is None
            
        Returns:
            int: Converted value or default
        """
        if value is None:
            return default
        try:
            return int(value)
        except (ValueError, TypeError):
            logger.warning(f"Could not convert {value} to int, using default {default}")
            return default

    def _convert_dynamodb_config_item(self, item, instance_id):
        """
        Convert DynamoDB item to ServerConfig format with proper type handling.
        
        Args:
            item (dict): DynamoDB item
            instance_id (str): EC2 instance ID
            
        Returns:
            dict: Server configuration matching ServerConfig GraphQL type
        """
        return {
            'id': instance_id,
            'shutdownMethod': item.get('shutdownMethod', ''),
            'stopScheduleExpression': item.get('stopScheduleExpression', ''),
            'startScheduleExpression': item.get('startScheduleExpression', ''),
            'alarmThreshold': self._safe_float(item.get('alarmThreshold'), 0.0),
            'alarmEvaluationPeriod': self._safe_int(item.get('alarmEvaluationPeriod'), 0),
            'runCommand': item.get('runCommand', ''),
            'workDir': item.get('workDir', ''),
            'timezone': item.get('timezone', 'UTC'),
            'isBootstrapComplete': bool(item.get('isBootstrapComplete', False)),
            'hasCognitoGroup': bool(item.get('hasCognitoGroup', False)),
            'minecraftVersion': item.get('minecraftVersion', ''),
            'latestPatchUpdate': item.get('latestPatchUpdate', ''),
            'runningMinutesCache': self._safe_float(item.get('runningMinutesCache'), None),
            'runningMinutesCacheTimestamp': item.get('runningMinutesCacheTimestamp', '')
        }

    def get_server_config(self, instance_id):
        """
        Get server configuration from DynamoDB.
        
        Args:
            instance_id (str): The EC2 instance ID
            
        Returns:
            dict: Server configuration matching ServerConfig GraphQL type, or None if not found
        """
        if not instance_id:
            raise ValueError("Instance ID is required")
            
        try:
            logger.info(f"get_server_config: {instance_id}")
            response = self.table.get_item(Key={'id': instance_id})
            
            if 'Item' in response:
                return self._convert_dynamodb_config_item(response['Item'], instance_id)
            else:
                logger.info(f"Server config not found for {instance_id}")
                return None

        except ClientError as e:
            logger.error(f"Error getting server config for {instance_id}: {e.response['Error']['Message']}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting server config for {instance_id}: {str(e)}")
            raise

    def put_server_config(self, config):
        """
        Save complete server configuration to DynamoDB.
        
        Args:
            config (dict): Server configuration matching ServerConfigInput GraphQL type
            
        Returns:
            dict: Saved configuration
        """
        instance_id = config.get('id')
        if not instance_id:
            raise ValueError("Instance ID is required")
            
        try:
            logger.info(f"put_server_config: {instance_id}")

            # Build item with all fields
            item = {
                'id': instance_id,
                'shutdownMethod': config.get('shutdownMethod', ''),
                'stopScheduleExpression': config.get('stopScheduleExpression', ''),
                'startScheduleExpression': config.get('startScheduleExpression', ''),
                'alarmThreshold': self._to_decimal(config.get('alarmThreshold', 0.0)),
                'alarmEvaluationPeriod': config.get('alarmEvaluationPeriod', 0),
                'runCommand': config.get('runCommand', ''),
                'workDir': config.get('workDir', ''),
                'timezone': config.get('timezone', 'UTC'),
                'isBootstrapComplete': config.get('isBootstrapComplete', False),
                'minecraftVersion': config.get('minecraftVersion', ''),
                'latestPatchUpdate': config.get('latestPatchUpdate', ''),
                'updatedAt': datetime.now(timezone.utc).isoformat()
            }
            
            # Preserve createdAt if it exists, otherwise set it
            item['createdAt'] = config.get('createdAt', datetime.now(timezone.utc).isoformat())
            
            # Preserve autoConfigured flag if it exists
            if 'autoConfigured' in config:
                item['autoConfigured'] = config['autoConfigured']
            
            # Preserve cache fields if they exist
            if 'runningMinutesCache' in config and config['runningMinutesCache'] is not None:
                item['runningMinutesCache'] = self._to_decimal(config['runningMinutesCache'])
            if 'runningMinutesCacheTimestamp' in config:
                item['runningMinutesCacheTimestamp'] = config['runningMinutesCacheTimestamp']
            
            # Remove empty strings to keep table clean (but keep timestamps and booleans)
            item = {k: v for k, v in item.items() 
                   if v != '' or k in ['createdAt', 'updatedAt', 'isBootstrapComplete', 'autoConfigured']}
            
            self.table.put_item(Item=item)
            logger.info(f"Server config saved for {instance_id}")
            
            # Return the saved config by fetching it back
            return self.get_server_config(instance_id)

        except ClientError as e:
            logger.error(f"Error saving server config for {instance_id}: {e.response['Error']['Message']}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error saving server config for {instance_id}: {str(e)}")
            raise

    def update_server_config(self, config):
        """
        Update specific fields in server configuration.
        
        Args:
            config (dict): Partial server configuration with id and fields to update
            
        Returns:
            dict: Updated configuration
        """
        instance_id = config.get('id')
        if not instance_id:
            raise ValueError("Instance ID is required")

        # Allowed fields for update operations (whitelist)
        # Potentially create a script to create it from the
        # GraphQL variables
        ALLOWED_UPDATE_FIELDS = {
            'shutdownMethod',
            'stopScheduleExpression',
            'startScheduleExpression',
            'alarmThreshold',
            'alarmEvaluationPeriod',
            'runCommand',
            'workDir',
            'timezone',
            'isBootstrapComplete',
            'hasCognitoGroup',
            'minecraftVersion',
            'latestPatchUpdate',
            'autoConfigured',
            'runningMinutesCache',
            'runningMinutesCacheTimestamp'
        }
        
        # Fields that need Decimal conversion for DynamoDB
        NUMERIC_FIELDS = {'alarmThreshold', 'runningMinutesCache'}

        try:
            logger.info(f"update_server_config: {instance_id}")
            
            # Build update expression dynamically
            update_parts = []
            expression_values = {}
            expression_names = {}
            
            for field_name in self.ALLOWED_UPDATE_FIELDS:
                if field_name in config and config[field_name] is not None:
                    placeholder = f":{field_name}"
                    name_placeholder = f"#{field_name}"
                    update_parts.append(f"{name_placeholder} = {placeholder}")
                    
                    # Convert numeric fields to Decimal
                    value = config[field_name]
                    if field_name in self.NUMERIC_FIELDS:
                        value = self._to_decimal(value)
                    
                    expression_values[placeholder] = value
                    expression_names[name_placeholder] = field_name
            
            if not update_parts:
                logger.warning(f"No fields to update for {instance_id}")
                return self.get_server_config(instance_id)
            
            # Always update timestamp
            update_parts.append("#updatedAt = :updatedAt")
            expression_values[':updatedAt'] = datetime.now(timezone.utc).isoformat()
            expression_names['#updatedAt'] = 'updatedAt'
            
            # Set createdAt if it doesn't exist (for legacy records)
            update_parts.append("#createdAt = if_not_exists(#createdAt, :createdAt)")
            expression_values[':createdAt'] = datetime.now(timezone.utc).isoformat()
            expression_names['#createdAt'] = 'createdAt'
            
            update_expression = "SET " + ", ".join(update_parts)
            
            response = self.table.update_item(
                Key={'id': instance_id},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values,
                ExpressionAttributeNames=expression_names,
                ReturnValues="ALL_NEW"
            )
            
            logger.info(f"Server config updated for {instance_id}")
            
            # Convert the returned item to proper format
            return self._convert_dynamodb_config_item(response['Attributes'], instance_id)

        except ClientError as e:
            logger.error(f"Error updating server config for {instance_id}: {e.response['Error']['Message']}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error updating server config for {instance_id}: {str(e)}")
            raise


    def get_server_info(self, instance_id):
        """
        Get server information from DynamoDB.
        
        Args:
            instance_id (str): EC2 instance ID
            
        Returns:
            dict: Server information or None if not found
        """
        try:
            logger.info(f"Getting server info for {instance_id}")
            
            response = self.table.get_item(
                Key={'id': instance_id}
            )
            
            if 'Item' not in response:
                logger.warning(f"No server info found for {instance_id}")
                return None
            
            item = response['Item']
            
            # Convert DynamoDB item to standard format
            server_info = {
                'id': item.get('id'),
                'name': item.get('name'),
                'userEmail': item.get('userEmail'),
                'state': item.get('state'),
                'vCpus': self._safe_int(item.get('vCpus')),
                'memSize': self._safe_int(item.get('memSize')),
                'diskSize': self._safe_int(item.get('diskSize')),
                'launchTime': item.get('launchTime'),
                'publicIp': item.get('publicIp'),
                'initStatus': item.get('initStatus'),
                'iamStatus': item.get('iamStatus'),
                'runningMinutes': item.get('runningMinutes'),
                'runningMinutesCacheTimestamp': item.get('runningMinutesCacheTimestamp'),
                'configStatus': item.get('configStatus'),
                'configValid': item.get('configValid'),
                'configWarnings': item.get('configWarnings', []),
                'configErrors': item.get('configErrors', []),
                'autoConfigured': item.get('autoConfigured', False)
            }
            
            logger.info(f"Server info retrieved for {instance_id}")
            return server_info
            
        except ClientError as e:
            logger.error(f"Error getting server info for {instance_id}: {e.response['Error']['Message']}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting server info for {instance_id}: {str(e)}")
            raise

    def update_server_name(self, instance_id, new_name):
        """
        Update only the server name in DynamoDB.
        
        Args:
            instance_id (str): EC2 instance ID
            new_name (str): New server name
            
        Returns:
            dict: DynamoDB response
        """
        try:
            if not instance_id:
                raise ValueError("Instance ID is required")
            if not new_name:
                raise ValueError("New name is required")
                
            logger.info(f"Updating server name for {instance_id} to '{new_name}'")
            
            response = self.table.update_item(
                Key={'id': instance_id},
                UpdateExpression="SET #name = :name",
                ExpressionAttributeNames={'#name': 'name'},
                ExpressionAttributeValues={':name': new_name},
                ReturnValues="ALL_NEW"
            )
            
            logger.info(f"Server name updated for {instance_id}")
            return response
            
        except ClientError as e:
            logger.error(f"Error updating server name for {instance_id}: {e.response['Error']['Message']}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error updating server name for {instance_id}: {str(e)}")
            raise

    def put_server_info(self, server_info):
        """
        Save server information to DynamoDB.
        
        Args:
            server_info (dict): Server information to save
            
        Returns:
            dict: DynamoDB response
        """
        try:
            instance_id = server_info.get('id')
            if not instance_id:
                raise ValueError("Server info must include 'id' field")
            
            logger.info(f"Saving server info for {instance_id}")
            
            # Prepare item for DynamoDB, converting numeric values to Decimal
            item = {
                'id': instance_id,
                'name': server_info.get('name'),
                'userEmail': server_info.get('userEmail'),
                'state': server_info.get('state'),
                'vCpus': self._to_decimal(server_info.get('vCpus')),
                'memSize': self._to_decimal(server_info.get('memSize')),
                'diskSize': self._to_decimal(server_info.get('diskSize')),
                'launchTime': server_info.get('launchTime'),
                'publicIp': server_info.get('publicIp'),
                'initStatus': server_info.get('initStatus'),
                'iamStatus': server_info.get('iamStatus'),
                'runningMinutes': server_info.get('runningMinutes'),
                'runningMinutesCacheTimestamp': server_info.get('runningMinutesCacheTimestamp'),
                'configStatus': server_info.get('configStatus'),
                'configValid': server_info.get('configValid'),
                'configWarnings': server_info.get('configWarnings', []),
                'configErrors': server_info.get('configErrors', []),
                'autoConfigured': server_info.get('autoConfigured', False)
            }
            
            # Remove None values to avoid storing them in DynamoDB
            item = {k: v for k, v in item.items() if v is not None}
            
            response = self.table.put_item(Item=item)
            
            logger.info(f"Server info saved for {instance_id}")
            return response
            
        except ClientError as e:
            logger.error(f"Error saving server info for {instance_id}: {e.response['Error']['Message']}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error saving server info for {instance_id}: {str(e)}")
            raise