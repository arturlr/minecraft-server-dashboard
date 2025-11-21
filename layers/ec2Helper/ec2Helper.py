import sys
import boto3
import logging
import os
import json
from datetime import datetime, timezone
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key, Attr

sys.path.insert(0, '/opt/utilHelper')
import utilHelper

utl = utilHelper.Utils()

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
        self.cw_client = boto3.client('cloudwatch')
        self.sts_client = boto3.client('sts')
        self.account_id = self.sts_client.get_caller_identity()['Account']
        self.appValue = os.getenv('TAG_APP_VALUE')
        self.ec2InstanceProfileArn = os.getenv('EC2_INSTANCE_PROFILE_ARN')

    def get_instance_attributes_from_tags(self,instance_id):
        """
        Retrieves the instance attributes from the EC2 tags.

        Args:
            instance_id (str): The ID of the EC2 instance.

        Returns:
            dict: A dictionary containing the instance attributes with proper type conversions.
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
            
            # Get values with proper type conversions
            alarm_threshold = tag_mapping.get('alarmthreshold', '')
            alarm_evaluation_period = tag_mapping.get('alarmevaluationperiod', '')
            
            # Convert alarmThreshold to Float if present
            if alarm_threshold:
                try:
                    alarm_threshold = float(alarm_threshold)
                except (ValueError, TypeError):
                    logger.warning(f"Invalid alarmThreshold value: {alarm_threshold}. Using default 0.0")
                    alarm_threshold = 0.0
            else:
                # Default value for alarmThreshold
                alarm_threshold = 0.0
                
            # Convert alarmEvaluationPeriod to Int if present
            if alarm_evaluation_period:
                try:
                    alarm_evaluation_period = int(alarm_evaluation_period)
                except (ValueError, TypeError):
                    logger.warning(f"Invalid alarmEvaluationPeriod value: {alarm_evaluation_period}. Using default 0")
                    alarm_evaluation_period = 0
            else:
                # Default value for alarmEvaluationPeriod
                alarm_evaluation_period = 0

            # returning following the Appsync Schema for ServerConfig
            return {
                'id': instance_id,
                'shutdownMethod': tag_mapping.get('shutdownmethod', ''),  
                'stopScheduleExpression': tag_mapping.get('stopscheduleexpression', ''),
                'startScheduleExpression': tag_mapping.get('startscheduleexpression', ''),
                'alarmType': tag_mapping.get('alarmtype', ''),
                'alarmThreshold': alarm_threshold,  # Now properly typed as Float
                'alarmEvaluationPeriod': alarm_evaluation_period,  # Now properly typed as Int
                'runCommand': tag_mapping.get('runcommand', ''),
                'workDir': tag_mapping.get('workdir', ''),
                'groupMembers': ''
            }
        
        except Exception as e:
            logger.error(f"Error getting tags: {e}")
            # Return default values in case of error
            return {
                'id': instance_id,
                'shutdownMethod': '',  
                'stopScheduleExpression': '',
                'startScheduleExpression': '',
                'alarmType': '',
                'alarmThreshold': 0.0,  # Default Float value
                'alarmEvaluationPeriod': 0,  # Default Int value
                'runCommand': '',
                'workDir': '',
                'groupMembers': ''
            }
        
    def set_instance_attributes_to_tags(self,input):
        instance_id = input.get('id', None)
        if not instance_id:
            raise ValueError("Instance ID is required")

        logger.info("Setting instance attributes for " + instance_id)

        serverConfigInput = {k: v for k, v in input.items() if k != 'id' and v is not None and v != ''}

        # Getting current EC2 Tags
        ec2_attrs = self.get_instance_attributes_from_tags(instance_id)

        ec2_tag_mapping = {
            utl.capitalize_first_letter(key): value 
            for key, value in serverConfigInput.items()
        }

        # logger.info(f"input : {input}")
        # logger.info(f"ec2_tag_mapping : {ec2_tag_mapping}")
        
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
 
            # return serverConfigInput keys and values
            return {
                'id': instance_id,
                **serverConfigInput
            }
           
        except Exception as e:
            logger.error(f"Error setting tags: {e}")

    def update_alarm(self, instance_id, alarm_metric, alarm_threshold, alarm_evaluation_period):
        logger.info("------- update_alarm : " + instance_id)

        dimensions=[]
        statistic="Average" 
        namespace="CWAgent"
        dimensions.append({'Name': 'InstanceId','Value': instance_id})
        if alarm_metric == "CPUUtilization":
            alarmMetricName = "cpu_usage_active"        
            dimensions.append({'Name': 'cpu','Value': "cpu-total"})
        elif alarm_metric == "Connections":
            alarmMetricName = "UserCount"
            statistic="Maximum"
            namespace="MinecraftDashboard"

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
            ComparisonOperator="LessThanOrEqualToThreshold"   
        )

        logger.info(f"Alarm configured to {alarm_metric} with threshold {alarm_threshold} and evaluation period {alarm_evaluation_period}")
    
    def remove_alarm(self, instance_id):
        logger.info("------- remove_alarm : " + instance_id)

        alarm_name = instance_id + "-" + "minecraft-server"
        
        # Check if alarm exists before deleting
        try:
            alarms = self.cw_client.describe_alarms(AlarmNames=[alarm_name])
            if alarms['MetricAlarms']:
                self.cw_client.delete_alarms(
                    AlarmNames=[
                        alarm_name
                    ]
                )
                logger.info(f"Alarm {alarm_name} deleted successfully")
            else:
                logger.info(f"Alarm {alarm_name} does not exist")
        except ClientError as e:
            logger.error(f"Error checking/deleting alarm: {e}")

    def configure_shutdown_event(self, instance_id, cron_expression):
        eventbridge = boto3.client('events')
        
        logger.info(f"Original cron expression: {cron_expression}")
        
        # Validate and format the cron expression for EventBridge
        formatted_schedule = self._format_schedule_expression(cron_expression)
        logger.info(f"Formatted schedule expression: {formatted_schedule}")
        
        if not formatted_schedule:
            logger.error(f"Invalid cron expression: {cron_expression}")
            raise ValueError(f"Invalid cron expression: {cron_expression}")
        
        # Create the rule with cron expression
        rule_name = f"shutdown-{instance_id}"
        logger.info(f"Creating EventBridge rule {rule_name} with schedule: {formatted_schedule}")
        
        eventbridge.put_rule(
            Name=rule_name,
            ScheduleExpression=formatted_schedule,
            State='ENABLED'
        )
        
        # Create the target for EC2 stop automation
        eventbridge.put_targets(
            Rule=rule_name,
            Targets=[{
                'Id': f"shutdown-target-{instance_id}",
                'Arn': f"arn:aws:automate:{aws_region}:ec2:stop",
                'RoleArn': f"arn:aws:iam::{self.account_id}:role/aws-service-role/events.amazonaws.com/AWSServiceRoleForEvents",
                'Input': json.dumps({"InstanceId": instance_id})
            }]
        )
        logger.info(f"Shutdown event configured for {instance_id} with schedule: {formatted_schedule}")

    def remove_shutdown_event(self, instance_id):
        eventbridge = boto3.client('events')

        # Remove the rule and target
        rule_name = f"shutdown-{instance_id}"
        try:
            # Check if rule exists
            rules = eventbridge.list_rules(NamePrefix=rule_name)
            if not rules.get('Rules'):
                logger.info(f"No shutdown event rule found for {instance_id}")
                return
                
            eventbridge.remove_targets(
                Rule=rule_name,
                Ids=[f"shutdown-target-{instance_id}"]
            )
            eventbridge.delete_rule(Name=rule_name)
            logger.info(f"Shutdown event removed for {instance_id}")

        except ClientError as e:
            logger.error(f"Error removing shutdown event: {e}")

    def configure_start_event(self, instance_id, cron_expression):
        """Configure EventBridge rule to start EC2 instance on schedule"""
        eventbridge = boto3.client('events')
        
        logger.info(f"Original start cron expression: {cron_expression}")
        
        # Validate and format the cron expression for EventBridge
        formatted_schedule = self._format_schedule_expression(cron_expression)
        logger.info(f"Formatted start schedule expression: {formatted_schedule}")
        
        if not formatted_schedule:
            logger.error(f"Invalid cron expression: {cron_expression}")
            raise ValueError(f"Invalid cron expression: {cron_expression}")
        
        # Create the rule with cron expression for starting
        rule_name = f"start-{instance_id}"
        logger.info(f"Creating EventBridge start rule {rule_name} with schedule: {formatted_schedule}")
        
        eventbridge.put_rule(
            Name=rule_name,
            ScheduleExpression=formatted_schedule,
            State='ENABLED'
        )
        
        # Create the target to start the instance
        eventbridge.put_targets(
            Rule=rule_name,
            Targets=[{
                'Id': f"start-target-{instance_id}",
                'Arn': f"arn:aws:automate:{aws_region}:ec2:start",
                'RoleArn': f"arn:aws:iam::{self.account_id}:role/aws-service-role/events.amazonaws.com/AWSServiceRoleForEvents",
                'Input': json.dumps({"InstanceId": instance_id})
            }]
        )
        logger.info(f"Start event configured for {instance_id} with schedule: {formatted_schedule}")

    def remove_start_event(self, instance_id):
        """Remove EventBridge rule for starting EC2 instance"""
        eventbridge = boto3.client('events')

        # Remove the rule and target
        rule_name = f"start-{instance_id}"
        try:
            # Check if rule exists
            rules = eventbridge.list_rules(NamePrefix=rule_name)
            if not rules.get('Rules'):
                logger.info(f"No start event rule found for {instance_id}")
                return
                
            eventbridge.remove_targets(
                Rule=rule_name,
                Ids=[f"start-target-{instance_id}"]
            )
            eventbridge.delete_rule(Name=rule_name)
            logger.info(f"Start event removed for {instance_id}")

        except ClientError as e:
            logger.error(f"Error removing start event: {e}")

    def _format_schedule_expression(self, cron_expression):
        """
        Format and validate cron expression for EventBridge.
        EventBridge requires cron expressions to be in the format: cron(minutes hours day month day-of-week year)
        
        EventBridge-specific rules:
        - Either day-of-month OR day-of-week must be '?' (not both can have specific values)
        - Day-of-week uses 1-7 (1=Monday, 7=Sunday) or SUN-SAT
        - Supports special characters: * ? , - / L W #
        
        Args:
            cron_expression (str): Standard cron expression (5 fields) or EventBridge format (6 fields)
            
        Returns:
            str: Properly formatted EventBridge schedule expression or None if invalid
        """
        if not cron_expression or not isinstance(cron_expression, str):
            return None
            
        cron_expression = cron_expression.strip()
        
        # If already in EventBridge format, validate and return
        if cron_expression.startswith('cron(') and cron_expression.endswith(')'):
            # Extract the cron part and validate
            cron_part = cron_expression[5:-1]  # Remove 'cron(' and ')'
            fields = cron_part.split()
            if len(fields) == 6:
                minute, hour, day, month, day_of_week, year = fields
                # Validate EventBridge-specific rule: day and day_of_week can't both have specific values
                if not self._validate_day_fields(day, day_of_week):
                    logger.warning(f"EventBridge requires either day-of-month OR day-of-week to be '?': {cron_expression}")
                    return None
                return cron_expression
            else:
                logger.warning(f"Invalid EventBridge cron format: {cron_expression}")
                return None
        
        # Handle standard 5-field cron expression
        fields = cron_expression.split()
        if len(fields) == 5:
            # Standard cron: minute hour day month day-of-week
            # EventBridge cron: minute hour day month day-of-week year
            minute, hour, day, month, day_of_week = fields
            
            # Validate basic format first
            if not self._validate_cron_field(minute, 0, 59) or \
               not self._validate_cron_field(hour, 0, 23) or \
               not self._validate_dow_field(day_of_week):
                logger.warning(f"Invalid cron expression values: {cron_expression}")
                return None
            
            # Convert day-of-week from standard cron (0-6, Sunday=0) to EventBridge (1-7, Sunday=7)
            converted_dow = self._convert_day_of_week(day_of_week)
            if not converted_dow:
                logger.warning(f"Failed to convert day-of-week: {day_of_week}")
                return None
            
            # Apply EventBridge rule: if both day and day-of-week are specified, use '?' for day
            # This handles the common case where users specify both (which EventBridge doesn't allow)
            if day != '*' and day != '?' and converted_dow != '*' and converted_dow != '?':
                logger.info(f"Both day ({day}) and day-of-week ({converted_dow}) specified. Using day-of-week and setting day to '?'")
                day = '?'
            
            # Convert to EventBridge format (add year field)
            eventbridge_cron = f"cron({minute} {hour} {day} {month} {converted_dow} *)"
            return eventbridge_cron
        
        logger.warning(f"Invalid cron expression format: {cron_expression}")
        return None
    
    def _convert_day_of_week(self, day_of_week):
        """
        Convert day-of-week from standard cron format (0-6, Sunday=0) to EventBridge format (1-7, Sunday=7).
        
        Args:
            day_of_week (str): Day of week field from cron expression
            
        Returns:
            str: Converted day-of-week field or None if invalid
        """
        if day_of_week == '*':
            return '*'
            
        # Handle comma-separated values
        if ',' in day_of_week:
            values = day_of_week.split(',')
            converted_values = []
            for val in values:
                converted_val = self._convert_single_dow(val.strip())
                if converted_val is None:
                    return None
                converted_values.append(converted_val)
            return ','.join(converted_values)
        
        # Handle ranges
        if '-' in day_of_week:
            try:
                start, end = day_of_week.split('-')
                start_converted = self._convert_single_dow(start.strip())
                end_converted = self._convert_single_dow(end.strip())
                if start_converted is None or end_converted is None:
                    return None
                return f"{start_converted}-{end_converted}"
            except ValueError:
                return None
        
        # Handle single value
        return self._convert_single_dow(day_of_week)
    
    def _convert_single_dow(self, value):
        """
        Convert a single day-of-week value from standard cron (0-6) to EventBridge (1-7).
        
        Args:
            value (str): Single day-of-week value
            
        Returns:
            str: Converted value or None if invalid
        """
        if value == '0':  # Sunday
            return '7'
        elif value.isdigit() and 1 <= int(value) <= 6:
            return value
        else:
            return None
    
    def _validate_dow_field(self, day_of_week):
        """
        Validate day-of-week field for standard cron format (0-6, where 0=Sunday).
        
        Args:
            day_of_week (str): Day of week field from cron expression
            
        Returns:
            bool: True if valid, False otherwise
        """
        if day_of_week == '*':
            return True
            
        # Handle comma-separated values
        if ',' in day_of_week:
            values = day_of_week.split(',')
            return all(self._validate_single_dow_value(val.strip()) for val in values)
        
        # Handle ranges
        if '-' in day_of_week:
            try:
                start, end = day_of_week.split('-')
                return (self._validate_single_dow_value(start.strip()) and 
                       self._validate_single_dow_value(end.strip()))
            except ValueError:
                return False
        
        # Handle step values
        if '/' in day_of_week:
            try:
                base, step = day_of_week.split('/')
                return (self._validate_dow_field(base) and 
                       step.isdigit() and int(step) > 0)
            except ValueError:
                return False
        
        # Single value
        return self._validate_single_dow_value(day_of_week)
    
    def _validate_single_dow_value(self, value):
        """Validate a single day-of-week value for standard cron (0-6)."""
        try:
            val = int(value)
            return 0 <= val <= 6  # Standard cron allows 0-6
        except ValueError:
            return False
    
    def _validate_cron_field(self, field, min_val, max_val, allow_star=True):
        """
        Validate a single cron field.
        
        Args:
            field (str): The cron field to validate
            min_val (int): Minimum allowed value
            max_val (int): Maximum allowed value
            allow_star (bool): Whether '*' is allowed
            
        Returns:
            bool: True if valid, False otherwise
        """
        if not field:
            return False
            
        # Allow wildcard
        if field == '*' and allow_star:
            return True
            
        # Handle comma-separated values
        if ',' in field:
            values = field.split(',')
            return all(self._validate_single_cron_value(val, min_val, max_val) for val in values)
        
        # Handle ranges
        if '-' in field:
            try:
                start, end = field.split('-')
                return (self._validate_single_cron_value(start, min_val, max_val) and 
                       self._validate_single_cron_value(end, min_val, max_val))
            except ValueError:
                return False
        
        # Handle step values
        if '/' in field:
            try:
                base, step = field.split('/')
                return (self._validate_cron_field(base, min_val, max_val, allow_star) and 
                       step.isdigit() and int(step) > 0)
            except ValueError:
                return False
        
        # Single value
        return self._validate_single_cron_value(field, min_val, max_val)
    
    def _validate_single_cron_value(self, value, min_val, max_val):
        """Validate a single cron value."""
        try:
            val = int(value)
            return min_val <= val <= max_val
        except ValueError:
            return False
    
    def _validate_day_fields(self, day, day_of_week):
        """
        Validate EventBridge-specific rule: either day-of-month OR day-of-week must be '?'
        Both can't have specific values at the same time.
        
        Args:
            day (str): Day-of-month field
            day_of_week (str): Day-of-week field
            
        Returns:
            bool: True if valid according to EventBridge rules
        """
        # Both wildcards is OK
        if (day == '*' or day == '?') and (day_of_week == '*' or day_of_week == '?'):
            return True
        
        # One specific, one wildcard/question is OK
        if (day != '*' and day != '?') and (day_of_week == '*' or day_of_week == '?'):
            return True
        if (day == '*' or day == '?') and (day_of_week != '*' and day_of_week != '?'):
            return True
        
        # Both specific is NOT OK for EventBridge
        logger.warning(f"EventBridge validation failed: day={day}, day_of_week={day_of_week}")
        return False
    
    def check_alarm_exists(self, instance_id):
        """Check if CloudWatch alarm exists for the instance."""
        alarm_name = f"{instance_id}-minecraft-server"
        try:
            alarms = self.cw_client.describe_alarms(AlarmNames=[alarm_name])
            return len(alarms['MetricAlarms']) > 0
        except Exception as e:
            logger.error(f"Error checking alarm {alarm_name}: {e}")
            return False
    
    def check_eventbridge_rules_exist(self, instance_id):
        """Check if EventBridge rules exist for the instance."""
        eventbridge = boto3.client('events')
        shutdown_rule = f"shutdown-{instance_id}"
        start_rule = f"start-{instance_id}"
        
        try:
            rules = eventbridge.list_rules()
            rule_names = [rule['Name'] for rule in rules['Rules']]
            
            return {
                'shutdown_rule_exists': shutdown_rule in rule_names,
                'start_rule_exists': start_rule in rule_names
            }
        except Exception as e:
            logger.error(f"Error checking EventBridge rules for {instance_id}: {e}")
            return {'shutdown_rule_exists': False, 'start_rule_exists': False}

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

    def extract_state_event_time(self, evt, previous_state, instance_id):
        logger.info(f"------- extract_state_event_time {instance_id}")

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
                            if item.get('instanceId') == instance_id and item['previousState']['name'] == previous_state:
                                return ct_event['eventTime']
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
                user_instances.extend([user_instances for reservation in reservations for user_instances in reservation["Instances"]])

        # Get the total number of instances
        total_instances = len(user_instances)

        # Log the total number of instances
        logger.info(f"Total instances: {total_instances}")

        return {
            "Instances": user_instances,
            "TotalInstances": total_instances
        }
        
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
            {"Name": "instance-state-name", "Values": ["pending", "running", "stopping", "stopped"]}
        ]
        
        response = self.ec2_client.describe_instances(Filters=filters)
        
        instances = []
        for reservation in response["Reservations"]:
            instances.extend(reservation["Instances"])
            
        total_instances = len(instances)
        logger.info(f"Found {total_instances} instances with App tag: {app_tag_value}")
        
        return {
            "Instances": instances,
            "TotalInstances": total_instances
        }

    def list_server_by_id(self, instance_id):
        response = self.ec2_client.describe_instances(InstanceIds=[instance_id])

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

    def describe_instance_attributes(self, instance_id):
        logger.info(f"------- describe_instance_attributes: {instance_id}")
        response = self.ec2_client.describe_instance_attribute(
            Attribute='userData',
            instanceId=instance_id
        )

   