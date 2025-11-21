"""
Unit tests for error handling scenarios in ServerAction Lambda

Tests cover:
- Missing JWT token handling
- Invalid JWT token handling
- Missing instance ID handling
- Authorization failure handling
- SQS queue unavailable handling

Requirements: 1.5, 4.5
"""

import pytest
import json
import os
from unittest.mock import Mock, patch, MagicMock
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Mock the Lambda layer modules before importing index
sys.modules['authHelper'] = MagicMock()
sys.modules['ec2Helper'] = MagicMock()
sys.modules['utilHelper'] = MagicMock()

# Mock environment variables before importing the module
os.environ['TAG_APP_VALUE'] = 'test-app'
os.environ['EC2_INSTANCE_PROFILE_NAME'] = 'test-profile'
os.environ['EC2_INSTANCE_PROFILE_ARN'] = 'arn:aws:iam::123456789012:instance-profile/test-profile'
os.environ['COGNITO_USER_POOL_ID'] = 'us-east-1_test123'
os.environ['SERVER_ACTION_QUEUE_URL'] = 'https://sqs.us-east-1.amazonaws.com/123456789012/test-queue'

import index


class TestMissingJWTToken:
    """Test cases for missing JWT token scenarios"""
    
    @patch('index.utl')
    def test_missing_authorization_header(self, mock_utl):
        """Test that missing authorization header returns 401"""
        # Mock utl.response to return proper structure
        mock_utl.response.side_effect = lambda code, body: {
            'statusCode': code,
            'body': json.dumps(body)
        }
        
        event = {
            'request': {
                'headers': {}
            },
            'arguments': {
                'instanceId': 'i-1234567890abcdef0'
            },
            'info': {
                'fieldName': 'startServer'
            }
        }
        
        result = index.handler(event, None)
        
        assert result['statusCode'] == 401
        assert 'No Authorization header found' in json.dumps(result['body'])
    
    @patch('index.utl')
    def test_missing_headers_in_request(self, mock_utl):
        """Test that missing headers object returns 401"""
        # Mock utl.response to return proper structure
        mock_utl.response.side_effect = lambda code, body: {
            'statusCode': code,
            'body': json.dumps(body)
        }
        
        event = {
            'request': {},
            'arguments': {
                'instanceId': 'i-1234567890abcdef0'
            },
            'info': {
                'fieldName': 'startServer'
            }
        }
        
        result = index.handler(event, None)
        
        assert result['statusCode'] == 401
        assert 'No headers found in request' in json.dumps(result['body'])


class TestInvalidJWTToken:
    """Test cases for invalid JWT token scenarios"""
    
    @patch('index.utl')
    @patch('index.auth')
    def test_invalid_token_format(self, mock_auth, mock_utl):
        """Test that invalid token format returns 401"""
        # Mock utl.response to return proper structure
        mock_utl.response.side_effect = lambda code, body: {
            'statusCode': code,
            'body': json.dumps(body)
        }
        
        # Mock auth.process_token to raise exception for invalid token
        mock_auth.process_token.side_effect = Exception("Invalid token format")
        
        event = {
            'request': {
                'headers': {
                    'authorization': 'invalid-token-format'
                }
            },
            'arguments': {
                'instanceId': 'i-1234567890abcdef0'
            },
            'info': {
                'fieldName': 'startServer'
            }
        }
        
        result = index.handler(event, None)
        
        assert result['statusCode'] == 401
        assert 'Invalid token' in json.dumps(result['body'])
    
    @patch('index.utl')
    @patch('index.auth')
    def test_token_returns_none(self, mock_auth, mock_utl):
        """Test that token processing returning None returns 401"""
        # Mock utl.response to return proper structure
        mock_utl.response.side_effect = lambda code, body: {
            'statusCode': code,
            'body': json.dumps(body)
        }
        
        # Mock auth.process_token to return None (invalid claims)
        mock_auth.process_token.return_value = None
        
        event = {
            'request': {
                'headers': {
                    'authorization': 'Bearer invalid.jwt.token'
                }
            },
            'arguments': {
                'instanceId': 'i-1234567890abcdef0'
            },
            'info': {
                'fieldName': 'startServer'
            }
        }
        
        result = index.handler(event, None)
        
        assert result['statusCode'] == 401
        assert 'Invalid token' in json.dumps(result['body'])


class TestMissingInstanceID:
    """Test cases for missing instance ID scenarios"""
    
    @patch('index.utl')
    @patch('index.auth')
    def test_missing_instance_id_in_arguments(self, mock_auth, mock_utl):
        """Test that missing instanceId returns 400"""
        # Mock utl.response to return proper structure
        mock_utl.response.side_effect = lambda code, body: {
            'statusCode': code,
            'body': json.dumps(body)
        }
        
        mock_auth.process_token.return_value = {
            'email': 'test@example.com',
            'sub': 'user-123'
        }
        
        event = {
            'request': {
                'headers': {
                    'authorization': 'Bearer valid.jwt.token'
                }
            },
            'arguments': {
                'someOtherField': 'value'
            },
            'info': {
                'fieldName': 'startServer'
            },
            'identity': {
                'groups': []
            }
        }
        
        result = index.handler(event, None)
        
        assert result['statusCode'] == 400
        assert 'Instance id is not present in the event' in json.dumps(result['body'])
    
    @patch('index.utl')
    @patch('index.auth')
    def test_no_arguments_in_event(self, mock_auth, mock_utl):
        """Test that missing arguments object returns 400"""
        # Mock utl.response to return proper structure
        mock_utl.response.side_effect = lambda code, body: {
            'statusCode': code,
            'body': json.dumps(body)
        }
        
        mock_auth.process_token.return_value = {
            'email': 'test@example.com',
            'sub': 'user-123'
        }
        
        event = {
            'request': {
                'headers': {
                    'authorization': 'Bearer valid.jwt.token'
                }
            },
            'info': {
                'fieldName': 'startServer'
            },
            'identity': {
                'groups': []
            }
        }
        
        result = index.handler(event, None)
        
        assert result['statusCode'] == 400
        assert 'No arguments found in the event' in json.dumps(result['body'])


