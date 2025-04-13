import asyncio
import random
import os
import json
import shutil
from generation import VideoGeneration
from speech import SpeechGenerator
from video_creator import VideoCreator
from s3_upload import S3Upload
from db_manager import VideoDatabase
import traceback
import sys
import logging

# Configure the logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

async def process_request(topic):
    # Keep track of temporary files for cleanup
    temp_files = []
    
    # Initialize all classes
    video_gen = VideoGeneration()
    speech_gen = SpeechGenerator()
    video_creator = VideoCreator()
    s3_upload = S3Upload()
    video_db = VideoDatabase()
    
    try:
        # Generate script
        logger.info(f"Generating script about: {topic}")
        script = await video_gen.script(topic)
        logger.info(f"Script generated: {script}")
        
        # Search and download images
        logger.info("Searching for images...")
        images = video_gen.search_images(num_results=15)
        if not images or len(images) == 0:
            logger.error("No images found.")
            return {"status": "error", "message": "No images found"}
        
        logger.info(f"Found {len(images)} images, downloading in parallel...")
        downloaded_paths = await video_gen.download_all_images(images)
        successful = [p for p in downloaded_paths if not isinstance(p, Exception)]
        temp_files.extend(successful)  # Add to cleanup list
        logger.info(f"Downloaded {len(successful)} images successfully")
        
        # Generate speech from the script
        try:
            logger.info("Generating speech from script...")
            voices = speech_gen.list_available_voices(language_code="en-US")
            
            # Randomly select one of the available voices
            random_voice = random.choice(voices)
            logger.info(f"Randomly selected voice: {random_voice}")

            audio_path = await speech_gen.generate_speech_async(
                text=script.content,
                voice_id=random_voice,  # Use randomly selected voice
                output_format="mp3"
            )
            temp_files.append(audio_path)  # Add to cleanup list
            logger.info(f"Speech generated and saved to: {audio_path}")
        except Exception as e:
            logger.error(f"Speech generation error: {e}")
            cleanup_temp_files(temp_files)
            return {"status": "error", "message": f"Speech generation error: {str(e)}"}
        
        # Create video from images and audio using ffmpeg
        try:
            logger.info("Creating video from images and audio...")
            successful_images = [p for p in downloaded_paths if not isinstance(p, Exception)]
            video_path = video_creator.create_video(
                image_paths=successful_images,
                audio_path=audio_path
            )
            temp_files.append(video_path)  # Add to cleanup list
            logger.info(f"Video created successfully and saved to: {video_path}")
            
            # Upload video to S3
            try:
                s3_key = f"videos/{os.path.basename(video_path)}"
                s3_url = s3_upload.upload_file(video_path, s3_key)
                logger.info(f"Video uploaded successfully to: {s3_url}")
                
                # Save video information to DynamoDB
                try:
                    video_id = video_db.save_video(title=topic, url=s3_url)
                    logger.info(f"Video information saved to DynamoDB with ID: {video_id}")
                    cleanup_temp_files(temp_files)
                    return {"status": "success", "video_url": s3_url, "video_id": video_id}
                except Exception as e:
                    error_msg = f"DynamoDB error: {e}"
                    logger.error(error_msg)
                    # Continue even if DynamoDB save fails, as video is already uploaded
                    cleanup_temp_files(temp_files)
                    return {"status": "partial_success", "video_url": s3_url, "message": error_msg}
            except Exception as e:
                error_msg = f"S3 upload error: {e}"
                logger.error(error_msg)
                cleanup_temp_files(temp_files)
                return {"status": "error", "message": error_msg}
        except Exception as e:
            error_msg = f"Video creation error: {e}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            cleanup_temp_files(temp_files)
            return {"status": "error", "message": error_msg}
    except Exception as e:
        logger.error(f"Unexpected error during processing: {str(e)}")
        logger.error(traceback.format_exc())
        cleanup_temp_files(temp_files)
        return {"status": "error", "message": f"Process failed: {str(e)}"}

def cleanup_temp_files(file_paths):
    """Clean up temporary files to avoid filling up Lambda's /tmp space"""
    for path in file_paths:
        if path and os.path.exists(path):
            try:
                os.remove(path)
                logger.info(f"Removed temporary file: {path}")
            except Exception as e:
                logger.error(f"Failed to remove file {path}: {e}")
    
    # Clean up temp directories if they exist
    temp_dirs = ["/tmp/images", "/tmp/audio", "/tmp/videos", "/tmp/temp", "/tmp/images_resized"]
    for dir_path in temp_dirs:
        if os.path.exists(dir_path):
            try:
                shutil.rmtree(dir_path)
                logger.info(f"Removed temporary directory: {dir_path}")
            except Exception as e:
                logger.error(f"Failed to remove directory {dir_path}: {e}")
                
def lambda_handler(event, context):
    # Start with logging the event received
    logger.info(f"EVENT RECEIVED: {json.dumps(event)}")
    
    try:
        # Log start of processing
        logger.info("PROCESS: Starting to process the event")
        
        # Extract the message from SQS event structure
        if 'Records' in event and len(event['Records']) > 0:
            logger.info("PROCESS: Found Records in event")
            message_body = event['Records'][0]['body']
            logger.info(f"PROCESS: Raw message body: {message_body}")
            
            # Parse the JSON message body if it's a string
            if isinstance(message_body, str):
                try:
                    message_body = json.loads(message_body)
                    logger.info(f"PROCESS: Parsed message body: {json.dumps(message_body)}")
                except json.JSONDecodeError as e:
                    logger.error(f"ERROR: Failed to parse message body as JSON: {str(e)}")
                    raise
            
            # Extract the topic
            topic = message_body.get('topic')
            logger.info(f"PROCESS: Extracted topic: {topic}")
            
            # Log all environment variables (redacted sensitive info)
            env_vars = {k: v if 'key' not in k.lower() and 'secret' not in k.lower() and 'password' not in k.lower() else '[REDACTED]' 
                       for k, v in os.environ.items()}
            logger.info(f"ENV VARS: {json.dumps(env_vars)}")
            
            # Verify ffmpeg installation before proceeding
            try:
                import subprocess
                ffmpeg_output = subprocess.check_output(['ffmpeg', '-version'], stderr=subprocess.STDOUT).decode('utf-8')
                logger.info(f"FFMPEG VERSION: {ffmpeg_output.splitlines()[0]}")
            except Exception as e:
                logger.error(f"FFMPEG CHECK ERROR: {str(e)}")
                logger.error(traceback.format_exc())
                raise RuntimeError("ffmpeg verification failed")
            
            # Run the async process_request function using asyncio
            try:
                logger.info(f"PROCESS: Starting async process for topic: {topic}")
                
                loop = asyncio.get_event_loop()
                result = loop.run_until_complete(process_request(topic))
                
                logger.info(f"PROCESS: Video generation complete. Result: {result}")
                
                return {
                    'statusCode': 200,
                    'body': json.dumps(result)
                }
            except Exception as e:
                logger.error(f"PROCESS ERROR: {str(e)}")
                logger.error(traceback.format_exc())
                raise
        else:
            logger.error("ERROR: No Records found in the event")
            return {
                'statusCode': 400,
                'body': json.dumps('No valid records found in the event')
            }
    except Exception as e:
        logger.error(f"CRITICAL ERROR: {str(e)}")
        logger.error("TRACEBACK:")
        logger.error(traceback.format_exc())

        raise 