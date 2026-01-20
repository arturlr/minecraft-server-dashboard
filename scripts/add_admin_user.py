#!/usr/bin/env python3
import boto3
import sys
import argparse

def get_user_by_email(user_pool_id, email, region='us-west-2'):
    """Query Cognito user pool for user by email."""
    cognito = boto3.client('cognito-idp', region_name=region)
    
    try:
        response = cognito.list_users(
            UserPoolId=user_pool_id,
            Filter=f'email = "{email}"'
        )
        
        if not response['Users']:
            print(f"No user found with email: {email}")
            return None
        
        user = response['Users'][0]
        user_sub = next((attr['Value'] for attr in user['Attributes'] if attr['Name'] == 'sub'), None)
        
        if not user_sub:
            print("User found but missing 'sub' attribute")
            return None
        
        return user_sub
    
    except Exception as e:
        print(f"Error querying Cognito: {e}")
        return None

def add_admin_to_dynamodb(table_name, user_sub, region='us-west-2'):
    """Add admin role to user in DynamoDB CoreTable."""
    dynamodb = boto3.resource('dynamodb', region_name=region)
    table = dynamodb.Table(table_name)
    
    try:
        table.put_item(
            Item={
                'PK': f'USER#{user_sub}',
                'SK': 'ADMIN',
                'Type': 'UserRole',
                'role': 'admin'
            }
        )
        print(f"Successfully added admin role for user: {user_sub}")
        return True
    
    except Exception as e:
        print(f"Error writing to DynamoDB: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Add admin user to DynamoDB CoreTable')
    parser.add_argument('email', help='Email address of the user')
    parser.add_argument('--user-pool-id', required=True, help='Cognito User Pool ID')
    parser.add_argument('--table-name', required=True, help='DynamoDB CoreTable name')
    parser.add_argument('--region', default='us-west-2', help='AWS region (default: us-west-2)')
    
    args = parser.parse_args()
    
    print(f"Searching for user with email: {args.email}")
    user_sub = get_user_by_email(args.user_pool_id, args.email, args.region)
    
    if not user_sub:
        sys.exit(1)
    
    print(f"Found user with sub: {user_sub}")
    
    if add_admin_to_dynamodb(args.table_name, user_sub, args.region):
        print("Admin user added successfully!")
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == '__main__':
    main()
