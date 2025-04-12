import asyncio
import random
import os
import json
import shutil
from generation import VideoGeneration
from speech import SpeechGenerator
from video_creator import VideoCreator
from s3_upload import S3Upload

async def process_request(topic):
    # Keep track of temporary files for cleanup
    temp_files = []
    
    # Initialize all classes
    video_gen = VideoGeneration()
    speech_gen = SpeechGenerator()
    video_creator = VideoCreator()
    s3_upload = S3Upload()
    
    # Generate script
    print(f"Generating script about: {topic}")
    script = await video_gen.script(topic)
    print(f"Script generated: {script}")
    
    # Search and download images
    print("Searching for images...")
    images = video_gen.search_images(num_results=15)
    if not images or len(images) == 0:
        print("No images found.")
        return {"status": "error", "message": "No images found"}
    
    print(f"Found {len(images)} images, downloading in parallel...")
    downloaded_paths = await video_gen.download_all_images(images)
    successful = [p for p in downloaded_paths if not isinstance(p, Exception)]
    temp_files.extend(successful)  # Add to cleanup list
    print(f"Downloaded {len(successful)} images successfully")
    
    # Generate speech from the script
    try:
        print("Generating speech from script...")
        voices = speech_gen.list_available_voices(language_code="en-US")
        
        # Randomly select one of the available voices
        random_voice = random.choice(voices)
        print(f"Randomly selected voice: {random_voice}")

        audio_path = await speech_gen.generate_speech_async(
            text=script.content,
            voice_id=random_voice,  # Use randomly selected voice
            output_format="mp3"
        )
        temp_files.append(audio_path)  # Add to cleanup list
        print(f"Speech generated and saved to: {audio_path}")
    except Exception as e:
        print(f"Speech generation error: {e}")
        cleanup_temp_files(temp_files)
        return {"status": "error", "message": f"Speech generation error: {str(e)}"}
    
    # Create video from images and audio
    try:
        print("Creating video from images and audio...")
        successful_images = [p for p in downloaded_paths if not isinstance(p, Exception)]
        video_path = video_creator.create_video(
            image_paths=successful_images,
            audio_path=audio_path
        )
        temp_files.append(video_path)  # Add to cleanup list
        print(f"Video created successfully and saved to: {video_path}")
        
        # Upload video to S3
        try:
            s3_key = f"videos/{os.path.basename(video_path)}"
            s3_url = s3_upload.upload_file(video_path, s3_key)
            print(f"Video uploaded successfully to: {s3_url}")
            cleanup_temp_files(temp_files)
            return {"status": "success", "video_url": s3_url}
        except Exception as e:
            error_msg = f"S3 upload error: {e}"
            print(error_msg)
            cleanup_temp_files(temp_files)
            return {"status": "error", "message": error_msg}
    except Exception as e:
        error_msg = f"Video creation error: {e}"
        print(error_msg)
        cleanup_temp_files(temp_files)
        return {"status": "error", "message": error_msg}

def cleanup_temp_files(file_paths):
    """Clean up temporary files to avoid filling up Lambda's /tmp space"""
    for path in file_paths:
        if path and os.path.exists(path):
            try:
                os.remove(path)
                print(f"Removed temporary file: {path}")
            except Exception as e:
                print(f"Failed to remove file {path}: {e}")
    
    # Clean up temp directories if they exist
    temp_dirs = ["/tmp/images", "/tmp/audio", "/tmp/videos", "/tmp/moviepy_temp"]
    for dir_path in temp_dirs:
        if os.path.exists(dir_path):
            try:
                shutil.rmtree(dir_path)
                print(f"Removed temporary directory: {dir_path}")
            except Exception as e:
                print(f"Failed to remove directory {dir_path}: {e}")

def lambda_handler(event, context):
    """
    AWS Lambda function handler that processes SQS messages
    Each message should contain a 'topic' field for video generation
    """
    try:
        results = []
        # Process all SQS events in the batch
        for record in event.get('Records', []):
            # Parse the message body as JSON
            try:
                message = json.loads(record.get('body', '{}'))
                topic = message.get('topic')
                
                if not topic:
                    result = {
                        'status': 'error',
                        'message': 'Missing topic in SQS message'
                    }
                    results.append(result)
                    continue
                
                # Process the video generation request
                # Use the existing event loop if available
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    # If no event loop exists, create a new one
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                # Run the async process_request function
                if loop.is_running():
                    # Use existing event loop with future
                    future = asyncio.run_coroutine_threadsafe(process_request(topic), loop)
                    result = future.result()
                else:
                    # Run the coroutine in the event loop
                    result = loop.run_until_complete(process_request(topic))
                
                results.append(result)
                
            except json.JSONDecodeError:
                result = {
                    'status': 'error',
                    'message': 'Invalid JSON in SQS message'
                }
                results.append(result)
        
        # Return a combined result for all processed messages
        return {
            'statusCode': 200,
            'body': json.dumps({
                'results': results,
                'processed_messages': len(results)
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'status': 'error',
                'message': f'Lambda error: {str(e)}'
            })
        } 