class TestAuthorizationFailure:
    """Test cases for authorization failure scenarios"""
    
    @patch('index.auth')
    @patch('index.utl')
    @patch('index.ec2_utils')
    def test_unauthorized_user(self, mock_ec2_utils, mock_utl, mock_auth):
        """Test that unauthorized user returns 401"""
        # Mock utl.response to return proper structure
        mock_utl.response.side_effect = lambda code, body: {
            'statusCode': code,
            'body': json.dumps(body)
        }
        
        mock_auth.process_token.return_value = {
            'email': 'unauthorized@example.com',
            'sub': 'user-456'
        }
        
        # Mock authorization check to return False
        mock_utl.check_user_authorization.return_value = (False, None)
        
        event = {
            'request': {
                'headers': {
                    'authorization': 'Bearer valid.jwt.token'
                }
            },
            'arguments': {
                'instanceId': 'i-1234567890abcdef0'
            },
            'info': {
                'fieldName': 'startServer'
            },
            'identity': {
                'groups': []
            }
        }
        
        result = index.handler(event, None)
        
        assert result['statusCode'] == 401
        assert 'User not authorized' in json.dumps(result['body'])
    
    @patch('index.auth')
    @patch('index.utl')
    @patch('index.ec2_utils')
    def test_authorization_check_exception(self, mock_ec2_utils, mock_utl, mock_auth):
        """Test that authorization check exception returns 500"""
        # Mock utl.response to return proper structure
        mock_utl.response.side_effect = lambda code, body: {
            'statusCode': code,
            'body': json.dumps(body)
        }
        
        mock_auth.process_token.return_value = {
            'email': 'test@example.com',
            'sub': 'user-123'
        }
        
        # Mock authorization check to raise exception
        mock_utl.check_user_authorization.side_effect = Exception("Authorization service unavailable")
        
        event = {
            'request': {
                'headers': {
                    'authorization': 'Bearer valid.jwt.token'
                }
            },
            'arguments': {
                'instanceId': 'i-1234567890abcdef0'
            },
            'info': {
                'fieldName': 'startServer'
            },
            'identity': {
                'groups': []
            }
        }
        
        result = index.handler(event, None)
        
        assert result['statusCode'] == 500
        assert 'Authorization check failed' in json.dumps(result['body'])


class TestSQSQueueUnavailable:
    """Test cases for SQS queue unavailable scenarios"""
    
    @patch('index.auth')
    @patch('index.utl')
    @patch('index.ec2_utils')
    @patch('index.sqs_client')
    def test_sqs_send_message_failure(self, mock_sqs, mock_ec2_utils, mock_utl, mock_auth):
        """Test that SQS send_message failure returns 500"""
        mock_auth.process_token.return_value = {
            'email': 'test@example.com',
            'sub': 'user-123'
        }
        
        # Mock authorization to succeed
        mock_utl.check_user_authorization.return_value = (True, "admin_group")
        mock_utl.response.side_effect = lambda code, body: {
            'statusCode': code,
            'body': json.dumps(body)
        }
        
        # Mock SQS to raise exception
        mock_sqs.send_message.side_effect = Exception("Queue unavailable")
        
        event = {
            'request': {
                'headers': {
                    'authorization': 'Bearer valid.jwt.token'
                }
            },
            'arguments': {
                'instanceId': 'i-1234567890abcdef0'
            },
            'info': {
                'fieldName': 'startServer'
            },
            'identity': {
                'groups': ['admin']
            }
        }
        
        result = index.handler(event, None)
        
        assert result['statusCode'] == 500
        assert 'Failed to queue action' in json.dumps(result['body'])
    
    @patch('index.server_action_queue_url', None)
    @patch('index.auth')
    @patch('index.utl')
    @patch('index.ec2_utils')
    def test_queue_url_not_configured(self, mock_ec2_utils, mock_utl, mock_auth):
        """Test that missing queue URL returns 500"""
        mock_auth.process_token.return_value = {
            'email': 'test@example.com',
            'sub': 'user-123'
        }
        
        # Mock authorization to succeed
        mock_utl.check_user_authorization.return_value = (True, "admin_group")
        mock_utl.response.side_effect = lambda code, body: {
            'statusCode': code,
            'body': json.dumps(body)
        }
        
        event = {
            'request': {
                'headers': {
                    'authorization': 'Bearer valid.jwt.token'
                }
            },
            'arguments': {
                'instanceId': 'i-1234567890abcdef0'
            },
            'info': {
                'fieldName': 'startServer'
            },
            'identity': {
                'groups': ['admin']
            }
        }
        
        result = index.handler(event, None)
        
        assert result['statusCode'] == 500
        assert 'Queue not configured' in json.dumps(result['body'])


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
