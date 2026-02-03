#!/usr/bin/env python3
"""
Add a user as a global admin in DynamoDB CoreTable.
Usage: python add_admin.py <user_email> --user-pool-id <pool_id> [--table-name TABLE_NAME] [--profile PROFILE]
"""

import argparse
import boto3
import sys

def add_admin(user_email, table_name, user_pool_id, profile=None):
    """Add user as global admin in CoreTable."""
    session = boto3.Session(profile_name=profile) if profile else boto3.Session()
    cognito = session.client('cognito-idp')
    dynamodb = session.resource('dynamodb')
    table = dynamodb.Table(table_name)
    
    try:
        # Look up username by email
        users = cognito.list_users(
            UserPoolId=user_pool_id,
            Filter=f'email = "{user_email}"'
        )
        
        if not users['Users']:
            print(f"✗ No user found with email {user_email}", file=sys.stderr)
            return False
        
        username = users['Users'][0]['Username']
        
        # Get user's Cognito sub
        response = cognito.admin_get_user(
            UserPoolId=user_pool_id,
            Username=username
        )
        
        user_sub = None
        for attr in response['UserAttributes']:
            if attr['Name'] == 'sub':
                user_sub = attr['Value']
                break
        
        if not user_sub:
            print(f"✗ Could not find Cognito sub for {user_email}", file=sys.stderr)
            return False
        
        table.put_item(
            Item={
                'PK': f'USER#{user_sub}',
                'SK': 'ADMIN',
                'email': user_email,
                'role': 'admin'
            }
        )
        print(f"✓ Added {user_email} (sub: {user_sub}) as admin")
        return True
    except Exception as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        return False

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Add user as global admin')
    parser.add_argument('email', help='User email address')
    parser.add_argument('--table-name', default='msd-dev-CoreTable', help='DynamoDB table name')
    parser.add_argument('--user-pool-id', required=True, help='Cognito User Pool ID')
    parser.add_argument('--profile', help='AWS profile name')
    
    args = parser.parse_args()
    
    success = add_admin(args.email, args.table_name, args.user_pool_id, args.profile)
    sys.exit(0 if success else 1)
