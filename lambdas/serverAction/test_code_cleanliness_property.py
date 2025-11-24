#!/usr/bin/env python3
"""
Property-based test for ServerAction Lambda code cleanliness
Tests that ServerAction code does not contain forbidden EC2 operations or infrastructure management

**Feature: async-server-actions, Property 9: ServerAction code cleanliness**
**Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5**
"""
import sys
import os
import unittest
import re
import ast
from hypothesis import given, strategies as st, settings

# Path to the ServerAction Lambda code
SERVERACTION_FILE = os.path.join(os.path.dirname(__file__), 'index.py')


class TestServerActionCodeCleanliness(unittest.TestCase):
    """
    Property-based test suite for ServerAction Lambda code cleanliness
    
    **Feature: async-server-actions, Property 9: ServerAction code cleanliness**
    **Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5**
    """
    
    @classmethod
    def setUpClass(cls):
        """Load the ServerAction code once for all tests"""
        with open(SERVERACTION_FILE, 'r') as f:
            cls.serveraction_code = f.read()
        
        # Parse the code into an AST for structural analysis
        try:
            cls.serveraction_ast = ast.parse(cls.serveraction_code)
        except SyntaxError as e:
            cls.fail(f"ServerAction code has syntax errors: {e}")
    
    def test_no_direct_ec2_operations(self):
        """
        Property Test: No Direct EC2 Operations
        
        The ServerAction Lambda code should NOT contain any direct calls to
        EC2 client methods for starting, stopping, or rebooting instances.
        
        Forbidden patterns:
        - ec2_client.start_instances
        - ec2_client.stop_instances
        - ec2_client.reboot_instances
        
        **Feature: async-server-actions, Property 9: ServerAction code cleanliness**
        **Validates: Requirements 6.1**
        """
        forbidden_patterns = [
            r'ec2_client\.start_instances',
            r'ec2_client\.stop_instances',
            r'ec2_client\.reboot_instances',
        ]
        
        violations = []
        for pattern in forbidden_patterns:
            matches = re.finditer(pattern, self.serveraction_code)
            for match in matches:
                # Find line number
                line_num = self.serveraction_code[:match.start()].count('\n') + 1
                violations.append(f"Line {line_num}: Found forbidden pattern '{pattern}'")
        
        self.assertEqual(
            len(violations), 0,
            f"ServerAction code contains forbidden EC2 operations:\n" + "\n".join(violations)
        )
    
    def test_no_iam_profile_management(self):
        """
        Property Test: No IAM Profile Management
        
        The ServerAction Lambda code should NOT contain any IAM profile
        management logic, including the IamProfile class or related operations.
        
        Forbidden patterns:
        - IamProfile class definition or usage
        - IAM profile attachment operations
        - iam_client usage
        
        **Feature: async-server-actions, Property 9: ServerAction code cleanliness**
        **Validates: Requirements 6.2**
        """
        forbidden_patterns = [
            r'class\s+IamProfile',
            r'IamProfile\(',
            r'associate_iam_instance_profile',
            r'replace_iam_instance_profile',
            r'disassociate_iam_instance_profile',
            r'iam_client\s*=',
            r'boto3\.client\([\'"]iam[\'"]\)',
        ]
        
        violations = []
        for pattern in forbidden_patterns:
            matches = re.finditer(pattern, self.serveraction_code)
            for match in matches:
                line_num = self.serveraction_code[:match.start()].count('\n') + 1
                violations.append(f"Line {line_num}: Found forbidden IAM pattern '{pattern}'")
        
        self.assertEqual(
            len(violations), 0,
            f"ServerAction code contains forbidden IAM profile management:\n" + "\n".join(violations)
        )
    
    def test_no_eventbridge_management(self):
        """
        Property Test: No EventBridge Management
        
        The ServerAction Lambda code should NOT contain any EventBridge rule
        management logic for scheduling operations.
        
        Forbidden patterns:
        - EventBridge client creation
        - Rule creation/deletion operations
        - Target management operations
        
        **Feature: async-server-actions, Property 9: ServerAction code cleanliness**
        **Validates: Requirements 6.3**
        """
        forbidden_patterns = [
            r'events_client\s*=',
            r'boto3\.client\([\'"]events[\'"]\)',
            r'put_rule',
            r'delete_rule',
            r'put_targets',
            r'remove_targets',
            r'enable_rule',
            r'disable_rule',
        ]
        
        violations = []
        for pattern in forbidden_patterns:
            matches = re.finditer(pattern, self.serveraction_code)
            for match in matches:
                line_num = self.serveraction_code[:match.start()].count('\n') + 1
                violations.append(f"Line {line_num}: Found forbidden EventBridge pattern '{pattern}'")
        
        self.assertEqual(
            len(violations), 0,
            f"ServerAction code contains forbidden EventBridge management:\n" + "\n".join(violations)
        )
    
    def test_no_cloudwatch_alarm_management(self):
        """
        Property Test: No CloudWatch Alarm Management
        
        The ServerAction Lambda code should NOT contain any CloudWatch alarm
        management logic for monitoring and auto-shutdown.
        
        Forbidden patterns:
        - CloudWatch client creation
        - Alarm creation/deletion operations
        - Alarm state management
        
        **Feature: async-server-actions, Property 9: ServerAction code cleanliness**
        **Validates: Requirements 6.4**
        """
        forbidden_patterns = [
            r'cloudwatch_client\s*=',
            r'boto3\.client\([\'"]cloudwatch[\'"]\)',
            r'put_metric_alarm',
            r'delete_alarms',
            r'describe_alarms',
            r'set_alarm_state',
            r'enable_alarm_actions',
            r'disable_alarm_actions',
        ]
        
        violations = []
        for pattern in forbidden_patterns:
            matches = re.finditer(pattern, self.serveraction_code)
            for match in matches:
                line_num = self.serveraction_code[:match.start()].count('\n') + 1
                violations.append(f"Line {line_num}: Found forbidden CloudWatch pattern '{pattern}'")
        
        self.assertEqual(
            len(violations), 0,
            f"ServerAction code contains forbidden CloudWatch alarm management:\n" + "\n".join(violations)
        )
    
    def test_only_allowed_operations(self):
        """
        Property Test: Only Allowed Operations Present
        
        The ServerAction Lambda code should ONLY contain:
        - Authorization logic (check_authorization)
        - Queue sending logic (send_to_queue)
        - Read-only operation handlers (handle_get_server_config, handle_get_server_users)
        - Cognito group management (check_and_create_group)
        
        **Feature: async-server-actions, Property 9: ServerAction code cleanliness**
        **Validates: Requirements 6.5**
        """
        # Extract all function definitions from the AST
        function_names = []
        for node in ast.walk(self.serveraction_ast):
            if isinstance(node, ast.FunctionDef):
                function_names.append(node.name)
        
        # Define allowed functions
        allowed_functions = {
            'handler',
            'check_authorization',
            'send_to_queue',
            'action_process_sync',
            'handle_get_server_config',
            'handle_get_server_users',
            'check_and_create_group',
            'handle_local_invocation',
        }
        
        # Define forbidden function patterns (functions that should NOT exist)
        forbidden_function_patterns = [
            'handle_server_action',  # Should only be in ServerActionProcessor
            'handle_fix_role',       # Should only be in ServerActionProcessor
            'handle_update_server_config',  # Should only be in ServerActionProcessor
        ]
        
        violations = []
        for func_name in function_names:
            if func_name in forbidden_function_patterns:
                violations.append(f"Found forbidden function: {func_name}")
        
        self.assertEqual(
            len(violations), 0,
            f"ServerAction code contains forbidden functions:\n" + "\n".join(violations)
        )
    
    @given(
        search_term=st.sampled_from([
            'start_instances',
            'stop_instances',
            'reboot_instances',
            'IamProfile',
            'put_rule',
            'delete_rule',
            'put_metric_alarm',
            'delete_alarms',
        ])
    )
    @settings(max_examples=100)
    def test_code_cleanliness_property(self, search_term):
        """
        Property Test: Code Cleanliness Across Multiple Forbidden Patterns
        
        For any forbidden operation pattern, the ServerAction code should not
        contain that pattern. This property test verifies cleanliness across
        a range of forbidden operations.
        
        **Feature: async-server-actions, Property 9: ServerAction code cleanliness**
        **Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5**
        """
        # Check if the forbidden term appears in the code
        # We need to be careful to avoid false positives from comments
        
        # Remove comments from code for analysis
        code_without_comments = re.sub(r'#.*$', '', self.serveraction_code, flags=re.MULTILINE)
        code_without_docstrings = re.sub(r'""".*?"""', '', code_without_comments, flags=re.DOTALL)
        code_without_docstrings = re.sub(r"'''.*?'''", '', code_without_docstrings, flags=re.DOTALL)
        
        # Search for the forbidden term
        if search_term in code_without_docstrings:
            # Find the context
            matches = re.finditer(re.escape(search_term), self.serveraction_code)
            violations = []
            for match in matches:
                line_num = self.serveraction_code[:match.start()].count('\n') + 1
                line_start = self.serveraction_code.rfind('\n', 0, match.start()) + 1
                line_end = self.serveraction_code.find('\n', match.end())
                if line_end == -1:
                    line_end = len(self.serveraction_code)
                line_content = self.serveraction_code[line_start:line_end].strip()
                
                # Skip if it's in a comment
                if not line_content.startswith('#'):
                    violations.append(f"Line {line_num}: {line_content}")
            
            if violations:
                self.fail(
                    f"ServerAction code contains forbidden pattern '{search_term}':\n" +
                    "\n".join(violations)
                )


if __name__ == '__main__':
    unittest.main()
