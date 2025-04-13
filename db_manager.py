import os
import boto3
import uuid
import time
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

class VideoDatabase:
    def __init__(self):
        aws_access_key = os.getenv("ACCESS_KEY_ID")
        aws_secret_key = os.getenv("SECRET_ACCESS_KEY")
        aws_region = os.getenv("REGION", "ap-south-1")
        self.table_name = os.getenv("VIDEO_TABLE_NAME", "ai_videos")
        
        if not aws_access_key or not aws_secret_key:
            logger.warning("AWS credentials not set. DynamoDB functionality will be unavailable.")
            self.dynamodb = None
            self.table = None
        else:
            # Initialize the DynamoDB client
            self.dynamodb = boto3.resource(
                'dynamodb',
                region_name=aws_region,
                aws_access_key_id=aws_access_key,
                aws_secret_access_key=aws_secret_key
            )
            
           
            self.table = self.dynamodb.Table(self.table_name)
    
    def save_video(self, title, url):
        """Save video information to DynamoDB"""
        if not self.dynamodb or not self.table:
            raise ValueError("AWS credentials not set. Cannot use DynamoDB.")
        
        # Generate a unique ID
        video_id = str(uuid.uuid4())
        timestamp = int(time.time())
        
        try:
            # Save to DynamoDB
            self.table.put_item(
                Item={
                    'id': video_id,
                    'title': title,
                    'url': url,
                    'created_at': timestamp
                }
            )
            logger.info(f"Video info saved to DynamoDB with ID: {video_id}")
            return video_id
        except Exception as e:
            logger.error(f"Error saving video to DynamoDB: {str(e)}")
            raise 