import boto3
import logging
import os
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key, Attr

logger = logging.getLogger()
logger.setLevel(logging.INFO)

session = boto3.session.Session()
awsRegion = session.region_name

class Dyn:
    def __init__(self):
        logger.info("------- Dyn Class Initialization")
        dynamodb = boto3.resource('dynamodb', region_name=awsRegion)
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
                # Process the item to ensure proper type conversion
                processed_item = self._process_item_types(response['Items'][0])
                return {'code': 200, 'msg': processed_item } 
            else:
                logger.warning("GetInstanceAttr: Instance not found in the App Database")
                return {'code': 400, 'msg': "Instance not found in the App Database" } 

        except ClientError as e:
            logger.error(e.response['Error']['Message'])
            return {'code': 500, 'msg': e.response['Error']['Message'] }
            
    def _process_item_types(self, item):
        """
        Process an item from DynamoDB to ensure proper type conversion for numeric fields.
        
        Args:
            item (dict): The DynamoDB item to process
            
        Returns:
            dict: The processed item with proper type conversion
        """
        processed_item = item.copy()
        
        # Convert alarmThreshold to Float with default value
        if 'alarmThreshold' in processed_item:
            try:
                processed_item['alarmThreshold'] = float(processed_item['alarmThreshold'])
            except (ValueError, TypeError):
                logger.warning(f"Invalid alarmThreshold value: {processed_item['alarmThreshold']}. Using default: 10")
                processed_item['alarmThreshold'] = 10.0
        else:
            # Add default value if missing
            processed_item['alarmThreshold'] = 10.0
            
        # Convert alarmEvaluationPeriod to Int with default value
        if 'alarmEvaluationPeriod' in processed_item:
            try:
                processed_item['alarmEvaluationPeriod'] = int(processed_item['alarmEvaluationPeriod'])
            except (ValueError, TypeError):
                logger.warning(f"Invalid alarmEvaluationPeriod value: {processed_item['alarmEvaluationPeriod']}. Using default: 35")
                processed_item['alarmEvaluationPeriod'] = 35
        else:
            # Add default value if missing
            processed_item['alarmEvaluationPeriod'] = 35
            
        return processed_item

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
                # Ensure alarmThreshold is stored as a float
                try:
                    valuesMap[':at'] = float(params["at"])
                except (ValueError, TypeError):
                    logger.warning(f"Invalid alarmThreshold value: {params['at']}. Using default: 10")
                    valuesMap[':at'] = 10.0
            if 'aep' in params:
                dynExpression = dynExpression + "alarmEvaluationPeriod = :aep,"
                # Ensure alarmEvaluationPeriod is stored as an integer
                try:
                    valuesMap[':aep'] = int(params["aep"])
                except (ValueError, TypeError):
                    logger.warning(f"Invalid alarmEvaluationPeriod value: {params['aep']}. Using default: 35")
                    valuesMap[':aep'] = 35
        
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
                        'region': awsRegion 
                    },
                    UpdateExpression=dynExpression[:-1],
                    ExpressionAttributeValues=valuesMap,
                    ReturnValues="UPDATED_NEW"
                )

            return {'code': 200, 'msg': "Item Saved" }

                        
        except ClientError as e:
            logger.error(e.response['Error']['Message'])
            return {'code': 500, 'msg': e.response['Error']['Message'] }

