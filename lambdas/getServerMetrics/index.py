import json
import os
import boto3
from datetime import datetime, timedelta
from botocore.exceptions import ClientError

cloudwatch = boto3.client('cloudwatch')

def handler(event, context):
    """
    Fetch historical CloudWatch metrics for a server instance.
    Returns the last hour of metrics data.
    """
    print(f"Event: {json.dumps(event)}")
    
    # Extract instance ID from event
    instance_id = event.get('arguments', {}).get('id')
    if not instance_id:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Instance ID is required'})
        }
    
    # Time range: last 6 hours (to ensure we get data even if instance was recently started)
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=6)
    
    try:
        # Fetch CPU metrics
        cpu_stats = get_metric_data(
            instance_id=instance_id,
            metric_name='cpu_usage_active',
            namespace='CWAgent',
            start_time=start_time,
            end_time=end_time,
            statistic='Average',
            dimensions=[
                {'Name': 'InstanceId', 'Value': instance_id},
                {'Name': 'cpu', 'Value': 'cpu-total'}
            ]
        )
        
        # Fetch Network In metrics
        network_in = get_metric_data(
            instance_id=instance_id,
            metric_name='transmit_bandwidth',
            namespace='MinecraftDashboard',
            start_time=start_time,
            end_time=end_time,
            statistic='Sum'
        )
        
        # Fetch Memory metrics (custom metric from CloudWatch agent)
        mem_stats = get_metric_data(
            instance_id=instance_id,
            metric_name='mem_used_percent',
            namespace='CWAgent',
            start_time=start_time,
            end_time=end_time,
            statistic='Average',
            dimensions=[
                {'Name': 'InstanceId', 'Value': instance_id}
            ]
        )
        
        # Fetch User Count (custom metric)
        user_stats = get_metric_data(
            instance_id=instance_id,
            metric_name='user_count',
            namespace='MinecraftDashboard',
            start_time=start_time,
            end_time=end_time,
            statistic='Maximum',
            dimensions=[
                {'Name': 'InstanceId', 'Value': instance_id}
            ]
        )
        
        # Format response
        response = {
            'id': instance_id,
            'cpuStats': json.dumps(cpu_stats),
            'networkStats': json.dumps(network_in),
            'memStats': json.dumps(mem_stats),
            'activeUsers': json.dumps(user_stats)
        }
        
        print(f"Returning metrics for {instance_id}: CPU={len(cpu_stats)}, Net={len(network_in)}, Mem={len(mem_stats)}, Users={len(user_stats)}")
        return response
        
    except ClientError as e:
        print(f"Error fetching metrics: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'Failed to fetch metrics: {str(e)}'})
        }


def get_metric_data(instance_id, metric_name, namespace, start_time, end_time, statistic, dimensions=None):
    """
    Fetch metric data from CloudWatch and format it for the frontend.
    """
    if dimensions is None:
        dimensions = [
            {'Name': 'InstanceId', 'Value': instance_id}
        ]
    
    try:
        print(f"Querying CloudWatch: Namespace={namespace}, Metric={metric_name}, Dimensions={dimensions}")
        
        response = cloudwatch.get_metric_statistics(
            Namespace=namespace,
            MetricName=metric_name,
            Dimensions=dimensions,
            StartTime=start_time,
            EndTime=end_time,
            Period=60,  # 1 minute intervals
            Statistics=[statistic]
        )
        
        # Format data points for ApexCharts
        datapoints = []
        for point in sorted(response.get('Datapoints', []), key=lambda x: x['Timestamp']):
            datapoints.append({
                'x': int(point['Timestamp'].timestamp() * 1000),  # Convert to milliseconds
                'y': round(point.get(statistic, 0), 2)
            })
        
        if len(datapoints) > 0:
            print(f"Fetched {len(datapoints)} points for {metric_name}. First: {datapoints[0]}, Last: {datapoints[-1]}")
        else:
            print(f"No datapoints found for {metric_name} in namespace {namespace} with dimensions {dimensions}")
        
        return datapoints
        
    except ClientError as e:
        print(f"Error fetching {metric_name}: {str(e)}")
        return []
