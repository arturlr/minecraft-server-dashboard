import boto3
import logging
import os
import authHelper
import ec2Helper
import utilHelper

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ec2_client = boto3.client('ec2')
ec2_utils = ec2Helper.Ec2Utils()
utl = utilHelper.Utils()

# Environment variables
ec2_instance_profile_name = os.getenv('EC2_INSTANCE_PROFILE_NAME')
ec2_instance_profile_arn = os.getenv('EC2_INSTANCE_PROFILE_ARN')
cognito_pool_id = os.getenv('COGNITO_USER_POOL_ID')

auth = authHelper.Auth(cognito_pool_id)


class IamProfile:
    """Manages IAM instance profile association for EC2 instances"""
    
    def __init__(self, instance_id):
        self.ec2_client = boto3.client('ec2')
        self.instance_id = instance_id
        self.association_id = None

    def manage_iam_profile(self):
        """
        Ensure instance has the correct IAM profile attached
        
        Returns:
            dict: Status response with success/error information
        """
        try:
            iam_profile = ec2_utils.describe_iam_profile(self.instance_id, "associated")

            if iam_profile and iam_profile['Arn'] == ec2_instance_profile_arn:
                logger.info(f"Instance IAM Profile is already valid: {iam_profile['Arn']}")
                return {"status": "success", "message": "IAM profile already correct"}
            elif iam_profile:
                logger.info(f"Instance IAM Profile is invalid: {iam_profile['Arn']}")
                self.association_id = iam_profile['AssociationId']
                rsp = self.disassociate_iam_profile()
                if not rsp:
                    return {"status": "error", "message": "Failed to disassociate existing profile"}
        except Exception as e:
            logger.warning(f"Error describing IAM profile: {str(e)}. Will attempt to attach profile anyway.")

        logger.info("Attaching IAM role to the Minecraft Instance")
        return self.attach_iam_profile()

    def disassociate_iam_profile(self):
        """
        Remove existing IAM profile association
        
        Returns:
            bool: True if successful, False otherwise
        """
        logger.info(f"Disassociating IAM profile: {self.association_id}")
        try:
            self.ec2_client.disassociate_iam_instance_profile(AssociationId=self.association_id)
        except Exception as e:
            if "InvalidAssociationID.NotFound" in str(e):
                logger.warning(f"Association ID not found: {self.association_id}. Continuing...")
                return True
            else:
                logger.error(f"Error disassociating IAM profile: {str(e)}")
                return False

        # Check if profile is fully disassociated
        def check_disassociated_status():
            try:
                return ec2_utils.describe_iam_profile(
                    self.instance_id, 
                    "disassociated", 
                    self.association_id
                ) is not None
            except Exception as e:
                logger.warning(f"Error checking disassociation status: {str(e)}. Assuming disassociated.")
                return True

        # Retry checking disassociation status
        if not utl.retry_operation(check_disassociated_status, max_retries=30, delay=5):
            logger.warning("Profile timeout during disassociating")
            return True  # Continue anyway

        return True
    
    def attach_iam_profile(self):
        """
        Attach the correct IAM profile to the instance
        
        Returns:
            dict: Status response with success/error information
        """
        logger.info(f"Attaching IAM profile: {ec2_instance_profile_name}")
        
        try:
            response = self.ec2_client.associate_iam_instance_profile(
                IamInstanceProfile={"Name": ec2_instance_profile_name},
                InstanceId=self.instance_id
            )
        except Exception as e:
            error_msg = str(e)
            if "UnauthorizedOperation" in error_msg:
                logger.error(f"Unauthorized operation when attaching IAM profile: {error_msg}")
                return {"status": "error", "message": "Unauthorized to attach IAM profile", "code": "UnauthorizedOperation"}
            else:
                logger.error(f"Error attaching IAM profile: {error_msg}")
                return {"status": "error", "message": f"Failed to attach IAM profile: {error_msg}"}

        # Check if profile is properly attached
        def check_associated_status():
            try:
                iam_profile = ec2_utils.describe_iam_profile(self.instance_id, "associated")
                return iam_profile and iam_profile['Arn'] == ec2_instance_profile_arn
            except Exception as e:
                logger.warning(f"Error checking association status: {str(e)}")
                return False

        # Retry checking profile association status
        if not utl.retry_operation(check_associated_status, max_retries=30, delay=5):
            logger.warning("Profile timeout during association")
            return {"status": "error", "message": "Timeout waiting for profile attachment"}

        return {"status": "success", "message": "IAM profile attached successfully"}


