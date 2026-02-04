import urllib.request
import urllib.error
import os
import ipaddress
import json
import base64
from ec2Helper import Ec2Utils
from authHelper import Auth
from utilHelper import Utils

def create_minimal_token(user_sub, instance_id):
    """Create minimal token with only sub and instance_id claims."""
    payload = {
        'sub': user_sub,
        'instance_id': instance_id
    }
    # Base64 encode for simple transport
    payload_json = json.dumps(payload)
    return base64.b64encode(payload_json.encode()).decode()

def is_safe_ip(ip_str):
    """Validate IP is not in dangerous ranges (localhost, private, etc)"""
    try:
        ip = ipaddress.ip_address(ip_str)
        # Allow private IPs (VPC) but block localhost/loopback
        if ip.is_loopback or ip.is_link_local:
            return False
        return True
    except ValueError:
        return False

def handler(event, context):
    """
    Fetch Minecraft server logs from msd-logs service
    """
    try:
        instance_id = event['arguments']['instanceId']
        lines = event['arguments'].get('lines', 100)
        
        # Validate lines parameter
        if not isinstance(lines, int) or lines < 1 or lines > 1000:
            return {
                'success': False,
                'error': 'Invalid lines parameter (must be 1-1000)'
            }
        
        # Authenticate user
        cognito_pool_id = os.environ.get('COGNITO_USER_POOL_ID')
        auth = Auth(cognito_pool_id)
        utils = Utils()
        
        # Extract and validate token
        token = utils.extract_auth_token(event)
        user_claims = auth.process_token(token)
        
        if not user_claims:
            return {
                'success': False,
                'error': 'Unauthorized'
            }
        
        user_sub = user_claims.get('sub')
        
        # Check user authorization for this instance (requires read_server permission)
        is_authorized, user_role, auth_reason = utils.check_user_authorization(user_sub, instance_id, 'read_server')
        if not is_authorized:
            return {
                'success': False,
                'error': 'Forbidden'
            }
        
        # Get instance info
        ec2 = Ec2Utils()
        instance = ec2.list_server_by_id(instance_id)
        
        if not instance:
            return {
                'success': False,
                'error': 'Instance not found'
            }
        
        # Check instance state
        state = instance.get('State', {}).get('Name', 'unknown')
        if state != 'running':
            return {
                'success': False,
                'error': 'Instance not running'
            }
        
        ip_address = instance.get('PrivateIpAddress') or instance.get('PublicIpAddress')
        
        if not ip_address:
            return {
                'success': False,
                'error': 'Instance has no IP address'
            }
        
        # Validate IP address to prevent SSRF
        if not is_safe_ip(ip_address):
            return {
                'success': False,
                'error': 'Invalid IP address'
            }
        
        # Fetch logs from msd-logs service with minimal token
        minimal_token = create_minimal_token(user_sub, instance_id)
        log_service_port = os.environ.get('LOG_SERVICE_PORT', '25566')
        url = f"http://{ip_address}:{log_service_port}/logs?lines={lines}"
        req = urllib.request.Request(url)
        req.add_header('Authorization', f'Bearer {minimal_token}')
        
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                logs = response.read().decode('utf-8')
                
            return {
                'success': True,
                'logs': logs,
                'instanceId': instance_id
            }
            
        except urllib.error.HTTPError as e:
            if e.code == 401:
                return {
                    'success': False,
                    'error': 'Authentication failed'
                }
            return {
                'success': False,
                'error': 'Failed to connect to log server'
            }
        except urllib.error.URLError:
            return {
                'success': False,
                'error': 'Failed to connect to log server'
            }
        
    except Exception as e:
        print(f"Error fetching logs: {str(e)}")
        return {
            'success': False,
            'error': 'Internal server error'
        }
