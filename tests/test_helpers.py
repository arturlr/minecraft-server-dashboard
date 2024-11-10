import pytest
import sys
import os
# Add the path to the directory containing the helpers module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'layers', 'helpers')))
from helpers import Utils
from unittest.mock import patch, MagicMock

@pytest.fixture
def mock_boto3_client():
    with patch('boto3.client') as mock_client:
        yield mock_client

@pytest.fixture
def utils(mock_boto3_client):
    return Utils()

def test_capitalize_first_letter(utils):
    assert utils.capitalize_first_letter('hello') == 'Hello'
    assert utils.capitalize_first_letter('world') == 'World'
    assert utils.capitalize_first_letter('') == ''

def test_response(utils):
    assert utils.response(200, 'Success') == {
        'statusCode': 200,
        'body': 'Success',
        'headers': {
            'Content-Type': 'application/json'
        }
    }

def test_get_ssm_parameter(utils, mock_boto3_client):
    # Mock the SSM client
    mock_ssm = MagicMock()
    utils.ssm_client = mock_boto3_client.return_value = mock_ssm

    # Mock the get_parameter method
    mock_ssm.get_parameter.return_value = {
        'Parameter': {
            'Value': 'value'
        }
    }

    result = utils.get_ssm_parameter('parameter_name')

    assert result == 'value'
    mock_ssm.get_parameter.assert_called_once_with(
        Name='parameter_name',
        WithDecryption=True
    )

def test_get_instance_attributes(utils, mock_boto3_client):
    # Mock the EC2 client
    mock_ec2 = MagicMock()
    utils.ec2_client = mock_boto3_client.return_value = mock_ec2

    # Mock the describe_tags method
    mock_ec2.describe_tags.return_value = {
        'Tags': [
            {'Key': 'AlarmMetric', 'Value': 'CPU'},
            {'Key': 'AlarmThreshold', 'Value': '80'},
            {'Key': 'AlarmEvaluationPeriod', 'Value': '5'},
            {'Key': 'RunCommand', 'Value': 'start.sh'},
            {'Key': 'WorkDir', 'Value': '/home/ec2-user'}
        ]
    }

    result = utils.get_instance_attributes('i-1234567890abcdef0')

    assert result == {
        'id': 'i-1234567890abcdef0',
        'alarmType': 'CPU',
        'alarmThreshold': '80',
        'alarmEvaluationPeriod': '5',
        'runCommand': 'start.sh',
        'workDir': '/home/ec2-user',
        'groupMembers': ''
    }

    mock_ec2.describe_tags.assert_called_once_with(
        Filters=[{'Name': 'resource-id', 'Values': ['i-1234567890abcdef0']}]
    )