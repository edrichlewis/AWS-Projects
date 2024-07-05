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
            instance_type = instance['InstanceType']
            print(f"Checking instance {instance_id} of type {instance_type}")
            
            metrics = cloudwatch.get_metric_statistics(
                Namespace='AWS/EC2',
                MetricName='CPUUtilization',
                Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
                StartTime=datetime.datetime.utcnow() - datetime.timedelta(days=7),
                EndTime=datetime.datetime.utcnow(),
                Period=86400,
                Statistics=['Average']
            )
            
            # Check if there are any data points
            if len(metrics['Datapoints']) > 0:
                avg_cpu_utilization = sum([point['Average'] for point in metrics['Datapoints']]) / len(metrics['Datapoints'])
                print(f"Average CPU utilization for instance {instance_id} is {avg_cpu_utilization}%")
                
                if avg_cpu_utilization < 20:  # Threshold for underutilized instance
                    # Example of downsizing: t2.medium to t2.micro
                    if instance_type == 't2.medium':
                        new_instance_type = 't2.micro'
                        print(f"Downgrading instance {instance_id} from {instance_type} to {new_instance_type}")
                        
                        # Check instance state before stopping
                        instance_state = ec2.describe_instances(InstanceIds=[instance_id])['Reservations'][0]['Instances'][0]['State']['Name']
                        
                        if instance_state == 'running':
                            # Stop the instance
                            ec2.stop_instances(InstanceIds=[instance_id])
                            ec2.get_waiter('instance_stopped').wait(InstanceIds=[instance_id])
                            
                            # Change the instance type
                            ec2.modify_instance_attribute(InstanceId=instance_id, InstanceType={'Value': new_instance_type})
                            
                            # Start the instance
                            ec2.start_instances(InstanceIds=[instance_id])
                            ec2.get_waiter('instance_running').wait(InstanceIds=[instance_id])
                            
                            print(f"Instance {instance_id} successfully downgraded to {new_instance_type}")
                        else:
                            print(f"Instance {instance_id} is not in running state. Skipping downgrade.")
                else:
                    print(f"Instance {instance_id} CPU utilization is above threshold")
            else:
                print(f"No CPU utilization data for instance {instance_id}")

    return "Underutilized instances downsized."