class Utils:
    def __init__(self):
        logger.info("------- Utils Class Initialization")
        self.ec2_client = boto3.client('ec2')
        self.ssm = boto3.client('ssm')        
        self.appValue = os.getenv('TAG_APP_VALUE')
        self.ec2InstanceProfileArn = os.getenv('EC2_INSTANCE_PROFILE_ARN')

    def response(self, status_code, body, headers={}):
        if bool(headers): # Return True if dictionary is not empty # use json.dumps for body when using with API GW
            return {"statusCode": status_code, "body": body, "headers": headers}
        else:
            return {"statusCode": status_code, "body": body }
        
    def getSsmParam(self, paramKey, isEncrypted=False):
        try:
            ssmResult = self.ssm.get_parameter(
                Name=paramKey,
                WithDecryption=isEncrypted
            )

            if (ssmResult["ResponseMetadata"]["HTTPStatusCode"] == 200):
                return ssmResult["Parameter"]["Value"]
            else:
                return None

        except Exception as e:
            logger.warning(str(e) + " for " + paramKey)
            return None

    def getSsmParameters(self, paramKeys, isEncrypted=False):
        try:
            resp=[]
            paramArray=paramKeys.split(",")            
            ssmResult = self.ssm.get_parameters(
                Names=paramArray,
                WithDecryption=isEncrypted
            )           
            if (len(ssmResult["Parameters"]) > 0):      
                for entry in ssmResult["Parameters"]:
                    resp.append({
                        "Name":entry["Name"],
                        "Value":entry["Value"]
                    })

                return resp
            else:
                return None

        except Exception as e:
            logger.warning(str(e) + " for " + paramKeys)
            return None

    def putSsmParam(self, paramKey, paramValue, paramType):
        try:
            ssmResult = self.ssm.put_parameter(
                Name=paramKey,
                Value=paramValue,
                Type=paramType,
                Overwrite=True
            )

            return ssmResult

        except Exception as e:
            logger.warning(str(e) + " for " + paramKey)
            return None

    def describeInstances(self,name,value):
        if name == 'id':
            response = self.ec2_client.describe_instances(
                    InstanceIds=[value]
                        )
        elif name == 'email':
            filters = [
                {"Name":"tag:App", "Values":[ self.appValue ]},
                {"Name":"instance-state-name", "Values":["pending","running","stopping","stopped"]}
                
                # {"Name":"tag:User", "Values":[ value ]}
            ]
            response =  self.ec2_client.describe_instances(
                Filters=filters            
            )
        elif name == 'state':
            filters = [
                {"Name":"tag:App", "Values":[ self.appValue ]},
                {"Name":"instance-state-name", "Values":[ value ]}
            ]
            response =  self.ec2_client.describe_instances(
                Filters=filters            
            )

        # checking response
        logger.info("for " + name + ": " + value + " found " + str(len(response["Reservations"])) + " instances")
        if (len(response["Reservations"])) == 0:
            return []
        else:
            return response["Reservations"]

    def describeIamProfile(self, instance, status):
        descResp = self.ec2_client.describe_iam_instance_profile_associations(
            Filters=[
                {
                    'Name': 'instance-id',
                    'Values': [
                        instance
                    ]
                },
            ])

        if len(descResp['IamInstanceProfileAssociations']) > 0:        
            for rec in descResp['IamInstanceProfileAssociations']:
                if rec['State'] == status:
                    return { "AssociationId": rec['AssociationId'], "Arn": rec['IamInstanceProfile']['Arn'] }

        return None
                
    def describeInstanceStatus(self, instanceId):
        iamStatus = 'Fail'
        initStatus = 'Fail'

        statusRsp = self.ec2_client.describe_instance_status(InstanceIds=[instanceId])

        if (len(statusRsp["InstanceStatuses"])) == 0:
            instanceStatus =  "Fail" 
            systemStatus = "Fail" 
        else:
            instanceStatus = statusRsp["InstanceStatuses"][0]["InstanceStatus"]["Status"]
            systemStatus = statusRsp["InstanceStatuses"][0]["SystemStatus"]["Status"]

        if instanceStatus == 'ok' and systemStatus == 'ok':
            initStatus = 'ok'
        
        iamProfile = self.describeIamProfile(instanceId,"associated")
        if iamProfile != None and iamProfile['Arn'] == self.ec2InstanceProfileArn:
            iamStatus = 'ok'
        
        return { 'initStatus': initStatus, 'iamStatus': iamStatus }
