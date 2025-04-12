import os
import boto3
from dotenv import load_dotenv

load_dotenv()

class SpeechGenerator:
    
    def __init__(self):
        aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
        aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        aws_region = os.getenv("AWS_REGION", "ap-south-1")
        
        if not aws_access_key or not aws_secret_key:
            print("Warning: AWS credentials not set. Text-to-speech functionality will be unavailable.")
            self.polly_client = None
        else:
            self.polly_client = boto3.client(
                'polly',
                region_name=aws_region,
                aws_access_key_id=aws_access_key,
                aws_secret_access_key=aws_secret_key
            )
    
    def generate_speech(self, text, voice_id="Joanna", output_format="mp3", output_path="./audio"):
        if not self.polly_client:
            raise ValueError("AWS credentials not set. Cannot use text-to-speech.")
            
        # Create output directory if it doesn't exist
        os.makedirs(output_path, exist_ok=True)
        
        # Request speech synthesis
        response = self.polly_client.synthesize_speech(
            Text=text,
            OutputFormat=output_format,
            VoiceId=voice_id,
            Engine='neural'  # Use neural engine for better quality
        )
        
        # Save the audio file
        import time
        filename = f"speech_{int(time.time())}.{output_format}"
        file_path = os.path.join(output_path, filename)
        
        if "AudioStream" in response:
            with open(file_path, "wb") as file:
                file.write(response["AudioStream"].read())
            return file_path
        else:
            raise Exception("Failed to generate speech")
    
    def list_available_voices(self, language_code=None):
        if not self.polly_client:
            raise ValueError("AWS credentials not set. Cannot list voices.")
            
        params = {}
        if language_code:
            params['LanguageCode'] = language_code
            
        response = self.polly_client.describe_voices(**params)
        return [voice['Id'] for voice in response.get('Voices', [])]
    
    async def generate_speech_async(self, text, voice_id="Joanna", output_format="mp3", output_path="./audio"):
        import asyncio
        
        # Run the synchronous method in a thread pool
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, 
            self.generate_speech,
            text, 
            voice_id, 
            output_format, 
            output_path
        )


if __name__ == "__main__":
    # Example usage
    generator = SpeechGenerator()
    
    try:
        # List available voices
        voices = generator.list_available_voices(language_code="en-US")
        print(f"Available voices: {voices[:10]}...")
        
        # Generate speech
        # output_file = generator.generate_speech(
        #     "Hello, this is a test of Amazon Polly text-to-speech service.",
        #     voice_id="Matthew"
        # )
        # print(f"Speech generated and saved to: {output_file}")
    except Exception as e:
        print(f"Error: {e}")
