import boto3
from botocore.exceptions import ClientError
import requests
import json
import os
import logging
import time
import re
from typing import Dict, Any, Optional
#from .errorHandler import ErrorHandler

logger = logging.getLogger()
logger.setLevel(logging.INFO)

class Utils:
    def __init__(self):
        logger.info("------- Utils Class Initialization")
        self.ssm = boto3.client('ssm')
        self.ses = boto3.client('ses')
        self.admin_group_name = os.getenv('ADMIN_GROUP_NAME', 'admin')  # Default to 'admin' if not set
    
    def capitalize_first_letter(self, text):
        """
        Capitalizes the first letter of each word in the given text, while preserving the original case of the remaining letters.
        
        Args:
            text (str): The input text to be capitalized.
            
        Returns:
            str: The text with the first letter of each word capitalized.
        """
        words = text.split()
        capitalized_words = [word[0].upper() + word[1:] for word in words]
        return ' '.join(capitalized_words)
    
    def get_metrics_data(self, instance_id, namespace, metric_name, unit, statistics, start_time, end_time, period=300):
        logger.info(f"------- get_metrics_data: {metric_name} - {instance_id}")
        cw_client = boto3.client('cloudwatch')

        dimensions = [
            {'Name': 'InstanceId', 'Value': instance_id}
        ]

        if metric_name == "cpu_usage_active":
            dimensions.append({'Name': 'cpu', 'Value': "cpu-total"})

        try:
            response = cw_client.get_metric_statistics(
                Namespace=namespace,
                MetricName=metric_name,
                Dimensions=dimensions,
                StartTime=start_time,
                EndTime=end_time,
                Period=period,
                Statistics=[statistics],
                Unit=unit
            )

            if not response["Datapoints"]:
                logger.warning(f'No Datapoint for namespace: {metric_name} - InstanceId: {instance_id}')
                return "[]"

            # Format data points for ApexCharts
            datapoints = []
            for point in sorted(response.get('Datapoints', []), key=lambda x: x['Timestamp']):
                datapoints.append({
                    # Convert to milliseconds
                    'x': int(point['Timestamp'].timestamp() * 1000), 
                    # Each datapoint contains keys like 'Timestamp', 'Average', 'Sum', 'Maximum', etc. - the actual statistic names.
                    'y': round(point.get(statistics, 0), 2)
                })
            
            if len(datapoints) > 0:
                logger.info(f"Fetched {len(datapoints)} points for {metric_name}. First: {datapoints[0]}, Last: {datapoints[-1]}")
            else:
                logger.warning(f"No datapoints found for {metric_name} in namespace {namespace} with dimensions {dimensions}")

            return json.dumps(sorted(datapoints, key=lambda x: x['x']))

        except Exception as e:
            logger.error(f'Something went wrong: {str(e)}')
            return "[]"

    def response(self, status_code, body, headers={}):
        """
        Returns a dictionary containing the status code, body, and headers.

        Args:
            status_code (int): The HTTP status code.
            body (str): The response body.
            headers (dict, optional): The response headers. Defaults to {}.

        Returns:
            dict: A dictionary containing the status code, body, and headers.
        """
        if bool(headers): # Return True if dictionary is not empty # use json.dumps for body when using with API GW
            return {"statusCode": status_code, "body": body, "headers": headers}
        else:
            return {"statusCode": status_code, "body": body }

    # To be removed - Moved it to Auth Layer
    def extract_auth_token(self, event):
        """Extract authorization token from Lambda event."""
        try:
            return event['request']['headers']['authorization']
        except KeyError:
            if 'request' not in event:
                raise ValueError("No request found in event")
            elif 'headers' not in event['request']:
                raise ValueError("No headers found in request")
            else:
                raise ValueError("No Authorization header found")

    def retry_operation(self, operation, max_retries, delay):
        retries = 0
        while retries < max_retries:
            if operation():
                return True
            retries += 1
            time.sleep(delay)
        return False

    def is_valid_cron(self, cron_expression):
        """
        Basic validation for cron expressions (5-field format)
        
        Args:
            cron_expression: String containing cron expression
            
        Returns:
            bool: True if valid format, False otherwise
        """
        if not cron_expression or not isinstance(cron_expression, str):
            return False

        cron_pattern = r'^(((((\d+,)+\d+|(\d+(\/|-|#)\d+)|\d+L?|\*(\/\d+)?|L(-\d+)?|\?|[A-Z]{3}(-[A-Z]{3})?) ?){5,7}))$'
    
        return bool(re.match(cron_pattern, cron_expression))        
   
    def check_user_authorization(self, user_sub_or_groups, server_id, required_permission_or_email='read_server', ec2_utils=None):
        """
        Comprehensive authorization check for server actions using DynamoDB membership.
        Supports both old and new calling patterns for backward compatibility.
        
        Old pattern: check_user_authorization(cognito_groups, instance_id, user_email, ec2_utils)
        New pattern: check_user_authorization(user_sub, server_id, required_permission, user_email, ec2_utils)
        
        Args:
            user_sub_or_groups: Either Cognito user sub (str) or list of Cognito groups (list) - for backward compatibility
            server_id (str): EC2 instance ID
            required_permission_or_email: Either permission level (str) or user email (str) - for backward compatibility
            ec2_utils (optional): EC2 utility object for fallback authorization
            
        Returns:
            tuple: (bool, str, str) - (is_authorized, user_role, authorization_reason)
                   For backward compatibility, may return (bool, str) for old calling pattern
        """
        try:
            # Detect calling pattern based on first argument type
            if isinstance(user_sub_or_groups, list):
                # Old calling pattern: (cognito_groups, instance_id, user_email, ec2_utils)
                cognito_groups = user_sub_or_groups
                instance_id = server_id
                user_email = required_permission_or_email
                
                logger.info(f"Using legacy authorization check: user={user_email}, instance={instance_id}, groups={cognito_groups}")
                
                # Log authorization attempt for legacy pattern
                # ErrorHandler.log_authorization_attempt(
                #     user_sub='legacy_user',
                #     server_id=instance_id,
                #     required_permission='legacy_check',
                #     success=False,
                #     reason='Using legacy Cognito groups authorization'
                # )
                
                # Check if user is admin using old method
                if self.admin_group_name in cognito_groups:
                    # ErrorHandler.log_authorization_attempt(
                    #     user_sub='legacy_user',
                    #     server_id=instance_id,
                    #     required_permission='legacy_check',
                    #     user_role='admin_group',
                    #     success=True,
                    #     reason='Admin group membership'
                    # )
                    return True, "admin_group"
                    
                # Check if user is in instance-specific group
                if cognito_groups:
                    for group in cognito_groups:
                        if group == instance_id:
                            # ErrorHandler.log_authorization_attempt(
                            #     user_sub='legacy_user',
                            #     server_id=instance_id,
                            #     required_permission='legacy_check',
                            #     user_role='instance_group',
                            #     success=True,
                            #     reason='Instance group membership'
                            # )
                            return True, "instance_group"
                
                # Check if user is the owner based on instance tags
                if ec2_utils:
                    try:
                        server_info = ec2_utils.list_server_by_id(instance_id)
                        if server_info["TotalInstances"] > 0:
                            instance = server_info['Instances'][0]
                            tags = instance.get('Tags', [])
                            
                            for tag in tags:
                                if tag['Key'] == 'Owner' and tag['Value'] == user_email:
                                    # ErrorHandler.log_authorization_attempt(
                                    #     user_sub='legacy_user',
                                    #     server_id=instance_id,
                                    #     required_permission='legacy_check',
                                    #     user_role='instance_owner',
                                    #     success=True,
                                    #     reason='Instance owner tag match'
                                    # )
                                    return True, "instance_owner"
                    except Exception as e:
                        logger.warning(f"Error checking owner tag: {str(e)}")
                        # ErrorHandler.log_error('INTERNAL_ERROR', 
                        #                      context={'operation': 'check_owner_tag', 'instance_id': instance_id},
                        #                      exception=e, error=str(e))
                
                # Not authorized - log the failure
                # ErrorHandler.log_authorization_attempt(
                #     user_sub='legacy_user',
                #     server_id=instance_id,
                #     required_permission='legacy_check',
                #     success=False,
                #     reason='No matching groups or owner tag'
                # )
                return False, "unauthorized"
                
            else:
                # New calling pattern: (user_sub, server_id, required_permission, ...)
                user_sub = user_sub_or_groups
                required_permission = required_permission_or_email if isinstance(required_permission_or_email, str) and required_permission_or_email in ['read_server', 'read_metrics', 'read_config', 'control_server', 'manage_users', 'manage_config'] else 'read_server'
                
                # Import here to avoid circular dependencies
                import sys
                sys.path.append('/opt/python')
                try:
                    from authHelper import Auth
                except ImportError:
                    # Fallback for local testing
                    sys.path.insert(0, '../authHelper')
                    from authHelper import Auth
                
                # Initialize Auth helper
                cognito_pool_id = os.getenv('COGNITO_USER_POOL_ID', 'dummy-pool-id')
                auth = Auth(cognito_pool_id)
                
                logger.info(f"Using DynamoDB authorization check: user={user_sub}, server={server_id}, permission={required_permission}")
                
                # Use the new DynamoDB-based permission checking
                try:
                    is_authorized, user_role, auth_reason = auth.check_user_permission(user_sub, server_id, required_permission)
                    
                    # Log the authorization attempt
                    # ErrorHandler.log_authorization_attempt(
                    #     user_sub=user_sub,
                    #     server_id=server_id,
                    #     required_permission=required_permission,
                    #     user_role=user_role,
                    #     success=is_authorized,
                    #     reason=auth_reason
                    # )
                    
                    if is_authorized:
                        logger.info(f"Authorization granted: user={user_sub}, server={server_id}, role={user_role}")
                        return True, user_role, auth_reason
                    else:
                        logger.warning(f"Authorization denied: user={user_sub}, server={server_id}, reason={auth_reason}")
                        return False, user_role, auth_reason
                        
                except Exception as e:
                    error_msg = f"Error checking permissions: {str(e)}"
                    logger.error(f"Authorization check failed: error={error_msg}")
                    
                    # Log the error with context
                    # ErrorHandler.log_error('AUTHORIZATION_FAILED',
                    #                      context={'user_sub': user_sub, 'server_id': server_id, 'required_permission': required_permission},
                    #                      exception=e, reason=str(e))
                    
                    return False, None, error_msg
                    
        except Exception as e:
            error_msg = f"Error checking permissions: {str(e)}"
            logger.error(f"Authorization check failed: error={error_msg}")
            
            # Log the error
            # ErrorHandler.log_error('AUTHORIZATION_FAILED',
            #                      context={'operation': 'check_user_authorization'},
            #                      exception=e, reason=str(e))
            
            # For backward compatibility, return the old format on error
            if isinstance(user_sub_or_groups, list):
                return False, "error"
            else:
                return False, None, error_msg

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

    def put_ssm_param(self, paramKey, paramValue, paramType):
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
                
    def retrieve_extension_value(self, url: str) -> Optional[Dict[Any, Any]]:
        """
        Retrieves extension value from a local endpoint with AWS authentication.
        
        Args:
            url (str): The endpoint path to retrieve the extension value from
            
        Returns:
            Optional[Dict]: JSON response data or None if request fails
            
        Raises:
            RequestException: If the HTTP request fails
            JSONDecodeError: If the response cannot be parsed as JSON
        """
        try:
            port = os.environ.get['PARAMETERS_SECRETS_EXTENSION_HTTP_PORT',2773]

            # Construct full URL
            base_url = f'http://localhost:{port}'
            full_url = f'{base_url}{url}'
            
            # Prepare headers with AWS authentication
            headers = {
                "X-Aws-Parameters-Secrets-Token": os.environ.get('AWS_SESSION_TOKEN'),
                "Accept": "application/json"
            }
            
            # Make the request
            response = requests.get(
                url=full_url,
                headers=headers,
                timeout=30  # Add timeout to prevent hanging
            )
            
            # Raise an exception for bad status codes (4xx, 5xx)
            response.raise_for_status()
            
            # Parse and return JSON response
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"HTTP Request failed: {str(e)}")
            return None
        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON response: {str(e)}")
            return None
        except Exception as e:
            print(f"Unexpected error occurred: {str(e)}")
            return None

    def send_server_notification_email(self, recipient_email: str, server_name: str, action: str, 
                                     instance_id: str, sender_email: str = None) -> bool:
        """
        Sends email notification when a server is started or stopped.
        
        Args:
            recipient_email (str): Email address to send notification to
            server_name (str): Name of the Minecraft server
            action (str): Action performed ('started', 'stopped', 'restarted')
            instance_id (str): EC2 instance ID
            sender_email (str, optional): Sender email address. If None, uses SSM parameter
            
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        try:
            # Get sender email from SSM parameter if not provided
            if not sender_email:
                sender_email = self.get_ssm_param('/minecraft-dashboard/notification-sender-email')
                if not sender_email:
                    logger.error("No sender email configured in SSM parameter '/minecraft-dashboard/notification-sender-email'")
                    return False
            
            # Prepare email content based on action
            action_past_tense = {
                'start': 'started',
                'stop': 'stopped', 
                'restart': 'restarted'
            }.get(action.lower(), action)
            
            subject = f"Minecraft Server {action_past_tense.title()}: {server_name}"
            
            # HTML email body
            html_body = f"""
            <html>
            <head></head>
            <body>
                <h2>Minecraft Server Notification</h2>
                <p>Your Minecraft server has been <strong>{action_past_tense}</strong>.</p>
                
                <table style="border-collapse: collapse; margin: 20px 0;">
                    <tr>
                        <td style="padding: 8px; font-weight: bold;">Server Name:</td>
                        <td style="padding: 8px;">{server_name}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; font-weight: bold;">Action:</td>
                        <td style="padding: 8px;">{action_past_tense.title()}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; font-weight: bold;">Instance ID:</td>
                        <td style="padding: 8px;">{instance_id}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; font-weight: bold;">Time:</td>
                        <td style="padding: 8px;">{time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}</td>
                    </tr>
                </table>
                
                <p>You can manage your server through the <a href="{os.getenv('DASHBOARD_URL', 'https://your-dashboard-url.com')}">Minecraft Server Dashboard</a>.</p>
                
                <hr style="margin: 20px 0;">
                <p style="font-size: 12px; color: #666;">
                    This is an automated notification from your Minecraft Server Dashboard.
                </p>
            </body>
            </html>
            """
            
            # Plain text version
            text_body = f"""
