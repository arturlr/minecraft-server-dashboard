import boto3
import logging
import os
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key, Attr

logger = logging.getLogger()
logger.setLevel(logging.INFO)

session = boto3.session.Session()
aws_region = session.region_name


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
                
