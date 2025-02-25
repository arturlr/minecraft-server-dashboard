import boto3
import logging
import os
import json
from datetime import datetime, timezone
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key, Attr

logger = logging.getLogger()
logger.setLevel(logging.INFO)

session = boto3.session.Session()
aws_region = session.region_name
               
class Ec2Utils:
    def __init__(self):
        logger.info("------- Ec2Utils Class Initialization")
        self.ec2_client = boto3.client('ec2')
        self.ssm = boto3.client('ssm')        
        self.ct_client = boto3.client('cloudtrail')        
        self.appValue = os.getenv('TAG_APP_VALUE')
        self.ec2InstanceProfileArn = os.getenv('EC2_INSTANCE_PROFILE_ARN')

    def get_instance_attributes_from_tags(self,instance_id):
        """
        Retrieves the instance attributes from the EC2 tags.

        Args:
            instance_id (str): The ID of the EC2 instance.

        Returns:
            dict: A dictionary containing the instance attributes.
        """
        try:        
            logger.info("------- get_instance_attributes_from_tags " + instance_id)
            paginator = self.ec2_client.get_paginator('describe_tags')
            existing_tags = []
            for page in paginator.paginate(
                Filters=[
                    {'Name': 'resource-id', 'Values': [instance_id]}
                ]
            ):
                existing_tags.extend(page['Tags'])
            
            tag_mapping = {}
            for tag in existing_tags:
                tag_mapping[tag['Key'].lower()] = tag['Value']

            # logger.info(f"Tag Mapping: {tag_mapping}")

            # returning following the Appsync Schema for ServerConfig
            return {
                'id': instance_id,
                'alarmType': tag_mapping.get('alarmtype', ''),
                'alarmThreshold': tag_mapping.get('alarmthreshold', ''),
                'alarmEvaluationPeriod': tag_mapping.get('alarmevaluationperiod', ''),
                'runCommand': tag_mapping.get('runcommand', ''),
                'workDir': tag_mapping.get('workdir', ''),
                'groupMembers': ''
            }
        
        except Exception as e:
            logger.error(f"Error getting tags: {e}")
            return None  # or handle this error as appropriate
        
    def set_instance_attributes_to_tags(self,input):
        logger.info("------- set_instance_attributes_to_tags")

        instance_id = input.get('id', None)
        if not instance_id:
            raise ValueError("Instance ID is required")

        logger.info("Setting instance attributes for " + instance_id)

        alarm_type = input.get('alarmType', '')
        alarm_threshold = input.get('alarmThreshold', '20')
        alarmEvaluationPeriod = input.get('alarmEvaluationPeriod', '35')
        run_command = input.get('runCommand', '')
        work_dir = input.get('workDir', '')

        # Getting current EC2 Tags
        ec2_attrs = self.get_instance_attributes(instance_id)

        ec2_tag_mapping = {
            self.capitalize_first_letter('alarmType'): alarm_type,
            self.capitalize_first_letter('alarmThreshold'): alarm_threshold,
            self.capitalize_first_letter('alarmEvaluationPeriod'): alarmEvaluationPeriod,
            self.capitalize_first_letter('runCommand'): run_command,
            self.capitalize_first_letter('workDir'): work_dir
        }

        appsync_server_config_attrs = {
            'id': instance_id,
            'alarmType': alarm_type,
            'alarmThreshold': alarm_threshold,
            'alarmEvaluationPeriod': alarmEvaluationPeriod,
            'runCommand': run_command,
            'workDir': work_dir
        }

        logger.info(f"input : {input}")
        logger.info(f"ec2_tag_mapping : {ec2_tag_mapping}")
        
        try:
            # Delete existing tags based on tag_mapping
            self.ec2_client.delete_tags(
                Resources=[instance_id],
                Tags=[{'Key': key} for key in ec2_attrs.keys()]
            )

            # Create new tags
            self.ec2_client.create_tags(
                Resources=[instance_id],
                Tags=[{'Key': key, 'Value': str(value) } for key, value in ec2_tag_mapping.items()]
            )
            logger.info(f"Tags set successfully for instance {instance_id}")

            return appsync_server_config_attrs

        except Exception as e:
            logger.error(f"Error setting tags: {e}")
        
    def get_total_hours_running_per_month(self, instanceId):
        logger.info(f"------- get_total_hours_running_per_month {instanceId}")

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
        logger.info(f"------- extract_state_event_time {instanceId}")

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
    
    def list_instances_by_user_group(self, user_groups):
        user_instances = []
        for group_name in user_groups:
            # check if group_name starts with i- (instanceId)
            if not group_name.startswith("i-"):
                continue

            logger.info(f"Processing group: {group_name}")
            response = self.ec2_client.describe_instances(InstanceIds=[group_name])
            logger.info(response)
            if not response["Reservations"]:
                continue
            else:
                reservations = response["Reservations"]
                user_instances.extend([user_instances for reservation in reservations for user_instances in reservation["Instances"]])

        # Get the total number of instances
        total_instances = len(user_instances)

        # Log the total number of instances
        logger.info(f"Total instances: {total_instances}")

        return {
            "Instances": user_instances,
            "TotalInstances": total_instances
        }

    def list_server_by_id(self, instanceId):
        response = self.ec2_client.describe_instances(InstanceIds=[instanceId])

        if not response["Reservations"]:
            return []
        else:
            return {
            "Instances": response["Reservations"][0]["Instances"],
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

    def list_servers_by_group(self, group, page=1, results_per_page=10):
        filters = [
            {"Name": "tag:App", "Values": [self.appValue]},
            {"Name": "instance-state-name", "Values": ["pending", "running", "stopping", "stopped"]},
            {"Name": "tag:Group", "Values": [group]}
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
        logger.info(f"paginate_instances filter: {filters}")

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
            logger.info("No instances found")
            return {
                "Instances": [],
                "TotalInstances": 0
            }

        # Get the total number of instances
        total_instances = len(instances)

        start_index = (page - 1) * results_per_page
        end_index = start_index + results_per_page

        # Log the total number of instances
        logger.info(f"Total instances: {total_instances}")

        return {
            "Instances": instances[start_index:end_index],
            "TotalInstances": total_instances
        }

    def describe_iam_profile(self, instance_id, status, association_id=None):
        logger.info(f"------- describe_iam_profile: {instance_id} - {status}")

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
        logger.info(f"------- describe_instance_status: {instance_id}") 
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

    def describe_instance_attributes(self, instanceId):
        logger.info(f"------- describe_instance_attributes: {instanceId}")
        response = self.ec2_client.describe_instance_attribute(
            Attribute='userData',
            InstanceId=instanceId
        )

   