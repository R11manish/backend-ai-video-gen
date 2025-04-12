import asyncio
from generation import VideoGeneration
from speech import SpeechGenerator
from video_creator import VideoCreator

async def main():
    # Initialize all classes
    video_gen = VideoGeneration()
    speech_gen = SpeechGenerator()
    video_creator = VideoCreator()
    
    # Topic to generate content for
    topic = "Nikhil Kamath journey"
    
    # Generate script
    print(f"Generating script about: {topic}")
    script = await video_gen.script(topic)
    print(f"Script generated: {script}")
    
    # Search and download images
    print("Searching for images...")
    images = video_gen.search_images(num_results=12)
    if images and len(images) > 0:
        print(f"Found {len(images)} images, downloading in parallel...")
        downloaded_paths = await video_gen.download_all_images(images)
        successful = [p for p in downloaded_paths if not isinstance(p, Exception)]
        print(f"Downloaded {len(successful)} images successfully")
    else:
        print("No images found.")
        return
    
    # Generate speech from the script
    try:
        print("Generating speech from script...")
        audio_path = await speech_gen.generate_speech_async(
            text=script.content,
            voice_id="Matthew",  # You can try different voices
            output_format="mp3"
        )
        print(f"Speech generated and saved to: {audio_path}")
    except Exception as e:
        print(f"Speech generation error: {e}")
        return
    
    # Create video from images and audio
    try:
        print("Creating video from images and audio...")
        successful_images = [p for p in downloaded_paths if not isinstance(p, Exception)]
        video_path = video_creator.create_video(
            image_paths=successful_images,
            audio_path=audio_path
        )
        print(f"Video created successfully and saved to: {video_path}")
    except Exception as e:
        print(f"Video creation error: {e}")
        return
    
    print("Process completed successfully!")

if __name__ == "__main__":
    asyncio.run(main())