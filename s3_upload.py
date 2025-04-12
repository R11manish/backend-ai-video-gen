import os
import boto3

class S3Upload:
    def __init__(self):
        aws_access_key = os.getenv("ACCESS_KEY_ID")
        aws_secret_key = os.getenv("SECRET_ACCESS_KEY")
        aws_region = os.getenv("REGION", "ap-south-1")
        self.bucket_name = os.getenv("BUCKET_NAME")
        
        if not aws_access_key or not aws_secret_key:
            print("Warning: AWS credentials not set. S3 upload functionality will be unavailable.")
            self.s3_client = None
        else:
            self.s3_client = boto3.client(
                's3',
                region_name=aws_region,
                aws_access_key_id=aws_access_key,
                aws_secret_access_key=aws_secret_key
            )
    
    def upload_file(self, file_path, s3_key=None):
        if not self.s3_client:
            raise ValueError("AWS credentials not set. Cannot upload to S3.")
            
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
            
        if s3_key is None:
            s3_key = os.path.basename(file_path)
      
        try:
            self.s3_client.upload_file(file_path, self.bucket_name, s3_key)
            s3_url = f"https://{self.bucket_name}.s3.amazonaws.com/{s3_key}"
            print(f"File uploaded successfully to {s3_url}")
            return s3_url
        except Exception as e:
            print(f"Error uploading file to S3: {e}")
            raise
    


