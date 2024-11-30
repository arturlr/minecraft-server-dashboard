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
        logger.info("------- Ec2Utils Class Initialization")
        self.ssm = boto3.client('ssm')        
    
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