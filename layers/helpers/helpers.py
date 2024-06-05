import boto3
import logging
import os
import time
import json
import requests
from datetime import datetime, timezone
from jose import jwk, jwt
from jose.utils import base64url_decode
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

class Utils:
    def __init__(self):
        logger.info("------- Utils Class Initialization")
        self.ec2_client = boto3.client('ec2')
        self.ssm = boto3.client('ssm')        
        self.ct_client = boto3.client('cloudtrail')
        self.appValue = os.getenv('TAG_APP_VALUE')
        self.ec2InstanceProfileArn = os.getenv('EC2_INSTANCE_PROFILE_ARN')

    def response(self, status_code, body, headers={}):
        if bool(headers): # Return True if dictionary is not empty # use json.dumps for body when using with API GW
            return {"statusCode": status_code, "body": body, "headers": headers}
        else:
            return {"statusCode": status_code, "body": body }
        
    def get_instance_attributes(self,instance_id):
        try:
        
            # Get existing tags
            existing_tags = self.ec2_client.describe_tags(
                Filters=[
                    {'Name': 'resource-id', 'Values': [instance_id]}
                ]
            )['Tags']

            tag_mapping = {}
            
            for tag in existing_tags:
                tag_mapping[tag['Key'].lower()] = tag['Value']

            return tag_mapping
        except Exception as e:
            logger.error(f"Error getting tags: {e}")
        

    def set_instance_attributes(self,instance_id):

        tag_mapping = self.get_instance_attr(instance_id)
        
        tags = [{'Key': key, 'Value': value} for key, value in tag_mapping.items()]

        try:
            # Delete existing tags based on tag_mapping
            self.ec2_client.delete_tags(
                Resources=[instance_id],
                Tags=[{'Key': key} for key in tag_mapping.keys()]
            )

            # Create new tags
            self.ec2_client.create_tags(
                Resources=[instance_id],
                Tags=tags
            )
            logger.info(f"Tags set successfully for instance {instance_id}")
        except Exception as e:
            logger.error(f"Error setting tags: {e}")


    # def set_instance_attr(self,instance_id):
        
    #     existing_tags = self.get_instance_attr(instance_id)
    #     if existing_tags:
    #         logger.info("Updating Instance " + instance_id)

    #         # Remove existing tags that are being updated
    #         tags = ['minecraftruncommand', 'alarm_name', 'alarm_threshold']
    #         tags_to_remove = [tag for tag in existing_tags if tag['Key'] in tags]
    #         if tags_to_remove:
    #             self.ec2_client.delete_tags(
    #                 Resources=[instance_id],
    #                 Tags=tags_to_remove
    #             )

    #         # Add or update tags
    #         if new_tags:
    #             self.ec2_client.create_tags(
    #                 Resources=[instance_id],
    #                 Tags=new_tags
    #             )

    #     return {'code': 200, 'msg': 'Tags updated successfully'}

        
    def get_total_hours_running_per_month(self, instanceId):
        total_minutes = 0
        event_data = []

        paginator = self.ct_client.get_paginator('lookup_events')
        start_time = datetime(datetime.now().year, datetime.now().month, 1, tzinfo=timezone.utc)
        end_time = datetime.now(tz=timezone.utc)

        for page in paginator.paginate(
            LookupAttributes=[{'AttributeKey': 'ResourceName', 'AttributeValue': instanceId}],
            StartTime=start_time,
            EndTime=end_time
        ):
            for event in page['Events']:
                event_name = event['EventName']
                if event_name == "RunInstances":
                    event_data.append({'s': 'StartInstances', 'x': json.loads(event['CloudTrailEvent'])['eventTime']})
                elif event_name == "StartInstances":
                    start_event = self.extract_state_event_time(event, "stopped", instanceId)
                    if start_event:
                        event_data.append({'s': 'StartInstances', 'x': start_event})
                elif event_name == "StopInstances":
                    stop_event = self.extract_state_event_time(event, "running", instanceId)
                    if stop_event:
                        event_data.append({'s': 'StopInstances', 'x': stop_event})

        data_points = sorted(event_data, key=lambda k: k['x'])

        start_event = None
        stop_event = None
        for point in data_points:
            if point['s'] == "StartInstances":
                start_event = datetime.fromisoformat(point['x'].replace("Z", "+00:00"))
            elif point['s'] == "StopInstances":
                if start_event:
                    stop_event = datetime.fromisoformat(point['x'].replace("Z", "+00:00"))
                else:
                    start_event = start_time
                    stop_event = datetime.fromisoformat(point['x'].replace("Z", "+00:00"))

                if start_event and stop_event:
                    delta = stop_event - start_event
                    total_minutes += round(delta.total_seconds() / 60, 2)
                    start_event = None
                    stop_event = None

        return total_minutes

    def extract_state_event_time(self, evt, previousState, instanceId):
        ct_event = evt.get('CloudTrailEvent')
        if ct_event:
            ct_event = json.loads(ct_event)
            response_elements = ct_event.get('responseElements')
            if response_elements:
                instances_set = response_elements.get('instancesSet')
                if instances_set:
                    items = instances_set.get('items')
                    if items:
                        for item in items:
                            if item.get('instanceId') == instanceId and item['previousState']['name'] == previousState:
                                return ct_event['eventTime']
        return None
        
    def get_ssm_param(self, paramKey, isEncrypted=False):
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

    def get_ssm_parameters(self, paramKeys, isEncrypted=False):
        try:
            resp=[]
            paramArray=paramKeys.split(",")            
            ssmResult = self.ssm.get_parameters(
                Names=paramArray,
                WithDecryption=isEncrypted
            )           
            if ssmResult["Parameters"]:
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
        

    def list_server_by_id(self,instanceId):
        response = self.ec2_client.describe_instances(InstanceIds=[instanceId])

        if not response["Reservations"]:
            return []
        else:
            return {
            "Reservations": response["Reservations"][0],
            "TotalInstances": 1
        }


    def list_servers_by_user(self, email, page=1, results_per_page=10):
        filters = [
            {"Name": "tag:App", "Values": [self.appValue]},
            {"Name":"instance-state-name", "Values":["pending","running","stopping","stopped"]},
            {"Name": "tag:User", "Values": [email]}
        ]

        return self.paginate_instances(filters, page, results_per_page)


    def list_servers_by_state(self, state, page=1, results_per_page=10):
        filters = [
            {"Name": "tag:App", "Values": [self.appValue]},
            {"Name": "instance-state-name", "Values": [state]}
        ]

        return self.paginate_instances(filters, page, results_per_page)

    def list_all_servers(self, page=1, results_per_page=10):
        filters = [
            {"Name": "tag:App", "Values": [self.appValue]},
            {"Name": "instance-state-name", "Values": ["pending", "running", "stopping", "stopped"]}
        ]

        return self.paginate_instances(filters, page, results_per_page)


    def paginate_instances(self, filters, page=1, results_per_page=10):
        instances = []
        next_token = None

        while True:
            if next_token:
                response = self.ec2_client.describe_instances(Filters=filters, NextToken=next_token)
            else:
                response = self.ec2_client.describe_instances(Filters=filters)

            reservations = response["Reservations"]
            instances.extend([instance for reservation in reservations for instance in reservation["Instances"]])
            next_token = response.get("NextToken")
            if not next_token:
                break

        if not instances:
            return []

        # Get the total number of instances
        total_instances = len(instances)

        start_index = (page - 1) * results_per_page
        end_index = start_index + results_per_page

        # Paginate the instances
        paginated_instances = instances[start_index:end_index]

        # Create a new list of reservations with the paginated instances
        paginated_reservations = {"Instances": paginated_instances}

        # Log the total number of instances
        logger.info(f"Total instances: {total_instances}")

        return {
            "Reservations": paginated_reservations,
            "TotalInstances": total_instances
        }

    def describe_iam_profile(self, instance_id, status, association_id=None):

        if association_id:
            response = self.ec2_client.describe_iam_instance_profile_associations(
                AssociationIds=[association_id]
                )
        else:                            
            response = self.ec2_client.describe_iam_instance_profile_associations(
                Filters=[
                    {
                        'Name': 'instance-id',
                        'Values': [instance_id]
                    },
                ]
            )            

        matching_association = next((
            {
                "AssociationId": rec['AssociationId'],
                "Arn": rec['IamInstanceProfile']['Arn']
            }
            for rec in response['IamInstanceProfileAssociations']
            if rec['InstanceId'] == instance_id and rec['State'].lower() == status.lower()
        ), None)

        return matching_association

                    
    def describe_instance_status(self, instance_id):
        iamStatus = 'Fail'
        initStatus = 'Fail'

        statusRsp = self.ec2_client.describe_instance_status(InstanceIds=[instance_id])

        if not statusRsp["InstanceStatuses"]:
            instanceStatus =  "Fail" 
            systemStatus = "Fail" 
        else:
            instanceStatus = statusRsp["InstanceStatuses"][0]["InstanceStatus"]["Status"]
            systemStatus = statusRsp["InstanceStatuses"][0]["SystemStatus"]["Status"]

        if instanceStatus == 'ok' and systemStatus == 'ok':
            initStatus = 'ok'
        
        iamProfile = self.describe_iam_profile(instance_id,"associated")
        if iamProfile is not None and iamProfile['Arn'] == self.ec2InstanceProfileArn:
            iamStatus = 'ok'
        
        return { 'instanceId': instance_id, 'initStatus': initStatus, 'iamStatus': iamStatus }

