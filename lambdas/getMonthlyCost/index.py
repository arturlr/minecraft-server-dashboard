import boto3
import logging
import os
import json
import urllib.request
import time
from jose import jwk, jwt
from jose.utils import base64url_decode
from datetime import date, datetime, timezone, timedelta

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ce_client = boto3.client('ce')
cognito_idp = boto3.client('cognito-idp')
ENCODING = 'utf-8'

appValue = os.getenv('appValue')

def _is_token_valid(token, keys):
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

def getUsageCost(granularity,startDate,endDate,tagValue):
    try:
        usageQuantity = 0
        unblendedCost = 0
        request = {
                "TimePeriod": {
                    "Start": startDate,
                    "End": endDate
                },
                "Filter": {
                    "And": [
                        {
                            "Dimensions": {
                                "Key": "USAGE_TYPE_GROUP",
                                "Values": [
                                    "EC2: Running Hours"
                                ]
                            },
                            
                        },
                        {
                            "Tags": {
                                "Key": "App",
                                "Values": [ tagValue
                                ]
                            }
                        }
                    ]
                },
                "Granularity": granularity,
                "Metrics": [
                    "UnblendedCost",
                    "UsageQuantity"
                ]
            }
        response = ce_client.get_cost_and_usage(**request)

        if granularity == "MONTHLY":
            for results in response['ResultsByTime']:              
                unblendedCost = float(results['Total']['UnblendedCost']['Amount'])
                usageQuantity = float(results['Total']['UsageQuantity']['Amount'])

            return { "date": endDate, "unblendedCost": round(unblendedCost,1), "usageQuantity": round(usageQuantity,1) }

        else:
            usageDays = []
            for results in response['ResultsByTime']:
                usageDays.append({
                    "date": results['TimePeriod']['Start'],
                    "unblendedCost": float(results['Total']['UnblendedCost']['Amount']),
                    "usageQuantity": float(results['Total']['UsageQuantity']['Amount'])
                })
            return usageDays
                
    except Exception as e:
        logger.error(str(e))
        return { "unblendedCost": 0, "usageQuantity": 0 }

def handler(event, context):
    
    end_date = datetime.utcnow()
    last_day_of_prev_month = datetime.utcnow().replace(day=1,hour=23,minute=59,second=59) - timedelta(days=1)
    dt_1st_day_of_month_ago = datetime.utcnow().replace(day=1,hour=0,minute=0,second=0)

    if end_date.strftime("%Y-%m-%d") == dt_1st_day_of_month_ago.strftime("%Y-%m-%d"):
        start_date = last_day_of_prev_month
    else:
        start_date = dt_1st_day_of_month_ago


    # validate query type
    # validate jwt token

    if not 'identity' in event:
        logger.error("No Identity found")
        return "No Identity found"

    iss = event["identity"]["claims"]["iss"] 
    token = event["request"]["headers"]["authorization"] 
    keys_url = iss + '/.well-known/jwks.json'
    # download the key
    with urllib.request.urlopen(keys_url) as f:
        response = f.read()
    keys = json.loads(response.decode('utf-8'))['keys']

    token_claims = _is_token_valid(token,keys)

    if token_claims == None:
        logger.error("Invalid Token")
        return "Invalid Token"

    if 'cognito:username' in token_claims:
        userName=token_claims["cognito:username"]
    else:
        userName=token_claims["username"]

    # Get User Email from Cognito
    cog_user = cognito_idp.admin_get_user(
        UserPoolId=iss.split("/")[3],
        Username=userName
    )
    
    monthlyTotalUsage = getUsageCost("MONTHLY",start_date.strftime("%Y-%m-%d"),end_date.strftime("%Y-%m-%d"),appValue)

    return [{
            "id": monthlyTotalUsage['date'],
            "timePeriod": end_date.strftime("%b"),
            "UnblendedCost": monthlyTotalUsage['unblendedCost'],
            "UsageQuantity": monthlyTotalUsage['usageQuantity']
            }]
