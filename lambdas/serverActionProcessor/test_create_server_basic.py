"""
Basic test to verify the process_create_server function structure
"""

from unittest.mock import patch


def test_process_create_server_structure():
    """Test that process_create_server function exists and has correct structure"""
    # Import the module
    import sys

    sys.path.insert(0, "../../layers/ec2Helper")
    sys.path.insert(0, "../../layers/ddbHelper")
    sys.path.insert(0, "../../layers/utilHelper")

    # Mock the dependencies
    with patch("boto3.client"), patch("boto3.Session"):

        # Import after mocking
        import index

        # Verify the function exists
        assert hasattr(index, "process_create_server"), "process_create_server function should exist"

        # Verify it's callable
        assert callable(index.process_create_server), "process_create_server should be callable"

        print("✓ process_create_server function exists and is callable")

        # Test with minimal message structure
        message = {
            "serverName": "test-server",
            "instanceType": "t3.micro",
            "shutdownMethod": "CPUUtilization",
            "userEmail": "test@example.com",
        }

        # Mock the ec2_utils.create_ec2_instance to return None (simulating failure)
        with patch.object(index.ec2_utils, "create_ec2_instance", return_value=None):
            result = index.process_create_server(message)
            assert result is False, "Should return False when EC2 creation fails"
            print("✓ process_create_server handles EC2 creation failure correctly")


if __name__ == "__main__":
    test_process_create_server_structure()
    print("\n✓ All basic structure tests passed!")