def check_authorization(event, instance_id, user_attributes):
    """
    Check if user is authorized to perform actions on instance
    
    Args:
        event: Lambda event object containing identity info
        instance_id: EC2 instance ID
        user_attributes: Dict containing user info including email
        
    Returns:
        bool: True if authorized, False if not
    """
    cognito_groups = event["identity"].get("groups", [])
    user_email = user_attributes["email"]
    
    logger.info(f"Authorization check: user={user_email}, instance={instance_id}, groups={cognito_groups}")
    
    try:
        is_authorized, auth_reason = utl.check_user_authorization(
            cognito_groups, 
            instance_id, 
            user_email, 
            ec2_utils
        )
        
        if is_authorized:
            logger.info(f"Authorization SUCCESS: {auth_reason} - {user_email} authorized for {instance_id}")
        else:
            logger.warning(f"Authorization DENIED: User {user_email} not authorized for {instance_id}")
        
        return is_authorized
        
    except Exception as e:
        logger.error(f"Authorization check FAILED: user={user_email}, instance={instance_id}, error={str(e)}", exc_info=True)
        raise


def handler(event, context):
    """
    Main handler for fixServerRole Lambda
    Validates authorization and fixes IAM profile for EC2 instance
    
    Args:
        event: Lambda event from AppSync
        context: Lambda context
        
    Returns:
        dict: Response with appropriate status code and body
    """
    logger.info(f"fixServerRole Lambda invoked")
    
    try:
        # Check for authorization header
        if 'request' not in event:
            logger.error("No request found in event")
            return utl.response(400, {"err": "Invalid request format"})
            
        if 'headers' not in event['request']:
            logger.error("No headers found in request")
            return utl.response(401, {"err": "No headers found in request"})
            
        if 'authorization' not in event['request']['headers']:
            logger.error("No Authorization header found")
            return utl.response(401, {"err": "No Authorization header found"})
        
        token = event['request']['headers']['authorization']
        
    except Exception as e:
        logger.error(f"Error processing request headers: {str(e)}")
        return utl.response(401, {"err": str(e)})

    # Get user info from JWT token
    try:
        user_attributes = auth.process_token(token)
    except Exception as e:
        logger.error(f"Token processing FAILED: error={str(e)}", exc_info=True)
        return utl.response(401, {"err": "Invalid token"})

    if user_attributes is None:
        logger.error("Invalid Token")
        return utl.response(401, {"err": "Invalid token"})

    # Validate arguments exist
    if not event.get("arguments"):
        logger.error("No arguments found in the event")
        return utl.response(400, {"err": "No arguments found in the event"})

    # Extract instance_id from arguments
    instance_id = event["arguments"].get("instanceId")

    if not instance_id:
        logger.error("Instance id is not present in the event") 
        return utl.response(400, {"err": "Instance id is not present in the event"})

    logger.info(f"Processing fixServerRole for instance: {instance_id}, user: {user_attributes['email']}")

    # Check authorization
    try:
        is_authorized = check_authorization(event, instance_id, user_attributes)
    except Exception as e:
        logger.error(f"Authorization check FAILED: user={user_attributes.get('email', 'unknown')}, instance={instance_id}, error={str(e)}", exc_info=True)
        return utl.response(500, {"err": "Authorization check failed"})

    if not is_authorized:
        logger.error(f"{user_attributes['email']} is not authorized for instance {instance_id}")
        return utl.response(401, {"err": "User not authorized"})

    # Fix IAM role
    try:
        logger.info(f"Creating IamProfile manager for instance: {instance_id}")
        iam_profile = IamProfile(instance_id)
        
        logger.info(f"Executing IAM profile management for instance: {instance_id}")
        result = iam_profile.manage_iam_profile()
        
        if result.get("status") == "success":
            logger.info(f"IAM role fix SUCCESS: {result.get('message')} - instance={instance_id}")
            return utl.response(200, {"msg": result.get("message"), "success": True})
        else:
            error_msg = result.get("message", "Unknown error")
            logger.error(f"IAM role fix FAILED: {error_msg} - instance={instance_id}")
            return utl.response(500, {"err": error_msg, "success": False})
            
    except Exception as e:
        logger.error(f"IAM role fix FAILED with exception: instance={instance_id}, error={str(e)}", exc_info=True)
        return utl.response(500, {"err": f"Failed to fix IAM role: {str(e)}", "success": False})
