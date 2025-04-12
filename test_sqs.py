import boto3
import json
import os
import argparse
from dotenv import load_dotenv

load_dotenv()

def setup_sqs_queue():
    """Create the SQS queue if it doesn't exist"""
    aws_access_key = os.getenv("ACCESS_KEY_ID")
    aws_secret_key = os.getenv("SECRET_ACCESS_KEY")
    aws_region = os.getenv("REGION", "ap-south-1")
    queue_name = "video-generation-queue"
    
    if not aws_access_key or not aws_secret_key:
        raise ValueError("AWS credentials not set. Check your .env file.")
    
    sqs = boto3.client(
        'sqs',
        region_name=aws_region,
        aws_access_key_id=aws_access_key,
        aws_secret_access_key=aws_secret_key
    )
    
    try:
        response = sqs.get_queue_url(QueueName=queue_name)
        queue_url = response['QueueUrl']
        print(f"Queue {queue_name} already exists.")
    except sqs.exceptions.QueueDoesNotExist:
        # Create the queue
        print(f"Creating queue {queue_name}...")
        response = sqs.create_queue(
            QueueName=queue_name,
            Attributes={
                'VisibilityTimeout': '900',  # 15 minutes
                'MessageRetentionPeriod': '86400',  # 1 day
                'ReceiveMessageWaitTimeSeconds': '10'  # Long polling
            }
        )
        queue_url = response['QueueUrl']
        print(f"Queue {queue_name} created successfully.")
    
    return sqs, queue_url

def send_message_to_sqs(sqs, queue_url, topic):
    """Send a message to the SQS queue"""
    message = {
        "topic": topic
    }
    
    response = sqs.send_message(
        QueueUrl=queue_url,
        MessageBody=json.dumps(message)
    )
    
    print(f"Message sent to SQS queue with ID: {response['MessageId']}")
    print(f"Request for topic '{topic}' has been queued.")
    
    return response['MessageId']

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Setup SQS queue and send a message')
    parser.add_argument('topic', nargs='?', default="hardik panday journey", 
                        help='The topic for the video (default: "hardik panday journey")')
    args = parser.parse_args()
    
    sqs, queue_url = setup_sqs_queue()
    message_id = send_message_to_sqs(sqs, queue_url, args.topic)
    
    print("\nTo manually trigger the Lambda function:")
    print(f"1. Go to AWS Lambda console")
    print(f"2. Find your Lambda function")
    print(f"3. Create a test event with this body:")
    print(json.dumps({
        "Records": [
            {
                "body": json.dumps({"topic": args.topic})
            }
        ]
    }, indent=2))
    print(f"4. Run the test event to simulate SQS trigger") 