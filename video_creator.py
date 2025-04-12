import os
import time
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
import imageio

# Install required backends for imageio
try:
    imageio.plugins.ffmpeg.download()
except:
    pass

# Fix for PIL.Image.ANTIALIAS deprecation
import PIL
if hasattr(PIL.Image, 'Resampling'):  # Pillow >= 9.0.0
    ANTIALIAS = PIL.Image.Resampling.LANCZOS
else:  # Pillow < 9.0.0
    ANTIALIAS = PIL.Image.ANTIALIAS

# Monkey patch the constant
PIL.Image.ANTIALIAS = ANTIALIAS

class VideoCreator:
    def __init__(self):
        os.makedirs("./videos", exist_ok=True)
        
        # Ensure imageio has the necessary backends
        try:
            import cv2
        except ImportError:
            print("Installing opencv backend for imageio...")
            import subprocess
            subprocess.check_call(["pip", "install", "opencv-python"])
        
        try:
            import av
        except ImportError:
            print("Installing pyav backend for imageio...")
            import subprocess
            subprocess.check_call(["pip", "install", "av"])
    
    def create_video(self, image_paths, audio_path, output_path="./videos", fps=24):
        """
        Create a video from images and audio
        
        Args:
            image_paths (list): List of paths to image files
            audio_path (str): Path to audio file
            output_path (str): Directory to save the output video
            fps (int): Frames per second for the video
            
        Returns:
            str: Path to the output video file
        """
        # Create output directory if it doesn't exist
        os.makedirs(output_path, exist_ok=True)
        
        # Filter out any paths that are exceptions
        valid_image_paths = [p for p in image_paths if not isinstance(p, Exception) and p is not None]
        
        if not valid_image_paths:
            raise ValueError("No valid image paths provided")
        
        # Verify image paths exist
        valid_image_paths = [p for p in valid_image_paths if os.path.exists(p)]
        print(f"Using {len(valid_image_paths)} valid images")
        
        if not valid_image_paths:
            raise ValueError("No valid image files found at the specified paths")
        
        # Load audio file
        audio_clip = AudioFileClip(audio_path)
        
        # Get actual audio duration
        audio_duration = audio_clip.duration
        
        # Calculate duration for each image
        image_duration = audio_duration / len(valid_image_paths)
        
        # Create image clips
        image_clips = []
        for img_path in valid_image_paths:
            try:
                clip = ImageClip(img_path).set_duration(image_duration)
                # Resize to 720p (1280x720) while maintaining aspect ratio
                clip = clip.resize(height=720)
                image_clips.append(clip)
                print(f"Successfully loaded image: {img_path}")
            except Exception as e:
                print(f"Error loading image {img_path}: {e}")
        
        if not image_clips:
            raise ValueError("No images could be loaded successfully")
        
        # Concatenate image clips
        video_clip = concatenate_videoclips(image_clips, method="compose")
        
        # Add audio to the video
        video_clip = video_clip.set_audio(audio_clip)
        
        # Set the duration to match the audio
        video_clip = video_clip.set_duration(audio_duration)
        
        # Generate output filename
        timestamp = int(time.time())
        output_file = os.path.join(output_path, f"video_{timestamp}.mp4")
        
        # Write the video to file with progress bar
        video_clip.write_videofile(
            output_file, 
            fps=fps, 
            codec='libx264', 
            audio_codec='aac',
            threads=4,  # Use multiple threads for faster processing
            preset='medium'  # Balances encoding speed and quality
        )
        
        # Close clips to free resources
        audio_clip.close()
        video_clip.close()
        
        return output_file 