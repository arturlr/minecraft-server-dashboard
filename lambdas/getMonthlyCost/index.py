import boto3
import logging
import os
import authHelper
import utilHelper
from datetime import datetime, timezone, timedelta

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ce_client = boto3.client("ce")
cognito_idp = boto3.client("cognito-idp")
ENCODING = "utf-8"

appValue = os.getenv("TAG_APP_VALUE")
cognito_pool_id = os.getenv("COGNITO_USER_POOL_ID")

auth = authHelper.Auth(cognito_pool_id)
utl = utilHelper.Utils()

# Token validation is now handled by authHelper


def getUsageCost(granularity, startDate, endDate, instanceId):
    try:
        usageQuantity = 0
        unblendedCost = 0
        request = {
            "TimePeriod": {"Start": startDate, "End": endDate},
            "Filter": {
                "And": [
                    {"Dimensions": {"Key": "USAGE_TYPE_GROUP", "Values": ["EC2: Running Hours"]}},
                    {"Tags": {"Key": "aws:cloudformation:stack-id", "Values": [instanceId]}},
                ]
            },
            "Granularity": granularity,
            "Metrics": ["UnblendedCost", "UsageQuantity"],
        }
        response = ce_client.get_cost_and_usage(**request)

        if granularity == "MONTHLY":
            for results in response["ResultsByTime"]:
                unblendedCost = float(results["Total"]["UnblendedCost"]["Amount"])
                usageQuantity = float(results["Total"]["UsageQuantity"]["Amount"])

            return {"date": endDate, "unblendedCost": round(unblendedCost, 1), "usageQuantity": round(usageQuantity, 1)}

        else:
            usageDays = []
            for results in response["ResultsByTime"]:
                usageDays.append(
                    {
                        "date": results["TimePeriod"]["Start"],
                        "unblendedCost": float(results["Total"]["UnblendedCost"]["Amount"]),
                        "usageQuantity": float(results["Total"]["UsageQuantity"]["Amount"]),
                    }
                )
            return usageDays

    except Exception as e:
        logger.error(str(e))
        return {"unblendedCost": 0, "usageQuantity": 0}


def handler(event, context):
    try:
        # Use current time in UTC for date calculations
        end_date = datetime.now(timezone.utc)
        last_day_of_prev_month = end_date.replace(day=1, hour=23, minute=59, second=59) - timedelta(days=1)
        dt_1st_day_of_month_ago = end_date.replace(day=1, hour=0, minute=0, second=0)

        if end_date.strftime("%Y-%m-%d") == dt_1st_day_of_month_ago.strftime("%Y-%m-%d"):
            start_date = last_day_of_prev_month
        else:
            start_date = dt_1st_day_of_month_ago

        # Validate request and token
        if (
            "request" not in event
            or "headers" not in event["request"]
            or "authorization" not in event["request"]["headers"]
        ):
            logger.error("Missing authorization header")
            return []

        # Get the token from the request
        token = event["request"]["headers"]["authorization"]

        # Use authHelper to validate token and get user attributes
        user_attributes = auth.process_token(token)

        # Check if claims are valid
        if user_attributes is None:
            logger.error("Invalid Token")
            return []

        # Get instance ID from arguments
        if not event.get("arguments") or not event["arguments"].get("instanceId"):
            logger.error("Missing instanceId argument")
            return []

        instance_id = event["arguments"]["instanceId"]

        # Check authorization using utilHelper
        cognito_groups = event["identity"].get("groups", [])
        is_authorized, auth_reason = utl.check_user_authorization(
            cognito_groups,
            instance_id,
            user_attributes["email"],
            None,  # We don't have ec2_utils here, but we can check admin status
        )

        # If not admin, check if user is authorized for this instance
        if not is_authorized and not utl.is_admin_user(cognito_groups):
            logger.error(f"User {user_attributes['email']} not authorized for instance {instance_id}")
            return []

        # Get cost data for the specific instance
        monthlyTotalUsage = getUsageCost(
            "MONTHLY", start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"), instance_id
        )

        return [
            {
                "id": instance_id,
                "timePeriod": end_date.strftime("%b"),
                "UnblendedCost": monthlyTotalUsage["unblendedCost"],
                "UsageQuantity": monthlyTotalUsage["usageQuantity"],
            }
        ]

    except Exception as e:
        logger.error(f"Error in handler: {str(e)}")
        return []
