import boto3
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key, Attr
import requests
from requests.exceptions import RequestException
import json
import os
import logging
import time
from typing import Dict, Any, Optional

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

    def retry_operation(self, operation, max_retries, delay):
        retries = 0
        while retries < max_retries:
            if operation():
                return True
            retries += 1
            time.sleep(delay)
        return False
        
    def is_admin_user(self, cognito_groups):
        """
        Checks if a user belongs to the admin group
        
        Args:
            cognito_groups (list): List of Cognito groups the user belongs to
            
        Returns:
            bool: True if user is in admin group, False otherwise
        """
        if not cognito_groups:
            return False
            
        return self.admin_group_name in cognito_groups
        
    def check_user_authorization(self, cognito_groups, instance_id, user_email, ec2_utils):
        """
        Comprehensive authorization check for server actions
        
        Args:
            cognito_groups (list): List of Cognito groups the user belongs to
            instance_id (str): EC2 instance ID
            user_email (str): Email of the user attempting the action
            ec2_utils: EC2 utility object for instance operations
            
        Returns:
            tuple: (bool, str) - (is_authorized, authorization_reason)
        """
        # Check if user is admin
        if self.is_admin_user(cognito_groups):
            return True, "admin_group"
            
        # Check if user is in instance-specific group
        if cognito_groups:
            for group in cognito_groups:
                if group == instance_id:
                    return True, "instance_group"
        
        # Check if user is the owner based on instance tags
        server_info = ec2_utils.list_server_by_id(instance_id)
        if server_info["TotalInstances"] > 0:
            instance = server_info['Instances'][0]
            tags = instance.get('Tags', [])
            
            for tag in tags:
                if tag['Key'] == 'Owner' and tag['Value'] == user_email:
                    return True, "instance_owner"
        
        # Not authorized
        return False, "unauthorized"

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