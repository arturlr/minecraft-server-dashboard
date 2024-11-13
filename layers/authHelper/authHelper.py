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
            
    def add_user_to_group(self,instance_id,userName):
            try:                
                userRsp = self.cognito_idp.admin_add_user_to_group(
                    UserPoolId=self.cognito_pool_id,
                    Username=userName,
                    GroupName=instance_id
                )

                logger.info("User added to the group")
                return True
        
            except Exception as e:
                logger.warning(str(e))
                return False
            
    def list_users_for_group(self, instance_id):
        try:
            groupMembers = []
            pagination_token = None

            while True:
                if pagination_token:
                    response = self.cognito_idp.list_users_in_group(
                        UserPoolId=self.cognito_pool_id,
                        GroupName=instance_id,
                        NextToken=pagination_token
                    )
                else:
                    groupMembers.extend([
                        {
                            "id": user_attrs.get("sub"),
                            "email": user_attrs.get("email"),
                            "fullname": f"{user_attrs.get('given_name')} {user_attrs.get('family_name')}"
                        }
                        for user in response["Users"]
                        if (user_attrs := {attr["Name"]: attr["Value"] for attr in user["Attributes"]})
                    ])

                    pagination_token = response.get('NextToken')
                    if not pagination_token:
                        break

            return groupMembers

        except Exception as e:
            logger.info("Exception list_users_in_group")
            logger.warning(str(e))
            return []
      
    def list_groups_for_user(self, username):
        groups = []
        next_token = None

        while True:
            if next_token:
                response = self.cognito_idp.admin_list_groups_for_user(
                    Username=username,
                    UserPoolId=self.cognito_pool_id,
                    NextToken=next_token
                )
            else:
                response = self.cognito_idp.admin_list_groups_for_user(
                    Username=username,
                    UserPoolId=self.cognito_pool_id
                )

            # extract the group names from the response
            groups.extend([group['GroupName'] for group in response.get('Groups', [])])

            next_token = response.get('NextToken')
            if not next_token:
                break

        return groups
        
