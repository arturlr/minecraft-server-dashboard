import logging
import os
import ec2Helper
import ddbHelper
import ssmHelper

logger = logging.getLogger()
logger.setLevel(logging.INFO)

appValue = os.getenv("TAG_APP_VALUE")
appName = os.getenv("APP_NAME")
envName = os.getenv("ENVIRONMENT_NAME")
queue_url = os.getenv("SSM_COMMAND_QUEUE_URL")
bootstrap_doc_name = os.getenv("BOOTSTRAP_SSM_DOC_NAME")

# Initialize helpers
core_dyn = ddbHelper.CoreTableDyn()
ec2_utils = ec2Helper.Ec2Utils()
ssm_helper = ssmHelper.SSMHelper(queue_url, bootstrap_doc_name)


def handler(event, context):
    """
    Process server boot events - validate configuration and apply defaults.
    Triggered when EC2 instance state changes to 'running'.
    """
    try:
        # Parse EventBridge event
        detail = event.get("detail", {})
        instance_id = detail.get("instance-id")
        state = detail.get("state")

        if not instance_id or state != "running":
            logger.info(f"Ignoring event: instance={instance_id}, state={state}")
            return {"statusCode": 200, "body": "Event ignored"}

        logger.info(f"Processing server boot: {instance_id}")

        # Get server info from EC2
        server_info = get_server_info_from_ec2(instance_id)
        if not server_info:
            logger.warning(f"Server not found or not tagged: {instance_id}")
            return {"statusCode": 404, "body": "Server not found"}

        # Validate and configure server
        validate_and_configure_server(instance_id, server_info, core_dyn, ec2_utils)

        # Update server info in CoreTable
        core_dyn.put_server_info(server_info)

        logger.info(f"Server boot processing completed: {instance_id}")
        return {"statusCode": 200, "body": "Server processed successfully"}

    except Exception as e:
        logger.error(f"Error processing server boot: {str(e)}", exc_info=True)
        return {"statusCode": 500, "body": f"Error: {str(e)}"}


def get_server_info_from_ec2(instance_id):
    """Get server information from EC2 tags and metadata."""
    try:
        server_data = ec2_utils.list_server_by_id(instance_id)
        if server_data["TotalInstances"] == 0:
            return None

        instance = server_data["Instances"][0]

        # Check if it's a Minecraft server
        tags = {tag["Key"]: tag["Value"] for tag in instance.get("Tags", [])}
        if tags.get("app") != os.getenv("TAG_APP_VALUE"):
            return None

        return {
            "id": instance_id,
            "name": tags.get("Name", instance_id),
            "state": instance["State"]["Name"],
            "vCpus": instance.get("CpuOptions", {}).get("CoreCount", 0),
            "memSize": 0,  # Would need instance type lookup
            "diskSize": 0,  # Would need EBS volume lookup
            "launchTime": instance.get("LaunchTime", "").isoformat() if instance.get("LaunchTime") else "",
            "publicIp": instance.get("PublicIpAddress", ""),
            "initStatus": "pending",
            "iamStatus": "checking",
            "configStatus": "validating",
            "configValid": False,
            "configWarnings": [],
            "configErrors": [],
            "autoConfigured": False,
        }
    except Exception as e:
        logger.error(f"Error getting server info from EC2: {str(e)}")
        return None


def queue_bootstrap_server(instance_id):
    """
    Queue bootstrap SSM command for asynchronous execution.
    The SSMCommandProcessor Lambda will handle retries and execution.

    Args:
        instance_id (str): EC2 instance ID
    """
    logger.info(f"------- queue_bootstrap_server {instance_id}")

    try:
        # Queue the bootstrap command for asynchronous execution
        result = ssm_helper.queue_bootstrap_command(instance_id)

        if result["success"]:
            logger.info(f"Bootstrap command queued for {instance_id}: MessageId={result['messageId']}")
        else:
            logger.error(f"Failed to queue bootstrap command for {instance_id}: {result['message']}")

    except Exception as e:
        logger.error(f"Error in bootstrap_server for {instance_id}: {str(e)}", exc_info=True)
        # Don't raise - allow the event handler to continue


def validate_and_configure_server(instance_id, server_info, core_dyn, ec2_utils):
    """Validate server configuration and apply defaults if needed."""
    try:
        warnings = []
        errors = []
        auto_configured = False

        # Get existing config
        config = core_dyn.get_server_config(instance_id)

        if not config:
            # Apply default configuration
            logger.info(f"Applying default configuration to {instance_id}")

            default_config = {
                "id": instance_id,
                "alarmThreshold": 5.0,
                "alarmEvaluationPeriod": 30,
                "runCommand": "java -Xmx1024M -Xms1024M -jar server.jar nogui",
                "workDir": "/opt/minecraft",
                "timezone": "UTC",
                "isBootstrapComplete": False,
                "autoConfigured": True,
            }

            core_dyn.put_server_config(default_config)
            auto_configured = True
            warnings.append("Default configuration applied")
        else:
            # Validate existing config
            if not config.get("runCommand"):
                warnings.append("Missing run command")
            if not config.get("workDir"):
                warnings.append("Missing working directory")
            if config.get("alarmThreshold", 0) <= 0:
                warnings.append("Invalid alarm threshold")
            # Check if server needs bootstrapping
            if config.get("isBootstrapComplete"):
                logger.warning(f"Server {instance_id} is not bootstrapped, queueing bootstrap command")
                queue_bootstrap_server(instance_id)

        # Check IAM instance profile
        try:
            iam_status = ec2_utils.check_instance_profile(instance_id)
            if iam_status != "correct":
                warnings.append("IAM instance profile needs attention")
                server_info["iamStatus"] = "needs_fix"
            else:
                server_info["iamStatus"] = "correct"
        except Exception as e:
            errors.append(f"IAM check failed: {str(e)}")
            server_info["iamStatus"] = "error"

        # Update server info with validation results
        server_info.update(
            {
                "configStatus": "valid" if not errors else "invalid",
                "configValid": len(errors) == 0,
                "configWarnings": warnings,
                "configErrors": errors,
                "autoConfigured": auto_configured,
            }
        )

        logger.info(f"Validation completed: {instance_id}, warnings={len(warnings)}, errors={len(errors)}")

    except Exception as e:
        logger.error(f"Error validating server configuration: {str(e)}")
        server_info.update(
            {"configStatus": "error", "configValid": False, "configErrors": [f"Validation error: {str(e)}"]}
        )
