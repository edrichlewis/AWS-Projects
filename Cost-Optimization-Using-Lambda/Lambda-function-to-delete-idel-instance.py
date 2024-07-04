import boto3
import datetime

def lambda_handler(event, context):
    ec2 = boto3.client('ec2')
    cloudwatch = boto3.client('cloudwatch')

    # Get list of running instances
    instances = ec2.describe_instances(Filters=[{'Name': 'instance-state-name', 'Values': ['running']}])
    
    # Check CloudWatch metrics for each instance
    for reservation in instances['Reservations']:
        for instance in reservation['Instances']:
            instance_id = instance['InstanceId']
            metrics = cloudwatch.get_metric_statistics(
                Namespace='AWS/EC2',
                MetricName='CPUUtilization',
                Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
                StartTime=datetime.datetime.utcnow() - datetime.timedelta(days=7),
                EndTime=datetime.datetime.utcnow(),
                Period=86400,
                Statistics=['Average']
            )
            
            avg_cpu_utilization = sum([point['Average'] for point in metrics['Datapoints']]) / len(metrics['Datapoints'])
            
            if avg_cpu_utilization < 10:  # Threshold for idle instance
                ec2.terminate_instances(InstanceIds=[instance_id])

    return "Idle resources terminated."
