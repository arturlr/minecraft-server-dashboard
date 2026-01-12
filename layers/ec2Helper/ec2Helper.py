import utilHelper
import sys
import boto3
import logging
import os
import json
from datetime import datetime, timezone
from botocore.exceptions import ClientError

sys.path.insert(0, "/opt/utilHelper")

utl = utilHelper.Utils()

logger = logging.getLogger()
logger.setLevel(logging.INFO)

session = boto3.session.Session()
aws_region = session.region_name


def extract_instance_id(event):
    """Extract instance ID from Lambda event arguments."""
    return (
        event["arguments"].get("instanceId")
        or event["arguments"].get("id")
        or event["arguments"].get("input", {}).get("id")
    )


class Ec2Utils:
    def __init__(self):
        logger.info("------- Ec2Utils Class Initialization")
        self.ec2_client = boto3.client("ec2")
        self.ssm = boto3.client("ssm")
        self.ct_client = boto3.client("cloudtrail")
        self.cw_client = boto3.client("cloudwatch")
        self.sts_client = boto3.client("sts")
        self.account_id = self.sts_client.get_caller_identity()["Account"]
        self.appValue = os.getenv("TAG_APP_VALUE")
        self.ec2InstanceProfileArn = os.getenv("EC2_INSTANCE_PROFILE_ARN")

    def get_latest_ubuntu_ami(self):
        """
        Get the latest Ubuntu 22.04 AMI ID from SSM Parameter Store
        """
        # Parameter path for Ubuntu 22.04 (Jammy) Server HVM with EBS storage
        parameter_name = "/aws/service/canonical/ubuntu/server/22.04/stable/current/amd64/hvm/ebs-gp2/ami-id"

        try:
            response = self.ssm.get_parameter(Name=parameter_name)
            ami_id = response["Parameter"]["Value"]
            print(f"Latest Ubuntu 22.04 AMI ID: {ami_id}")
            return ami_id
        except Exception as e:
            print(f"Error retrieving AMI from Parameter Store: {e}")
            return None

    def create_ec2_instance(self, instance_name, instance_type="t3.micro", subnet_id=None, security_group_id=None):
        """
        Create a new EC2 instance with specified configuration

        Args:
            instance_name (str): Name tag for the instance
            instance_type (str): EC2 instance type (default: t3.micro)
            subnet_id (str): Subnet ID (None for default)
            security_group_id (list): Security group IDs (None for default)

        Returns:
            str: Instance ID if successful, None if failed
        """
        logger.info(f"------- create_ec2_instance: {instance_name} ({instance_type})")

        # Validate instance type
        supported_instance_types = ["t3.micro", "t3.small", "t3.medium", "t3.large", "t3.xlarge", "t3.2xlarge"]

        if instance_type not in supported_instance_types:
            logger.error(f"Unsupported instance type: {instance_type}. Supported types: {supported_instance_types}")
            return None

        try:
            # Get the latest Ubuntu 22.04 AMI
            ami_id = self.get_latest_ubuntu_ami()
            if not ami_id:
                logger.error("Failed to retrieve Ubuntu 22.04 AMI ID")
                return None

            logger.info(f"Using Ubuntu 22.04 AMI: {ami_id}")
            logger.info(f"Creating instance with type: {instance_type}")

            # Define block device mappings for two EBS volumes
            block_device_mappings = [
                {
                    # Root volume (OS) - 16GB for OS
                    "DeviceName": "/dev/sda1",
                    "Ebs": {
                        "VolumeSize": 16,  # 16 GB for OS
                        "VolumeType": "gp3",
                        "DeleteOnTermination": True,
                        "Encrypted": False,
                    },
                },
                {
                    # Second volume for game data and logs - 50GB for game
                    "DeviceName": "/dev/sdf",
                    "Ebs": {
                        "VolumeSize": 50,  # 50 GB for game and logs
                        "VolumeType": "gp3",
                        "DeleteOnTermination": True,
                        "Encrypted": False,
                    },
                },
            ]

            logger.info("Configured two EBS volumes: 16GB root (/dev/sda1), 50GB data (/dev/sdf)")

            # Prepare run_instances parameters
            run_params = {
                "ImageId": ami_id,
                "InstanceType": instance_type,
                "MinCount": 1,
                "MaxCount": 1,
                "IamInstanceProfile": {"Arn": self.ec2InstanceProfileArn},
                "BlockDeviceMappings": block_device_mappings,
                "TagSpecifications": [
                    {
                        "ResourceType": "instance",
                        "Tags": [{"Key": "Name", "Value": instance_name}, {"Key": "App", "Value": self.appValue}],
                    },
                    {
                        "ResourceType": "volume",
                        "Tags": [
                            {"Key": "Name", "Value": f"{instance_name}-volume"},
                            {"Key": "App", "Value": self.appValue},
                        ],
                    },
                ],
            }

            # Add optional parameters if provided
            if subnet_id:
                run_params["SubnetId"] = subnet_id
                logger.info(f"Using subnet: {subnet_id}")
            else:
                logger.info("Using default subnet")

            if security_group_id:
                run_params["SecurityGroupIds"] = security_group_id
                logger.info(f"Using security groups: {security_group_id}")
            else:
                logger.info("Using default security group")

            response = self.ec2_client.run_instances(**run_params)

            instance_id = response["Instances"][0]["InstanceId"]
            logger.info(f"✓ EC2 instance created successfully: {instance_id}")
            logger.info(f"✓ Instance type: {instance_type}")

            return instance_id

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_message = e.response.get("Error", {}).get("Message", str(e))
            logger.error(f"✗ AWS ClientError creating instance: {error_code} - {error_message}")

            # Log specific common errors with helpful context
            if error_code == "InvalidParameterValue":
                logger.error("Check if the instance type is available in the current region")
            elif error_code == "InsufficientInstanceCapacity":
                logger.error("AWS does not have sufficient capacity for the requested instance type")
            elif error_code == "UnauthorizedOperation":
                logger.error("Check IAM permissions for ec2:RunInstances and iam:PassRole")

            return None
        except Exception as e:
            logger.error(f"✗ Unexpected error creating instance: {str(e)}", exc_info=True)
            return None

    def update_alarm(self, instance_id, alarm_metric, alarm_threshold, alarm_evaluation_period):
        logger.info("------- update_alarm : " + instance_id)

        dimensions = []
        statistic = "Average"
        namespace = "CWAgent"
        dimensions.append({"Name": "InstanceId", "Value": instance_id})
        if alarm_metric == "CPUUtilization":
            alarmMetricName = "cpu_usage_active"
            dimensions.append({"Name": "cpu", "Value": "cpu-total"})
        elif alarm_metric == "Connections":
            alarmMetricName = "UserCount"
            statistic = "Maximum"
            namespace = "MinecraftDashboard"

        self.cw_client.put_metric_alarm(
            AlarmName=instance_id + "-" + "minecraft-server",
            ActionsEnabled=True,
            AlarmActions=["arn:aws:automate:" + aws_region + ":ec2:stop"],
            InsufficientDataActions=[],
            MetricName=alarmMetricName,
            Namespace=namespace,
            Statistic=statistic,
            Dimensions=dimensions,
            Period=60,
            EvaluationPeriods=int(alarm_evaluation_period),
            DatapointsToAlarm=int(alarm_evaluation_period),
            Threshold=float(alarm_threshold),  # Use float to support decimal thresholds
            TreatMissingData="missing",
            ComparisonOperator="LessThanOrEqualToThreshold",
        )

        logger.info(
            f"Alarm configured to {alarm_metric} with threshold {alarm_threshold} and evaluation period {alarm_evaluation_period}"
        )

    def remove_alarm(self, instance_id):
        logger.info("------- remove_alarm : " + instance_id)

        alarm_name = instance_id + "-" + "minecraft-server"

        # Check if alarm exists before deleting
        try:
            alarms = self.cw_client.describe_alarms(AlarmNames=[alarm_name])
            if alarms["MetricAlarms"]:
                self.cw_client.delete_alarms(AlarmNames=[alarm_name])
                logger.info(f"Alarm {alarm_name} deleted successfully")
            else:
                logger.info(f"Alarm {alarm_name} does not exist")
        except ClientError as e:
            logger.error(f"Error checking/deleting alarm: {e}")

    def check_alarm_exists(self, instance_id):
        """Check if CloudWatch alarm exists for the instance."""
        alarm_name = f"{instance_id}-minecraft-server"
        try:
            alarms = self.cw_client.describe_alarms(AlarmNames=[alarm_name])
            return len(alarms["MetricAlarms"]) > 0
        except Exception as e:
            logger.error(f"Error checking alarm {alarm_name}: {e}")
            return False

    def check_eventbridge_rules_exist(self, instance_id):
        """Check if EventBridge rules exist for the instance.
        This is a read-only check used by the listServers Lambda function
        """
        eventbridge = boto3.client("events")
        shutdown_rule = f"shutdown-{instance_id}"
        start_rule = f"start-{instance_id}"

        try:
            rules = eventbridge.list_rules()
            rule_names = [rule["Name"] for rule in rules["Rules"]]

            return {"shutdown_rule_exists": shutdown_rule in rule_names, "start_rule_exists": start_rule in rule_names}
        except Exception as e:
            logger.error(f"Error checking EventBridge rules for {instance_id}: {e}")
            return {"shutdown_rule_exists": False, "start_rule_exists": False}

    def get_cached_running_minutes(self, instance_id):
        """
        Get cached running minutes from DynamoDB.
        Falls back to real-time calculation if cache is missing.

        Args:
            instance_id (str): EC2 instance ID

        Returns:
            dict: {
                'minutes': float - Total running minutes for the current month,
                'timestamp': str - ISO timestamp when value was calculated (or None if real-time)
            }
        """
        logger.info(f"------- get_cached_running_minutes: {instance_id}")

        try:
            # Import ddbHelper here to avoid circular dependency
            import ddbHelper

            dyn = ddbHelper.Dyn()

            # Get server config with cache
            config = dyn.get_server_config(instance_id)

            if config and config.get("runningMinutesCache") is not None:
                cache_timestamp_str = config.get("runningMinutesCacheTimestamp")

                if cache_timestamp_str:
                    logger.info(f"Using cached value for {instance_id}: {config['runningMinutesCache']} minutes")
                    return {"minutes": config["runningMinutesCache"], "timestamp": cache_timestamp_str}
                else:
                    logger.info(f"Cache timestamp missing for {instance_id}, falling back to calculation")
            else:
                logger.info(f"No cache found for {instance_id}, falling back to calculation")

        except Exception as e:
            logger.warning(f"Error reading cache for {instance_id}: {e}, falling back to calculation")

        # Fallback to real-time calculation
        return self.get_total_hours_running_per_month(instance_id)

    def get_total_hours_running_per_month(self, instanceId):
        """
        Calculate total running minutes for the current month from CloudTrail events.
        This is an expensive operation - prefer using get_cached_running_minutes() instead.
        """
        logger.info(f"------- get_total_hours_running_per_month {instanceId}")

        total_minutes = 0
        event_data = []

        # Get current instance state to handle running instances
        try:
            instance_response = self.ec2_client.describe_instances(InstanceIds=[instanceId])
            current_state = instance_response["Reservations"][0]["Instances"][0]["State"]["Name"]
        except Exception as e:
            logger.error(f"Error getting instance state: {e}")
            current_state = None

        paginator = self.ct_client.get_paginator("lookup_events")
        start_time = datetime(datetime.now().year, datetime.now().month, 1, tzinfo=timezone.utc)
        end_time = datetime.now(tz=timezone.utc)

        # Limit to relevant event names only
        event_names = ["RunInstances", "StartInstances", "StopInstances"]

        try:
            for page in paginator.paginate(
                LookupAttributes=[{"AttributeKey": "ResourceName", "AttributeValue": instanceId}],
                StartTime=start_time,
                EndTime=end_time,
                PaginationConfig={"MaxItems": 1000},  # Limit total items to prevent excessive API calls
            ):
                for event in page["Events"]:
                    event_name = event["EventName"]

                    # Skip irrelevant events early
                    if event_name not in event_names:
                        continue

                    # Parse CloudTrail event once
                    ct_event = json.loads(event["CloudTrailEvent"])
                    event_time = ct_event["eventTime"]

                    if event_name == "RunInstances":
                        event_data.append({"s": "StartInstances", "x": event_time})
                    elif event_name == "StartInstances":
                        # Check if this was a transition from stopped state
                        response_elements = ct_event.get("responseElements", {})
                        instances_set = response_elements.get("instancesSet", {})
                        items = instances_set.get("items", [])

                        for item in items:
                            if (
                                item.get("instanceId") == instanceId
                                and item.get("previousState", {}).get("name") == "stopped"
                            ):
                                event_data.append({"s": "StartInstances", "x": event_time})
                                break

                    elif event_name == "StopInstances":
                        # Check if this was a transition from running state
                        response_elements = ct_event.get("responseElements", {})
                        instances_set = response_elements.get("instancesSet", {})
                        items = instances_set.get("items", [])

                        for item in items:
                            if (
                                item.get("instanceId") == instanceId
                                and item.get("previousState", {}).get("name") == "running"
                            ):
                                event_data.append({"s": "StopInstances", "x": event_time})
                                break
        except Exception as e:
            logger.error(f"Error fetching CloudTrail events: {e}")
            return {"minutes": 0, "timestamp": None}

        # Sort events chronologically
        data_points = sorted(event_data, key=lambda k: k["x"])

        # Calculate runtime from event pairs
        start_event = None
        for point in data_points:
            if point["s"] == "StartInstances":
                start_event = datetime.fromisoformat(point["x"].replace("Z", "+00:00"))
            elif point["s"] == "StopInstances" and start_event:
                stop_event = datetime.fromisoformat(point["x"].replace("Z", "+00:00"))
                delta = stop_event - start_event
                total_minutes += round(delta.total_seconds() / 60, 2)
                start_event = None

        # Handle case where instance is currently running
        if start_event and current_state == "running":
            delta = end_time - start_event
            total_minutes += round(delta.total_seconds() / 60, 2)

        # Return dict with minutes and timestamp (None for real-time calculation)
        return {"minutes": total_minutes, "timestamp": None}

    def extract_state_event_time(self, evt, previous_state, instance_id):
        logger.info(f"------- extract_state_event_time {instance_id}")

        ct_event = evt.get("CloudTrailEvent")
        if ct_event:
            ct_event = json.loads(ct_event)
            response_elements = ct_event.get("responseElements")
            if response_elements:
                instances_set = response_elements.get("instancesSet")
                if instances_set:
                    items = instances_set.get("items")
                    if items:
                        for item in items:
                            if (
                                item.get("instanceId") == instance_id
                                and item["previousState"]["name"] == previous_state
                            ):
                                return ct_event["eventTime"]
        return None

    def list_instances_by_user_group(self, user_groups):
        user_instances = []
        for group_name in user_groups:
            # check if group_name starts with i- (instance_id)
            if not group_name.startswith("i-"):
                continue

            logger.info(f"Processing group: {group_name}")
            response = self.ec2_client.describe_instances(InstanceIds=[group_name])
            logger.info(response)
            if not response["Reservations"]:
                continue
            else:
                reservations = response["Reservations"]
                user_instances.extend(
                    [user_instances for reservation in reservations for user_instances in reservation["Instances"]]
                )

        # Get the total number of instances
        total_instances = len(user_instances)

        # Log the total number of instances
        logger.info(f"Total instances: {total_instances}")

        return {"Instances": user_instances, "TotalInstances": total_instances}

    def list_instances_by_app_tag(self, app_tag_value):
        """
        Lists all instances with the specified app tag value.

        Args:
            app_tag_value (str): The value of the App tag to filter by.

        Returns:
            dict: A dictionary containing the instances and total count.
        """
        logger.info(f"Listing instances by app tag: {app_tag_value}")

        filters = [
            {"Name": "tag:App", "Values": [app_tag_value]},
            {"Name": "instance-state-name", "Values": ["pending", "running", "stopping", "stopped"]},
        ]

        response = self.ec2_client.describe_instances(Filters=filters)

        instances = []
        for reservation in response["Reservations"]:
            instances.extend(reservation["Instances"])

        total_instances = len(instances)
        logger.info(f"Found {total_instances} instances with App tag: {app_tag_value}")

        return {"Instances": instances, "TotalInstances": total_instances}

    def list_server_by_id(self, instance_id):
        response = self.ec2_client.describe_instances(InstanceIds=[instance_id])

        if not response["Reservations"]:
            return []
        else:
            return {"Instances": response["Reservations"][0]["Instances"], "TotalInstances": 1}

    def list_servers_by_user(self, email, page=1, results_per_page=10):
        filters = [
            {"Name": "tag:App", "Values": [self.appValue]},
            {"Name": "instance-state-name", "Values": ["pending", "running", "stopping", "stopped"]},
            {"Name": "tag:User", "Values": [email]},
        ]

        return self.paginate_instances(filters, page, results_per_page)

    def list_servers_by_state(self, state, page=1, results_per_page=10):
        filters = [{"Name": "tag:App", "Values": [self.appValue]}, {"Name": "instance-state-name", "Values": [state]}]

        return self.paginate_instances(filters, page, results_per_page)

    def list_servers_by_group(self, group, page=1, results_per_page=10):
        filters = [
            {"Name": "tag:App", "Values": [self.appValue]},
            {"Name": "instance-state-name", "Values": ["pending", "running", "stopping", "stopped"]},
            {"Name": "tag:Group", "Values": [group]},
        ]

        return self.paginate_instances(filters, page, results_per_page)

    def list_all_servers(self, page=1, results_per_page=10):
        filters = [
            {"Name": "tag:App", "Values": [self.appValue]},
            {"Name": "instance-state-name", "Values": ["pending", "running", "stopping", "stopped"]},
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
            return {"Instances": [], "TotalInstances": 0}

        # Get the total number of instances
        total_instances = len(instances)

        start_index = (page - 1) * results_per_page
        end_index = start_index + results_per_page

        # Log the total number of instances
        logger.info(f"Total instances: {total_instances}")

        return {"Instances": instances[start_index:end_index], "TotalInstances": total_instances}

    def describe_iam_profile(self, instance_id, status, association_id=None):
        logger.info(f"------- describe_iam_profile: {instance_id} - {status}")

        if association_id:
            response = self.ec2_client.describe_iam_instance_profile_associations(AssociationIds=[association_id])
        else:
            response = self.ec2_client.describe_iam_instance_profile_associations(
                Filters=[
                    {"Name": "instance-id", "Values": [instance_id]},
                ]
            )

        matching_association = next(
            (
                {"AssociationId": rec["AssociationId"], "Arn": rec["IamInstanceProfile"]["Arn"]}
                for rec in response["IamInstanceProfileAssociations"]
                if rec["InstanceId"] == instance_id and rec["State"].lower() == status.lower()
            ),
            None,
        )

        return matching_association

    def describe_instance_status(self, instance_id):
        logger.info(f"------- describe_instance_status: {instance_id}")
        iamStatus = "Fail"
        initStatus = "Fail"

        statusRsp = self.ec2_client.describe_instance_status(InstanceIds=[instance_id])

        if not statusRsp["InstanceStatuses"]:
            instanceStatus = "Fail"
            systemStatus = "Fail"
        else:
            instanceStatus = statusRsp["InstanceStatuses"][0]["InstanceStatus"]["Status"]
            systemStatus = statusRsp["InstanceStatuses"][0]["SystemStatus"]["Status"]

        if instanceStatus == "ok" and systemStatus == "ok":
            initStatus = "ok"

        iamProfile = self.describe_iam_profile(instance_id, "associated")
        if iamProfile is not None and iamProfile["Arn"] == self.ec2InstanceProfileArn:
            iamStatus = "ok"

        return {"instanceId": instance_id, "initStatus": initStatus, "iamStatus": iamStatus}

    def describe_instance_attribute(self, instance_id, attribute):
        logger.info(f"------- describe_instance_attributes: {instance_id}")
        return self.ec2_client.describe_instance_attribute(Attribute=attribute, instanceId=instance_id)

    def update_instance_name_tag(self, instance_id, new_name):
        """
        Update the Name tag of an EC2 instance

        Args:
            instance_id (str): The EC2 instance ID
            new_name (str): The new name for the instance

        Returns:
            bool: True if successful, False otherwise
        """
        logger.info(f"------- update_instance_name_tag: {instance_id} -> {new_name}")

        try:
            # Update the Name tag
            self.ec2_client.create_tags(Resources=[instance_id], Tags=[{"Key": "Name", "Value": new_name}])
            logger.info(f"Successfully updated Name tag for instance {instance_id} to '{new_name}'")
            return True

        except ClientError as e:
            logger.error(f"Failed to update Name tag for instance {instance_id}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error updating Name tag for instance {instance_id}: {e}")
            return False
