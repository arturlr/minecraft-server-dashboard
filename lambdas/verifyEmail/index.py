import json
import boto3

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('Users')

def lambda_handler(event, context):

    email = event['arguments']['userEmail']
    
    response = table.get_item(Key={'email': email})

    if 'Item' in response:
        return True
    else:
        return False
