"""
Centralized error handling and logging utilities for the user membership migration system.
Provides consistent error messages, logging patterns, and error response formatting.
"""

import logging
import traceback
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timezone

logger = logging.getLogger()


class ErrorHandler:
    """
    Centralized error handling for membership operations and authorization checks.
    Provides consistent error messages and logging patterns across all Lambda functions.
    """

    # Standard error message templates
    ERROR_MESSAGES = {
        # DynamoDB operation errors
        "MEMBERSHIP_ALREADY_EXISTS": "User membership already exists for this server",
        "MEMBERSHIP_NOT_FOUND": "User membership not found for server {server_id}",
        "USER_NOT_FOUND": "No user found with email {email}. The user must log in to the dashboard at least once before they can be added to a server.",
        "SERVER_NOT_FOUND": "Server {server_id} not found or you do not have access",
        "DYNAMODB_UNAVAILABLE": "Database temporarily unavailable. Please try again",
        "INVALID_ROLE": 'Invalid role "{role}". Must be one of: admin, moderator, viewer',
        "REQUIRED_FIELD_MISSING": 'Required field "{field}" is missing or empty',
        # Authorization errors
        "INSUFFICIENT_PERMISSIONS": "Insufficient permissions. Required role: {required_role}, your role: {user_role}",
        "NO_SERVER_ACCESS": "You do not have access to server {server_id}",
        "AUTHORIZATION_FAILED": "Authorization check failed: {reason}",
        "SELF_ADMIN_ROLE_PROTECTION": "Cannot modify your own admin role to prevent lockout",
        "LAST_ADMIN_PROTECTION": "Cannot remove yourself as the only admin to prevent lockout",
        # Migration errors
        "MIGRATION_FAILED": "Migration failed: {reason}",
        "MIGRATION_VERIFICATION_FAILED": "Migration verification failed. Manual review required",
        "COGNITO_ACCESS_ERROR": "Unable to access Cognito groups during migration",
        "PARTIAL_MIGRATION": "Migration completed with errors. See migration report for details",
        # General errors
        "INTERNAL_ERROR": "An unexpected error occurred: {error}",
        "VALIDATION_ERROR": "Validation error: {error}",
        "CONFIGURATION_ERROR": "Configuration error: {error}",
        "NETWORK_ERROR": "Network error: {error}",
        "TIMEOUT_ERROR": "Operation timed out: {error}",
    }

    # Error categories for logging levels
    ERROR_CATEGORIES = {
        "CRITICAL": ["MIGRATION_FAILED", "DYNAMODB_UNAVAILABLE", "CONFIGURATION_ERROR"],
        "ERROR": ["MEMBERSHIP_NOT_FOUND", "USER_NOT_FOUND", "SERVER_NOT_FOUND", "AUTHORIZATION_FAILED"],
        "WARNING": ["INSUFFICIENT_PERMISSIONS", "INVALID_ROLE", "MEMBERSHIP_ALREADY_EXISTS"],
        "INFO": ["SELF_ADMIN_ROLE_PROTECTION", "LAST_ADMIN_PROTECTION"],
    }

    @classmethod
    def get_error_message(cls, error_code: str, **kwargs) -> str:
        """
        Get formatted error message for a given error code.

        Args:
            error_code: Error code from ERROR_MESSAGES
            **kwargs: Format parameters for the error message

        Returns:
            Formatted error message string
        """
        template = cls.ERROR_MESSAGES.get(error_code, "Unknown error: {error_code}")
        try:
            return template.format(error_code=error_code, **kwargs)
        except KeyError as e:
            logger.warning(f"Missing format parameter for error {error_code}: {e}")
            return f"{template} (formatting error: missing {e})"

    @classmethod
    def log_error(cls, error_code: str, context: Dict[str, Any] = None, exception: Exception = None, **kwargs):
        """
        Log error with appropriate level and consistent format.

        Args:
            error_code: Error code from ERROR_MESSAGES
            context: Additional context information
            exception: Exception object if available
            **kwargs: Format parameters for the error message
        """
        message = cls.get_error_message(error_code, **kwargs)

        # Determine log level based on error category
        log_level = "ERROR"  # Default
        for level, codes in cls.ERROR_CATEGORIES.items():
            if error_code in codes:
                log_level = level
                break

        # Build log entry
        log_data = {"error_code": error_code, "message": message, "timestamp": datetime.now(timezone.utc).isoformat()}

        if context:
            log_data["context"] = context

        if exception:
            log_data["exception"] = str(exception)
            log_data["traceback"] = traceback.format_exc()

        # Log with appropriate level
        if log_level == "CRITICAL":
            logger.critical(f"CRITICAL ERROR: {message}", extra=log_data)
        elif log_level == "ERROR":
            logger.error(f"ERROR: {message}", extra=log_data)
        elif log_level == "WARNING":
            logger.warning(f"WARNING: {message}", extra=log_data)
        else:
            logger.info(f"INFO: {message}", extra=log_data)

    @classmethod
    def create_error_response(cls, status_code: int, error_code: str, **kwargs) -> Dict[str, Any]:
        """
        Create standardized error response for Lambda functions.

        Args:
            status_code: HTTP status code
            error_code: Error code from ERROR_MESSAGES
            **kwargs: Format parameters for the error message

        Returns:
            Dictionary with statusCode, body containing error information
        """
        message = cls.get_error_message(error_code, **kwargs)

        return {
            "statusCode": status_code,
            "body": {"error": error_code, "message": message, "timestamp": datetime.now(timezone.utc).isoformat()},
        }

    @classmethod
    def handle_dynamodb_error(
        cls, error: Exception, operation: str, context: Dict[str, Any] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Handle DynamoDB-specific errors with appropriate error codes and logging.

        Args:
            error: DynamoDB ClientError or other exception
            operation: Description of the operation that failed
            context: Additional context information

        Returns:
            Tuple of (error_code, error_response_dict)
        """
        from botocore.exceptions import ClientError

        if isinstance(error, ClientError):
            error_code_aws = error.response["Error"]["Code"]
            error_message = error.response["Error"]["Message"]

            # Map AWS error codes to our standard error codes
            error_mapping = {
                "ConditionalCheckFailedException": "MEMBERSHIP_ALREADY_EXISTS",
                "ResourceNotFoundException": "MEMBERSHIP_NOT_FOUND",
                "ValidationException": "VALIDATION_ERROR",
                "ProvisionedThroughputExceededException": "DYNAMODB_UNAVAILABLE",
                "ItemCollectionSizeLimitExceededException": "VALIDATION_ERROR",
            }

            error_code = error_mapping.get(error_code_aws, "INTERNAL_ERROR")

            # Log the error with context
            log_context = {"operation": operation, "aws_error_code": error_code_aws, "aws_error_message": error_message}
            if context:
                log_context.update(context)

            cls.log_error(error_code, context=log_context, exception=error, error=str(error))

            # Determine appropriate HTTP status code
            status_codes = {
                "MEMBERSHIP_ALREADY_EXISTS": 409,
                "MEMBERSHIP_NOT_FOUND": 404,
                "VALIDATION_ERROR": 400,
                "DYNAMODB_UNAVAILABLE": 503,
                "INTERNAL_ERROR": 500,
            }

            status_code = status_codes.get(error_code, 500)
            return error_code, cls.create_error_response(status_code, error_code, error=str(error))

        else:
            # Handle non-ClientError exceptions
            cls.log_error("INTERNAL_ERROR", context={"operation": operation}, exception=error, error=str(error))
            return "INTERNAL_ERROR", cls.create_error_response(500, "INTERNAL_ERROR", error=str(error))

    @classmethod
    def handle_authorization_error(
        cls,
        user_sub: str,
        server_id: str,
        required_permission: str,
        user_role: Optional[str] = None,
        reason: str = None,
    ) -> Dict[str, Any]:
        """
        Handle authorization errors with consistent logging and response format.

        Args:
            user_sub: User's Cognito sub
            server_id: Server ID being accessed
            required_permission: Permission that was required
            user_role: User's actual role (if known)
            reason: Specific reason for authorization failure

        Returns:
            Error response dictionary
        """
        context = {
            "user_sub": user_sub,
            "server_id": server_id,
            "required_permission": required_permission,
            "user_role": user_role,
        }

        if not user_role:
            # User has no membership
            error_code = "NO_SERVER_ACCESS"
            cls.log_error(error_code, context=context, server_id=server_id)
            return cls.create_error_response(403, error_code, server_id=server_id)
        else:
            # User has insufficient permissions
            error_code = "INSUFFICIENT_PERMISSIONS"

            # Determine minimum required role
            permission_levels = {"viewer": 1, "moderator": 2, "admin": 3}
            operation_permissions = {
                "read_server": 1,
                "read_metrics": 1,
                "read_config": 1,
                "control_server": 2,
                "manage_users": 3,
                "manage_config": 3,
            }

            required_level = operation_permissions.get(required_permission, 3)
            required_role = next(
                (role for role, level in permission_levels.items() if level >= required_level), "admin"
            )

            cls.log_error(error_code, context=context, required_role=required_role, user_role=user_role)
            return cls.create_error_response(403, error_code, required_role=required_role, user_role=user_role)

    @classmethod
    def log_membership_operation(
        cls,
        operation: str,
        user_id: str,
        server_id: str,
        role: str = None,
        initiated_by: str = None,
        success: bool = True,
        error: str = None,
    ):
        """
        Log membership operations for audit trail and troubleshooting.

        Args:
            operation: Type of operation (create, update, delete, etc.)
            user_id: User's Cognito sub
            server_id: Server ID
            role: User's role (if applicable)
            initiated_by: Email of user who initiated the operation
            success: Whether the operation succeeded
            error: Error message if operation failed
        """
        log_data = {
            "operation": operation,
            "user_id": user_id,
            "server_id": server_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "success": success,
        }

        if role:
            log_data["role"] = role
        if initiated_by:
            log_data["initiated_by"] = initiated_by
        if error:
            log_data["error"] = error

        if success:
            logger.info(f"MEMBERSHIP OPERATION SUCCESS: {operation}", extra=log_data)
        else:
            logger.error(f"MEMBERSHIP OPERATION FAILED: {operation}", extra=log_data)

    @classmethod
    def log_authorization_attempt(
        cls,
        user_sub: str,
        server_id: str,
        required_permission: str,
        user_role: str = None,
        success: bool = True,
        reason: str = None,
    ):
        """
        Log authorization attempts for security auditing.

        Args:
            user_sub: User's Cognito sub
            server_id: Server ID being accessed
            required_permission: Permission that was required
            user_role: User's role for the server
            success: Whether authorization succeeded
            reason: Reason for authorization result
        """
        log_data = {
            "user_sub": user_sub,
            "server_id": server_id,
            "required_permission": required_permission,
            "user_role": user_role,
            "success": success,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if reason:
            log_data["reason"] = reason

        if success:
            logger.info(f"AUTHORIZATION SUCCESS: {required_permission}", extra=log_data)
        else:
            logger.warning(f"AUTHORIZATION DENIED: {required_permission}", extra=log_data)


class MigrationErrorHandler:
    """
    Specialized error handling for migration operations.
    """

    @classmethod
    def log_migration_progress(
        cls,
        stage: str,
        total_users: int = None,
        processed_users: int = None,
        server_id: str = None,
        success: bool = True,
        error: str = None,
    ):
        """
        Log migration progress for monitoring and troubleshooting.

        Args:
            stage: Migration stage (start, processing, verification, completion)
            total_users: Total number of users to migrate
            processed_users: Number of users processed so far
            server_id: Server being processed (if applicable)
            success: Whether the stage succeeded
            error: Error message if stage failed
        """
        log_data = {"migration_stage": stage, "timestamp": datetime.now(timezone.utc).isoformat(), "success": success}

        if total_users is not None:
            log_data["total_users"] = total_users
        if processed_users is not None:
            log_data["processed_users"] = processed_users
        if server_id:
            log_data["server_id"] = server_id
        if error:
            log_data["error"] = error

        if success:
            logger.info(f"MIGRATION PROGRESS: {stage}", extra=log_data)
        else:
            logger.error(f"MIGRATION FAILED: {stage}", extra=log_data)

    @classmethod
    def create_migration_report(
        cls, total_servers: int, successful_servers: int, total_users: int, successful_users: int, errors: list = None
    ) -> Dict[str, Any]:
        """
        Create migration completion report.

        Args:
            total_servers: Total number of servers processed
            successful_servers: Number of servers successfully migrated
            total_users: Total number of users processed
            successful_users: Number of users successfully migrated
            errors: List of errors encountered during migration

        Returns:
            Migration report dictionary
        """
        report = {
            "migration_completed_at": datetime.now(timezone.utc).isoformat(),
            "servers": {
                "total": total_servers,
                "successful": successful_servers,
                "failed": total_servers - successful_servers,
            },
            "users": {"total": total_users, "successful": successful_users, "failed": total_users - successful_users},
            "success_rate": {
                "servers": (successful_servers / total_servers * 100) if total_servers > 0 else 0,
                "users": (successful_users / total_users * 100) if total_users > 0 else 0,
            },
        }

        if errors:
            report["errors"] = errors

        logger.info("MIGRATION REPORT GENERATED", extra=report)
        return report