class Auth:
    def __init__(self,cognito_pool_id):
        logger.info("------- Auth Class Initialization")
        self.cognito_pool_id = cognito_pool_id
        self.jwk_url = 'https://cognito-idp.{}.amazonaws.com/{}/.well-known/jwks.json'.format(aws_region, cognito_pool_id)
        self.cognito_idp = boto3.client('cognito-idp')

    def is_token_valid(self,token,keys):
        # https://github.com/awslabs/aws-support-tools/tree/master/Cognito/decode-verify-jwt
        headers = jwt.get_unverified_headers(token)
        kid = headers['kid']
        # search for the kid in the downloaded public keys
        key_index = -1
        for i in range(len(keys)):
            if kid == keys[i]['kid']:
                key_index = i
                break
        if key_index == -1:
            logger.error('Public key not found in jwks.json')
            return None
        # construct the public key
        public_key = jwk.construct(keys[key_index])
        # get the last two sections of the token,
        # message and signature (encoded in base64)
        message, encoded_signature = str(token).rsplit('.', 1)
        # decode the signature
        decoded_signature = base64url_decode(encoded_signature.encode('utf-8'))
        # verify the signature
        if not public_key.verify(message.encode("utf8"), decoded_signature):
            logger.error('Signature verification failed')
            return None
        logger.info('Signature successfully verified')
        # since we passed the verification, we can now safely
        # use the unverified claims
        claims = jwt.get_unverified_claims(token)
        
        # additionally we can verify the token expiration
        if time.time() > claims['exp']:
            logger.error('Token is expired')
            return None
        # now we can use the claims
        return claims

    def process_token(self,token):
        # download the key
        try:
            with requests.get(self.jwk_url) as keys_response:
                keys_response.raise_for_status()
                keys = keys_response.json()["keys"]
        except (requests.RequestException, ValueError, KeyError) as e:
            logger.error(f"Error fetching JWT keys: {e}")
            return None

        token_claims = self.is_token_valid(token,keys)

        if token_claims is None:
            logger.error("Invalid Token")
            return None
        
        user_attributes = {}

        user_name = token_claims.get("cognito:username") or token_claims.get("username")

        # Get User attributes from Cognito
        cog_user = self.cognito_idp.admin_get_user(
            UserPoolId=self.cognito_pool_id,
            Username=user_name
        )

        user_attributes["username"] = user_name

        for att in cog_user["UserAttributes"]:
            if att["Name"].lower() in ["email", "given_name", "family_name", "sub", "name", "username", "cognito:username"]:
                user_attributes[att["Name"].lower()] = att["Value"]

        return user_attributes
    
    def group_exists(self, instanceId):
        try:
            grpRsp = self.cognito_idp.get_group(
                    GroupName=instanceId,
                    UserPoolId=self.cognito_pool_id
                )
                
            return True
        
        except self.cognito_idp.exceptions.ResourceNotFoundException:
            logger.warning("Group does not exist.")
            return False
            
    def create_group(self, instanceId):    
        try:
            grpRsp = self.cognito_idp.create_group(
                GroupName=instanceId,
                UserPoolId=self.cognito_pool_id,
                Description='Minecraft Dashboard'
            )

            return True

        except Exception as e:
                logger.info("Exception create_group")
                logger.error(str(e))
                return False
            
    def add_user_to_group(self,instance_id,userEmail):
            try:
                user = self.cognito_idp.list_users(
                    UserPoolId=self.cognito_pool_id,
                    Filter="email = '" + userEmail + "'"
                )

                if len(user['Users']) == 0:
                    logger.error("Unable to find user: " + userEmail + ". User has to create a profile by login in this website")
                    return {"err": "Unable to find user: " + userEmail + ". User has to create a profile by login in this website" }

                userRsp = self.cognito_idp.admin_add_user_to_group(
                    UserPoolId=self.cognito_pool_id,
                    Username=user['Users'][0]["Username"],
                    GroupName=instance_id
                )

                return {"msg": "User added to the group"}
        
            except Exception as e:
                logger.info("Exception admin_add_user_to_group")
                logger.warning(str(e))
                return { "err": str(e) } 
            
    def list_users_in_group(self,instance_id):
        try:
            response = self.cognito_idp.list_users_in_group(
                UserPoolId=self.cognito_pool_id,
                GroupName=instance_id
            )

            groupMembers = [
                    {
                        "id": user_attrs.get("sub"),
                        "email": user_attrs.get("email"),
                        "fullname": f"{user_attrs.get('given_name')} {user_attrs.get('family_name')}"
                    }
                    for user in response["Users"]
                    if (user_attrs := {attr["Name"]: attr["Value"] for attr in user["Attributes"]})
                ]
        
            return groupMembers

        except Exception as e:
            logger.info("Exception list_users_in_group")
            logger.warning(str(e))
            return []

     
