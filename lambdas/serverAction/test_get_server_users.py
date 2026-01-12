#!/usr/bin/env python3
"""
Unit tests for getServerUsers functionality in serverAction Lambda
Tests the updated resolver that queries DynamoDB membership table instead of Cognito groups
"""
from index import handle_get_server_users
import sys
import os
import unittest
from unittest.mock import Mock, patch

# Mock environment variables before importing
os.environ["COGNITO_USER_POOL_ID"] = "test-pool-id"
os.environ["USER_MEMBERSHIP_TABLE_NAME"] = "test-user-membership-table"

# Mock the imports that would normally come from Lambda layers
sys.modules["authHelper"] = Mock()
sys.modules["ec2Helper"] = Mock()
sys.modules["utilHelper"] = Mock()
sys.modules["ddbHelper"] = Mock()

# Add the lambda directory to the path
sys.path.insert(0, ".")
sys.path.insert(0, "../..")

# Import the function we want to test


class TestGetServerUsers(unittest.TestCase):
    """Test suite for getServerUsers functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.instance_id = "i-1234567890abcdef0"

        # Mock membership data
        self.mock_members = [
            {
                "userId": "cognito-sub-admin-123",
                "serverId": self.instance_id,
                "email": "admin@example.com",
                "role": "admin",
                "createdAt": "2024-01-08T10:30:00Z",
                "updatedAt": "2024-01-08T10:30:00Z",
                "createdBy": "system@example.com",
            },
            {
                "userId": "cognito-sub-moderator-456",
                "serverId": self.instance_id,
                "email": "moderator@example.com",
                "role": "moderator",
                "createdAt": "2024-01-08T10:30:00Z",
                "updatedAt": "2024-01-08T10:30:00Z",
                "createdBy": "admin@example.com",
            },
            {
                "userId": "cognito-sub-viewer-789",
                "serverId": self.instance_id,
                "email": "viewer@example.com",
                "role": "viewer",
                "createdAt": "2024-01-08T10:30:00Z",
                "updatedAt": "2024-01-08T10:30:00Z",
                "createdBy": "admin@example.com",
            },
        ]

        # Mock Cognito user data
        self.mock_cognito_users = {
            "cognito-sub-admin-123": {
                "username": "admin-user",
                "email": "admin@example.com",
                "fullName": "Admin User",
                "sub": "cognito-sub-admin-123",
            },
            "cognito-sub-moderator-456": {
                "username": "moderator-user",
                "email": "moderator@example.com",
                "fullName": "Moderator User",
                "sub": "cognito-sub-moderator-456",
            },
            "cognito-sub-viewer-789": {
                "username": "viewer-user",
                "email": "viewer@example.com",
                "fullName": "Viewer User",
                "sub": "cognito-sub-viewer-789",
            },
        }

    @patch("index.auth")
    def test_get_server_users_success_with_cognito_data(self, mock_auth):
        """Test successful retrieval of server users with Cognito user data"""
        # Arrange
        with patch("builtins.__import__") as mock_import:
            # Mock the dynamic import of UserMembershipDyn
            mock_ddb_helper = Mock()
            mock_membership_class = Mock()
            mock_ddb_helper.UserMembershipDyn = mock_membership_class

            def side_effect(name, *args, **kwargs):
                if name == "ddbHelper":
                    return mock_ddb_helper
                return Mock()

            mock_import.side_effect = side_effect

            # Mock UserMembershipDyn instance
            mock_membership_dyn = Mock()
            mock_membership_class.return_value = mock_membership_dyn
            mock_membership_dyn.list_server_members.return_value = self.mock_members

            # Mock auth.get_user_by_sub to return user details
            def mock_get_user_by_sub(user_sub):
                return self.mock_cognito_users.get(user_sub)

            mock_auth.get_user_by_sub.side_effect = mock_get_user_by_sub

            # Act
            result = handle_get_server_users(self.instance_id)

            # Assert
            self.assertIsInstance(result, list)
            self.assertEqual(len(result), 3)

            # Verify membership query was called correctly
            mock_membership_dyn.list_server_members.assert_called_once_with(self.instance_id)

            # Verify Cognito queries were made for each user
            self.assertEqual(mock_auth.get_user_by_sub.call_count, 3)

            # Verify the structure and content of returned data
            expected_users = [
                {
                    "id": "cognito-sub-admin-123",
                    "email": "admin@example.com",
                    "fullName": "Admin User",
                    "role": "admin",
                },
                {
                    "id": "cognito-sub-moderator-456",
                    "email": "moderator@example.com",
                    "fullName": "Moderator User",
                    "role": "moderator",
                },
                {
                    "id": "cognito-sub-viewer-789",
                    "email": "viewer@example.com",
                    "fullName": "Viewer User",
                    "role": "viewer",
                },
            ]

            # Sort both lists by id for consistent comparison
            result_sorted = sorted(result, key=lambda x: x["id"])
            expected_sorted = sorted(expected_users, key=lambda x: x["id"])

            self.assertEqual(result_sorted, expected_sorted)

    @patch("index.auth")
    def test_get_server_users_cognito_fallback(self, mock_auth):
        """Test that email is used as fallback when Cognito user data is unavailable"""
        # Arrange
        with patch("builtins.__import__") as mock_import:
            # Mock the dynamic import of UserMembershipDyn
            mock_ddb_helper = Mock()
            mock_membership_class = Mock()
            mock_ddb_helper.UserMembershipDyn = mock_membership_class

            def side_effect(name, *args, **kwargs):
                if name == "ddbHelper":
                    return mock_ddb_helper
                return Mock()

            mock_import.side_effect = side_effect

            # Mock UserMembershipDyn instance
            mock_membership_dyn = Mock()
            mock_membership_class.return_value = mock_membership_dyn
            mock_membership_dyn.list_server_members.return_value = [self.mock_members[0]]  # Only one user

            # Mock auth.get_user_by_sub to raise exception (simulating Cognito unavailable)
            mock_auth.get_user_by_sub.side_effect = Exception("Cognito unavailable")

            # Act
            result = handle_get_server_users(self.instance_id)

            # Assert
            self.assertIsInstance(result, list)
            self.assertEqual(len(result), 1)

            # Verify fallback behavior - email used as fullName
            user = result[0]
            self.assertEqual(user["id"], "cognito-sub-admin-123")
            self.assertEqual(user["email"], "admin@example.com")
            self.assertEqual(user["fullName"], "admin@example.com")  # Email used as fallback
            self.assertEqual(user["role"], "admin")

    def test_get_server_users_empty_membership_list(self):
        """Test graceful handling of empty membership lists"""
        # Arrange
        with patch("builtins.__import__") as mock_import:
            # Mock the dynamic import of UserMembershipDyn
            mock_ddb_helper = Mock()
            mock_membership_class = Mock()
            mock_ddb_helper.UserMembershipDyn = mock_membership_class

            def side_effect(name, *args, **kwargs):
                if name == "ddbHelper":
                    return mock_ddb_helper
                return Mock()

            mock_import.side_effect = side_effect

            # Mock UserMembershipDyn instance
            mock_membership_dyn = Mock()
            mock_membership_class.return_value = mock_membership_dyn
            mock_membership_dyn.list_server_members.return_value = []  # Empty list

            # Act
            result = handle_get_server_users(self.instance_id)

            # Assert
            self.assertIsInstance(result, list)
            self.assertEqual(len(result), 0)

            # Verify membership query was called
            mock_membership_dyn.list_server_members.assert_called_once_with(self.instance_id)

    @patch("index.utl")
    def test_get_server_users_dynamodb_error(self, mock_utl):
        """Test error handling when DynamoDB operation fails"""
        # Arrange
        with patch("builtins.__import__") as mock_import:
            # Mock the dynamic import of UserMembershipDyn to raise exception
            def side_effect(name, *args, **kwargs):
                if name == "ddbHelper":
                    raise Exception("DynamoDB error")
                return Mock()

            mock_import.side_effect = side_effect

            # Mock utl.response to return error response
            mock_utl.response.return_value = {
                "statusCode": 500,
                "body": {"error": "Failed to retrieve users: DynamoDB error"},
            }

            # Act
            result = handle_get_server_users(self.instance_id)

            # Assert
            mock_utl.response.assert_called_once_with(500, {"error": "Failed to retrieve users: DynamoDB error"})
            self.assertEqual(result["statusCode"], 500)

    @patch("index.auth")
    def test_get_server_users_includes_role_information(self, mock_auth):
        """Test that role information is included in responses (Requirements 5.4)"""
        # Arrange
        with patch("builtins.__import__") as mock_import:
            # Mock the dynamic import of UserMembershipDyn
            mock_ddb_helper = Mock()
            mock_membership_class = Mock()
            mock_ddb_helper.UserMembershipDyn = mock_membership_class

            def side_effect(name, *args, **kwargs):
                if name == "ddbHelper":
                    return mock_ddb_helper
                return Mock()

            mock_import.side_effect = side_effect

            # Mock UserMembershipDyn instance
            mock_membership_dyn = Mock()
            mock_membership_class.return_value = mock_membership_dyn
            mock_membership_dyn.list_server_members.return_value = self.mock_members

            # Mock auth.get_user_by_sub to return user details
            def mock_get_user_by_sub(user_sub):
                return self.mock_cognito_users.get(user_sub)

            mock_auth.get_user_by_sub.side_effect = mock_get_user_by_sub

            # Act
            result = handle_get_server_users(self.instance_id)

            # Assert
            self.assertIsInstance(result, list)
            self.assertEqual(len(result), 3)

            # Verify each user has role information
            for user in result:
                self.assertIn("role", user)
                self.assertIn(user["role"], ["admin", "moderator", "viewer"])

            # Verify specific roles are correct
            roles_by_id = {user["id"]: user["role"] for user in result}
            self.assertEqual(roles_by_id["cognito-sub-admin-123"], "admin")
            self.assertEqual(roles_by_id["cognito-sub-moderator-456"], "moderator")
            self.assertEqual(roles_by_id["cognito-sub-viewer-789"], "viewer")


if __name__ == "__main__":
    unittest.main()
