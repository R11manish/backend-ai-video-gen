import asyncio
import random
import os
from generation import VideoGeneration
from speech import SpeechGenerator
from video_creator import VideoCreator
from s3_upload import S3Upload

async def main():
    video_gen = VideoGeneration()
    speech_gen = SpeechGenerator()
    video_creator = VideoCreator()
    s3_upload = S3Upload()
    
    topic = "anushka sharama  journey"
    
    print(f"Generating script about: {topic}")
    script = await video_gen.script(topic)
    print(f"Script generated: {script}")
    
    print("Searching for images...")
    images = video_gen.search_images(num_results=15)
    if images and len(images) > 0:
        print(f"Found {len(images)} images, downloading in parallel...")
        downloaded_paths = await video_gen.download_all_images(images)
        successful = [p for p in downloaded_paths if not isinstance(p, Exception)]
        print(f"Downloaded {len(successful)} images successfully")
    else:
        print("No images found.")
        return
    
    try:
        print("Generating speech from script...")
        voices = speech_gen.list_available_voices(language_code="en-US")
        
        random_voice = random.choice(voices)
        print(f"Randomly selected voice: {random_voice}")

        audio_path = await speech_gen.generate_speech_async(
            text=script.content,
            voice_id=random_voice,  
            output_format="mp3"
        )
        print(f"Speech generated and saved to: {audio_path}")
    except Exception as e:
        print(f"Speech generation error: {e}")
        return
    
    try:
        print("Creating video from images and audio...")
        successful_images = [p for p in downloaded_paths if not isinstance(p, Exception)]
        video_path = video_creator.create_video(
            image_paths=successful_images,
            audio_path=audio_path
        )
        print(f"Video created successfully and saved to: {video_path}")
        
        try:
            s3_key = f"videos/{os.path.basename(video_path)}"
            s3_url = s3_upload.upload_file(video_path, s3_key)
            print(f"Video uploaded successfully to: {s3_url}")
        except Exception as e:
            print(f"S3 upload error: {e}")
    except Exception as e:
        print(f"Video creation error: {e}")
        return
    
    print("Process completed successfully!")

if __name__ == "__main__":
    asyncio.run(main())