Minecraft Server Notification

Your Minecraft server has been {action_past_tense}.

Server Name: {server_name}
Action: {action_past_tense.title()}
Instance ID: {instance_id}
Time: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}

You can manage your server through the Minecraft Server Dashboard: {os.getenv('DASHBOARD_URL', 'https://your-dashboard-url.com')}

This is an automated notification from your Minecraft Server Dashboard.
            """
            
            # Send email using SES
            response = self.ses.send_email(
                Source=sender_email,
                Destination={
                    'ToAddresses': [recipient_email]
                },
                Message={
                    'Subject': {
                        'Data': subject,
                        'Charset': 'UTF-8'
                    },
                    'Body': {
                        'Text': {
                            'Data': text_body,
                            'Charset': 'UTF-8'
                        },
                        'Html': {
                            'Data': html_body,
                            'Charset': 'UTF-8'
                        }
                    }
                }
            )
            
            if response['ResponseMetadata']['HTTPStatusCode'] == 200:
                logger.info(f"Email notification sent successfully to {recipient_email} for server {server_name} ({action_past_tense})")
                return True
            else:
                logger.error(f"Failed to send email notification. SES response: {response}")
                return False
                
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logger.error(f"SES ClientError: {error_code} - {error_message}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending email notification: {str(e)}")
            return False