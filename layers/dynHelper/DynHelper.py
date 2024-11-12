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
        instancesTable = os.getenv('INSTANCES_TABLE_NAME')
        self.table = dynamodb.Table(instancesTable)

    def GetInstanceAttr(self,instanceId):
        try:
            logger.info("GetInstanceAttr: " + instanceId)
            response = self.table.query(
                KeyConditionExpression=Key('instanceId').eq(instanceId) 
                    # For future implementation
                    # Key('region').eq(region_name)
            )
            if 'Items' in response and len(response['Items']) > 0:
                return {'code': 200, 'msg': response['Items'][0] } 
            else:
                logger.warning("GetInstanceAttr: Instance not found in the App Database")
                return {'code': 400, 'msg': "Instance not found in the App Database" } 

        except ClientError as e:
            logger.error(e.response['Error']['Message'])
            return {'code': 500, 'msg': e.response['Error']['Message'] }

    def SetInstanceAttr(self,instanceId,params):
        try:
            logger.info("SetInstanceAttr: " + instanceId)

            dynExpression = "set "               
            valuesMap = {}

            if 'rc' in params:
                dynExpression = dynExpression + "runCommand = :rc,"     
                valuesMap[':rc'] = params["rc"]
            if 'wd' in params:
                dynExpression = dynExpression + "workingDir = :wd,"     
                valuesMap[':wd'] = params["wd"]
            if 'am' in params:
                dynExpression = dynExpression + "alarmMetric = :am,"     
                valuesMap[':am'] = params["am"]
            if 'at' in params:
                dynExpression = dynExpression + "alarmThreshold = :at,"     
                valuesMap[':at'] = params["at"]
        
            entry = self.GetInstanceAttr(instanceId)

            if entry['code'] == 200:
                logger.info("Updating Instance " + instanceId)
            elif entry['code'] == 400:
                logger.info("Creating Instance " + instanceId)
            else:
                logger.error("GetInstance failed")
                return {'code': 500, 'msg': "GetInstance failed" }

            resp = self.table.update_item(
                    Key={ 
                        'instanceId': instanceId, 
                        'region': aws_region 
                    },
                    UpdateExpression=dynExpression[:-1],
                    ExpressionAttributeValues=valuesMap,
                    ReturnValues="UPDATED_NEW"
                )

            return {'code': 200, 'msg': "Item Saved" }

                        
        except ClientError as e:
            logger.error(e.response['Error']['Message'])
            return {'code': 500, 'msg': e.response['Error']['Message'] }
