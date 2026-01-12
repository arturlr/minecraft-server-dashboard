#!/usr/bin/env python3
"""
Unit tests for UserMembership DynamoDB operations in ddbHelper.py
Tests CRUD operations for user membership records with role-based access control.
"""
from ddbHelper import UserMembershipDyn
import sys
import os
import unittest
from unittest.mock import Mock, patch, MagicMock
from botocore.exceptions import ClientError
from datetime import datetime, timezone
from hypothesis import given, strategies as st, settings

# Mock environment variables before importing
os.environ["USER_MEMBERSHIP_TABLE_NAME"] = "test-user-membership-table"

# Import after mocking environment
sys.path.insert(0, ".")


class TestUserMembershipDyn(unittest.TestCase):
    """Test suite for UserMembershipDyn class"""

    def setUp(self):
        """Set up test fixtures"""
        self.user_id = "cognito-sub-uuid-123"
        self.server_id = "i-1234567890abcdef0"
        self.email = "test@example.com"
        self.role = "admin"
        self.created_by = "admin@example.com"

        # Create mock DynamoDB table
        self.mock_table = Mock()

        # Patch boto3.resource to return mock table
        self.patcher = patch("boto3.resource")
        self.mock_boto_resource = self.patcher.start()

        mock_dynamodb = Mock()
        mock_dynamodb.Table.return_value = self.mock_table
        self.mock_boto_resource.return_value = mock_dynamodb

        # Create UserMembershipDyn instance
        self.membership_dyn = UserMembershipDyn()

    def tearDown(self):
        """Clean up after tests"""
        self.patcher.stop()

    def test_create_membership_success(self):
        """Test successful membership creation"""
        # Arrange
        self.mock_table.put_item.return_value = {}

        # Act
        result = self.membership_dyn.create_membership(
            self.user_id, self.server_id, self.email, self.role, self.created_by
        )

        # Assert
        self.mock_table.put_item.assert_called_once()
        call_args = self.mock_table.put_item.call_args
        item = call_args[1]["Item"]

        self.assertEqual(item["userId"], self.user_id)
        self.assertEqual(item["serverId"], self.server_id)
        self.assertEqual(item["email"], self.email)
        self.assertEqual(item["role"], self.role)
        self.assertEqual(item["createdBy"], self.created_by)
        self.assertIn("createdAt", item)
        self.assertIn("updatedAt", item)

        # Verify conditional expression to prevent duplicates
        self.assertIn("ConditionExpression", call_args[1])

        # Verify return value
        self.assertEqual(result["userId"], self.user_id)
        self.assertEqual(result["role"], self.role)

    def test_create_membership_duplicate_raises_error(self):
        """Test that creating duplicate membership raises ValueError"""
        # Arrange
        self.mock_table.put_item.side_effect = ClientError(
            {"Error": {"Code": "ConditionalCheckFailedException", "Message": "Item already exists"}}, "PutItem"
        )

        # Act & Assert
        with self.assertRaises(ValueError) as context:
            self.membership_dyn.create_membership(self.user_id, self.server_id, self.email, self.role, self.created_by)

        self.assertIn("already exists", str(context.exception))

    def test_create_membership_invalid_role_raises_error(self):
        """Test that invalid role raises ValueError"""
        # Act & Assert
        with self.assertRaises(ValueError) as context:
            self.membership_dyn.create_membership(
                self.user_id, self.server_id, self.email, "invalid_role", self.created_by
            )

        self.assertIn("Invalid role", str(context.exception))

    def test_create_membership_missing_fields_raises_error(self):
        """Test that missing required fields raise ValueError"""
        test_cases = [
            ("", self.server_id, self.email, self.role, self.created_by, "user_id"),
            (self.user_id, "", self.email, self.role, self.created_by, "server_id"),
            (self.user_id, self.server_id, "", self.role, self.created_by, "email"),
            (self.user_id, self.server_id, self.email, "", self.created_by, "role"),
            (self.user_id, self.server_id, self.email, self.role, "", "created_by"),
        ]

        for user_id, server_id, email, role, created_by, expected_field in test_cases:
            with self.subTest(missing_field=expected_field):
                with self.assertRaises(ValueError) as context:
                    self.membership_dyn.create_membership(user_id, server_id, email, role, created_by)

                self.assertIn("required", str(context.exception).lower())

    def test_get_membership_success(self):
        """Test successful membership retrieval"""
        # Arrange
        expected_item = {
            "userId": self.user_id,
            "serverId": self.server_id,
            "email": self.email,
            "role": self.role,
            "createdAt": "2024-01-08T10:30:00Z",
            "updatedAt": "2024-01-08T10:30:00Z",
            "createdBy": self.created_by,
        }
        self.mock_table.get_item.return_value = {"Item": expected_item}

        # Act
        result = self.membership_dyn.get_membership(self.user_id, self.server_id)

        # Assert
        self.mock_table.get_item.assert_called_once_with(Key={"userId": self.user_id, "serverId": self.server_id})
        self.assertEqual(result, expected_item)

    def test_get_membership_not_found_returns_none(self):
        """Test that non-existent membership returns None"""
        # Arrange
        self.mock_table.get_item.return_value = {}

        # Act
        result = self.membership_dyn.get_membership(self.user_id, self.server_id)

        # Assert
        self.assertIsNone(result)

    def test_update_membership_role_success(self):
        """Test successful role update"""
        # Arrange
        updated_item = {
            "userId": self.user_id,
            "serverId": self.server_id,
            "email": self.email,
            "role": "moderator",
            "createdAt": "2024-01-08T10:30:00Z",
            "updatedAt": "2024-01-08T11:00:00Z",
            "createdBy": self.created_by,
        }
        self.mock_table.update_item.return_value = {"Attributes": updated_item}

        # Act
        result = self.membership_dyn.update_membership(self.user_id, self.server_id, role="moderator")

        # Assert
        self.mock_table.update_item.assert_called_once()
        call_args = self.mock_table.update_item.call_args

        # Verify key
        self.assertEqual(call_args[1]["Key"], {"userId": self.user_id, "serverId": self.server_id})

        # Verify update expression includes role and updatedAt
        update_expr = call_args[1]["UpdateExpression"]
        self.assertIn("#role = :role", update_expr)
        self.assertIn("#updatedAt = :updatedAt", update_expr)

        # Verify conditional expression to ensure item exists
        self.assertIn("ConditionExpression", call_args[1])

        self.assertEqual(result, updated_item)

    def test_update_membership_email_success(self):
        """Test successful email update"""
        # Arrange
        new_email = "newemail@example.com"
        updated_item = {
            "userId": self.user_id,
            "serverId": self.server_id,
            "email": new_email,
            "role": self.role,
            "createdAt": "2024-01-08T10:30:00Z",
            "updatedAt": "2024-01-08T11:00:00Z",
            "createdBy": self.created_by,
        }
        self.mock_table.update_item.return_value = {"Attributes": updated_item}

        # Act
        result = self.membership_dyn.update_membership(self.user_id, self.server_id, email=new_email)

        # Assert
        call_args = self.mock_table.update_item.call_args
        update_expr = call_args[1]["UpdateExpression"]
        self.assertIn("#email = :email", update_expr)
        self.assertEqual(result["email"], new_email)

    def test_update_membership_not_found_raises_error(self):
        """Test that updating non-existent membership raises ValueError"""
        # Arrange
        self.mock_table.update_item.side_effect = ClientError(
            {"Error": {"Code": "ConditionalCheckFailedException", "Message": "Item not found"}}, "UpdateItem"
        )

        # Act & Assert
        with self.assertRaises(ValueError) as context:
            self.membership_dyn.update_membership(self.user_id, self.server_id, role="moderator")

        self.assertIn("not found", str(context.exception))

    def test_update_membership_no_fields_raises_error(self):
        """Test that update with no fields raises ValueError"""
        # Act & Assert
        with self.assertRaises(ValueError) as context:
            self.membership_dyn.update_membership(self.user_id, self.server_id)

        self.assertIn("At least one field", str(context.exception))

    def test_delete_membership_success(self):
        """Test successful membership deletion"""
        # Arrange
        deleted_item = {
            "userId": self.user_id,
            "serverId": self.server_id,
            "email": self.email,
            "role": self.role,
            "createdAt": "2024-01-08T10:30:00Z",
            "updatedAt": "2024-01-08T10:30:00Z",
            "createdBy": self.created_by,
        }
        self.mock_table.delete_item.return_value = {"Attributes": deleted_item}

        # Act
        result = self.membership_dyn.delete_membership(self.user_id, self.server_id)

        # Assert
        self.mock_table.delete_item.assert_called_once()
        call_args = self.mock_table.delete_item.call_args

        # Verify key
        self.assertEqual(call_args[1]["Key"], {"userId": self.user_id, "serverId": self.server_id})

        # Verify conditional expression to ensure item exists
        self.assertIn("ConditionExpression", call_args[1])

        # Verify return values setting
        self.assertEqual(call_args[1]["ReturnValues"], "ALL_OLD")

        self.assertEqual(result, deleted_item)

    def test_delete_membership_not_found_raises_error(self):
        """Test that deleting non-existent membership raises ValueError"""
        # Arrange
        self.mock_table.delete_item.side_effect = ClientError(
            {"Error": {"Code": "ConditionalCheckFailedException", "Message": "Item not found"}}, "DeleteItem"
        )

        # Act & Assert
        with self.assertRaises(ValueError) as context:
            self.membership_dyn.delete_membership(self.user_id, self.server_id)

        self.assertIn("not found", str(context.exception))

    def test_list_server_members_all_roles(self):
        """Test listing all members of a server"""
        # Arrange
        expected_members = [
            {"userId": "user1", "serverId": self.server_id, "role": "admin", "email": "user1@example.com"},
            {"userId": "user2", "serverId": self.server_id, "role": "moderator", "email": "user2@example.com"},
            {"userId": "user3", "serverId": self.server_id, "role": "viewer", "email": "user3@example.com"},
        ]
        self.mock_table.query.return_value = {"Items": expected_members}

        # Act
        result = self.membership_dyn.list_server_members(self.server_id)

        # Assert
        self.mock_table.query.assert_called_once()
        call_args = self.mock_table.query.call_args

        # Verify GSI usage
        self.assertEqual(call_args[1]["IndexName"], "ServerMembership-Index")

        # Verify key condition (server only, no role filter)
        key_condition = call_args[1]["KeyConditionExpression"]
        # This is a complex Key object, so we'll verify the query was called

        self.assertEqual(result, expected_members)

    def test_list_server_members_with_role_filter(self):
        """Test listing server members filtered by role"""
        # Arrange
        expected_members = [
            {"userId": "user1", "serverId": self.server_id, "role": "admin", "email": "user1@example.com"}
        ]
        self.mock_table.query.return_value = {"Items": expected_members}

        # Act
        result = self.membership_dyn.list_server_members(self.server_id, role_filter="admin")

        # Assert
        self.mock_table.query.assert_called_once()
        call_args = self.mock_table.query.call_args

        # Verify GSI usage
        self.assertEqual(call_args[1]["IndexName"], "ServerMembership-Index")

        self.assertEqual(result, expected_members)

    def test_list_server_members_invalid_role_filter_raises_error(self):
        """Test that invalid role filter raises ValueError"""
        # Act & Assert
        with self.assertRaises(ValueError) as context:
            self.membership_dyn.list_server_members(self.server_id, role_filter="invalid_role")

        self.assertIn("Invalid role", str(context.exception))

    def test_list_user_memberships_success(self):
        """Test listing all memberships for a user"""
        # Arrange
        expected_memberships = [
            {"userId": self.user_id, "serverId": "i-111", "role": "admin", "email": self.email},
            {"userId": self.user_id, "serverId": "i-222", "role": "moderator", "email": self.email},
        ]
        self.mock_table.query.return_value = {"Items": expected_memberships}

        # Act
        result = self.membership_dyn.list_user_memberships(self.user_id)

        # Assert
        self.mock_table.query.assert_called_once()
        call_args = self.mock_table.query.call_args

        # Verify primary key query (no IndexName should be specified)
        self.assertNotIn("IndexName", call_args[1])

        self.assertEqual(result, expected_memberships)

    def test_role_validation_accepts_valid_roles(self):
        """Test that all valid roles are accepted"""
        valid_roles = ["admin", "moderator", "viewer"]

        for role in valid_roles:
            with self.subTest(role=role):
                # Should not raise exception
                self.membership_dyn._validate_role(role)

    def test_role_validation_rejects_invalid_roles(self):
        """Test that invalid roles are rejected"""
        invalid_roles = ["superadmin", "guest", "owner", "", None, "ADMIN", "Admin"]

        for role in invalid_roles:
            with self.subTest(role=role):
                with self.assertRaises(ValueError):
                    self.membership_dyn._validate_role(role)

    def test_check_user_permission_success(self):
        """Test successful permission check"""
        # Arrange
        membership = {
            "userId": self.user_id,
            "serverId": self.server_id,
            "email": self.email,
            "role": "admin",
            "createdAt": "2024-01-08T10:30:00Z",
            "updatedAt": "2024-01-08T10:30:00Z",
            "createdBy": self.created_by,
        }
        self.mock_table.get_item.return_value = {"Item": membership}

        # Act
        is_authorized, user_role, auth_reason = self.membership_dyn.check_user_permission(
            self.user_id, self.server_id, "manage_users"
        )

        # Assert
        self.assertTrue(is_authorized)
        self.assertEqual(user_role, "admin")
        self.assertIn("sufficient permissions", auth_reason)

    def test_check_user_permission_insufficient_permissions(self):
        """Test permission check with insufficient permissions"""
        # Arrange
        membership = {
            "userId": self.user_id,
            "serverId": self.server_id,
            "email": self.email,
            "role": "viewer",
            "createdAt": "2024-01-08T10:30:00Z",
            "updatedAt": "2024-01-08T10:30:00Z",
            "createdBy": self.created_by,
        }
        self.mock_table.get_item.return_value = {"Item": membership}

        # Act
        is_authorized, user_role, auth_reason = self.membership_dyn.check_user_permission(
            self.user_id, self.server_id, "manage_users"
        )

        # Assert
        self.assertFalse(is_authorized)
        self.assertEqual(user_role, "viewer")
        self.assertIn("Insufficient permissions", auth_reason)
        self.assertIn("Required role: admin", auth_reason)

    def test_check_user_permission_no_membership(self):
        """Test permission check when user has no membership"""
        # Arrange
        self.mock_table.get_item.return_value = {}

        # Act
        is_authorized, user_role, auth_reason = self.membership_dyn.check_user_permission(
            self.user_id, self.server_id, "read_server"
        )

        # Assert
        self.assertFalse(is_authorized)
        self.assertIsNone(user_role)
        self.assertIn("does not have access", auth_reason)

    def test_check_user_permission_invalid_permission(self):
        """Test permission check with invalid permission"""
        # Act & Assert
        with self.assertRaises(ValueError) as context:
            self.membership_dyn.check_user_permission(self.user_id, self.server_id, "invalid_permission")

        self.assertIn("Invalid permission", str(context.exception))

    @given(
        user_id=st.text(
            min_size=1,
            max_size=100,
            alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd", "Pc"), whitelist_characters="-_"),
        ),
        server_id=st.text(min_size=12, max_size=19, alphabet="abcdef0123456789").map(lambda x: f"i-{x}"),
        email=st.emails(),
        role=st.sampled_from(["admin", "moderator", "viewer"]),
        created_by=st.emails(),
    )
    @settings(max_examples=100)
    def test_property_membership_data_integrity(self, user_id, server_id, email, role, created_by):
        """
        Property 1: Membership data integrity
        For any membership creation operation, all required fields (userId, serverId, email, role)
        should be properly stored and retrievable from DynamoDB.

        Feature: user-membership-migration, Property 1: Membership data integrity
        Validates: Requirements 1.2
        """
        # Reset mocks for each iteration
        self.mock_table.reset_mock()

        # Arrange - Mock successful DynamoDB operations
        expected_membership = {
            "userId": user_id,
            "serverId": server_id,
            "email": email,
            "role": role,
            "createdAt": "2024-01-08T10:30:00Z",
            "updatedAt": "2024-01-08T10:30:00Z",
            "createdBy": created_by,
        }

        # Mock put_item for creation
        self.mock_table.put_item.return_value = {}

        # Mock get_item for retrieval
        self.mock_table.get_item.return_value = {"Item": expected_membership}

        # Act - Create membership
        created_membership = self.membership_dyn.create_membership(user_id, server_id, email, role, created_by)

        # Verify creation call was made with correct data
        self.mock_table.put_item.assert_called_once()
        put_call_args = self.mock_table.put_item.call_args
        created_item = put_call_args[1]["Item"]

        # Assert all required fields are present in created item
        self.assertEqual(created_item["userId"], user_id)
        self.assertEqual(created_item["serverId"], server_id)
        self.assertEqual(created_item["email"], email)
        self.assertEqual(created_item["role"], role)
        self.assertEqual(created_item["createdBy"], created_by)
        self.assertIn("createdAt", created_item)
        self.assertIn("updatedAt", created_item)

        # Act - Retrieve membership
        retrieved_membership = self.membership_dyn.get_membership(user_id, server_id)

        # Verify retrieval call was made with correct key
        self.mock_table.get_item.assert_called_once_with(Key={"userId": user_id, "serverId": server_id})

        # Assert all required fields are present and correct in retrieved item
        self.assertEqual(retrieved_membership["userId"], user_id)
        self.assertEqual(retrieved_membership["serverId"], server_id)
        self.assertEqual(retrieved_membership["email"], email)
        self.assertEqual(retrieved_membership["role"], role)
        self.assertEqual(retrieved_membership["createdBy"], created_by)
        self.assertIn("createdAt", retrieved_membership)
        self.assertIn("updatedAt", retrieved_membership)

        # Assert that created and retrieved data match for all required fields
        for field in ["userId", "serverId", "email", "role", "createdBy"]:
            self.assertEqual(created_membership[field], retrieved_membership[field])

    @given(
        user_id=st.text(
            min_size=1,
            max_size=100,
            alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd", "Pc"), whitelist_characters="-_"),
        ),
        server_id=st.text(min_size=12, max_size=19, alphabet="abcdef0123456789").map(lambda x: f"i-{x}"),
        email=st.emails(),
        role=st.sampled_from(["admin", "moderator", "viewer"]),
        created_by=st.emails(),
    )
    @settings(max_examples=100)
    def test_property_membership_removal_consistency(self, user_id, server_id, email, role, created_by):
        """
        Property 3: Membership removal consistency
        For any user removal operation, the corresponding DynamoDB membership record
        should no longer exist after the operation completes.

        Feature: user-membership-migration, Property 3: Membership removal consistency
        Validates: Requirements 1.4
        """
        # Reset mocks for each iteration
        self.mock_table.reset_mock()

        # Arrange - Mock existing membership for deletion
        existing_membership = {
            "userId": user_id,
            "serverId": server_id,
            "email": email,
            "role": role,
            "createdAt": "2024-01-08T10:30:00Z",
            "updatedAt": "2024-01-08T10:30:00Z",
            "createdBy": created_by,
        }

        # Mock successful deletion - returns the deleted item
        self.mock_table.delete_item.return_value = {"Attributes": existing_membership}

        # Mock get_item to return None after deletion (membership no longer exists)
        self.mock_table.get_item.return_value = {}

        # Act - Delete the membership
        deleted_membership = self.membership_dyn.delete_membership(user_id, server_id)

        # Verify deletion call was made with correct parameters
        self.mock_table.delete_item.assert_called_once()
        delete_call_args = self.mock_table.delete_item.call_args

        # Assert deletion was called with correct key
        expected_key = {"userId": user_id, "serverId": server_id}
        self.assertEqual(delete_call_args[1]["Key"], expected_key)

        # Assert conditional expression ensures item exists before deletion
        self.assertIn("ConditionExpression", delete_call_args[1])

        # Assert return values setting to get deleted item
        self.assertEqual(delete_call_args[1]["ReturnValues"], "ALL_OLD")

        # Assert deleted membership contains the expected data
        self.assertEqual(deleted_membership["userId"], user_id)
        self.assertEqual(deleted_membership["serverId"], server_id)
        self.assertEqual(deleted_membership["email"], email)
        self.assertEqual(deleted_membership["role"], role)
        self.assertEqual(deleted_membership["createdBy"], created_by)

        # Act - Attempt to retrieve the membership after deletion
        retrieved_membership = self.membership_dyn.get_membership(user_id, server_id)

        # Verify get_item was called with correct key
        self.mock_table.get_item.assert_called_once_with(Key={"userId": user_id, "serverId": server_id})

        # Assert - The membership should no longer exist (consistency check)
        self.assertIsNone(
            retrieved_membership, f"Membership should not exist after deletion: user={user_id}, server={server_id}"
        )


if __name__ == "__main__":
    unittest.main()
