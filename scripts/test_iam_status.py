#!/usr/bin/env python3
import boto3
import sys
import os

def check_iam_status(instance_id, expected_profile_arn, region='us-west-2'):
    """Test IAM status check for an instance."""
    ec2_client = boto3.client('ec2', region_name=region)
    
    print(f"Checking IAM status for instance: {instance_id}")
    print(f"Expected profile ARN: {expected_profile_arn}\n")
    
    # Get IAM profile associations
    try:
        response = ec2_client.describe_iam_instance_profile_associations(
            Filters=[{'Name': 'instance-id', 'Values': [instance_id]}]
        )
        
        print(f"Raw response: {response}\n")
        
        associations = response.get('IamInstanceProfileAssociations', [])
        
        if not associations:
            print("❌ No IAM instance profile associations found")
            return 'fail'
        
        for assoc in associations:
            print(f"Association ID: {assoc['AssociationId']}")
            print(f"State: {assoc['State']}")
            print(f"Instance ID: {assoc['InstanceId']}")
            print(f"Profile ARN: {assoc['IamInstanceProfile']['Arn']}\n")
            
            if assoc['State'].lower() == 'associated' and assoc['InstanceId'] == instance_id:
                actual_arn = assoc['IamInstanceProfile']['Arn']
                if actual_arn == expected_profile_arn:
                    print(f"✅ IAM status: OK - Profile matches")
                    return 'ok'
                else:
                    print(f"❌ IAM status: FAIL - Profile mismatch")
                    print(f"   Expected: {expected_profile_arn}")
                    print(f"   Actual:   {actual_arn}")
                    return 'fail'
        
        print("❌ No associated profile found")
        return 'fail'
        
    except Exception as e:
        print(f"❌ Error checking IAM status: {e}")
        return 'fail'

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python3 test_iam_status.py <instance-id> <expected-profile-arn> [region]")
        sys.exit(1)
    
    instance_id = sys.argv[1]
    expected_arn = sys.argv[2]
    region = sys.argv[3] if len(sys.argv) > 3 else 'us-west-2'
    
    status = check_iam_status(instance_id, expected_arn, region)
    print(f"\nFinal IAM Status: {status}")
