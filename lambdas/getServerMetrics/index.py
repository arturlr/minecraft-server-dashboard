import json
import os
import boto3
from datetime import datetime, timedelta
from botocore.exceptions import ClientError
import utilHelper

cloudwatch = boto3.client("cloudwatch")

utl = utilHelper.Utils()

appValue = os.getenv("TAG_APP_VALUE")


def handler(event, context):
    """
    Fetch historical CloudWatch metrics for a server instance.
    Returns the last hour of metrics data.
    """
    print(f"Event: {json.dumps(event)}")

    # Extract instance ID from event
    instance_id = event.get("arguments", {}).get("id")
    if not instance_id:
        return {"statusCode": 400, "body": json.dumps({"error": "Instance ID is required"})}

    # Time range: last 1 hours (to ensure we get data even if instance was recently started)
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=1)

    try:
        cpu_stats = utl.get_metrics_data(
            instance_id, "CWAgent", "cpu_usage_active", "Percent", "Average", start_time, end_time, 300
        )
        mem_stats = utl.get_metrics_data(
            instance_id, "CWAgent", "mem_used_percent", "Percent", "Average", start_time, end_time, 300
        )
        network_in = utl.get_metrics_data(
            instance_id, "MinecraftDashboard", "transmit_bandwidth", "Bytes/Second", "Sum", start_time, end_time, 300
        )
        user_stats = utl.get_metrics_data(
            instance_id, "MinecraftDashboard", "user_count", "Count", "Maximum", start_time, end_time, 300
        )

        # Format response
        response = {
            "id": instance_id,
            "cpuStats": json.dumps(cpu_stats),
            "networkStats": json.dumps(network_in),
            "memStats": json.dumps(mem_stats),
            "activeUsers": json.dumps(user_stats),
        }

        print(
            f"Returning metrics for {instance_id}: CPU={len(cpu_stats)}, Net={len(network_in)}, Mem={len(mem_stats)}, Users={len(user_stats)}"
        )
        return response

    except ClientError as e:
        print(f"Error fetching metrics: {str(e)}")
        return {"statusCode": 500, "body": json.dumps({"error": f"Failed to fetch metrics: {str(e)}"})}
