import os
import time
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, TextClip, CompositeVideoClip, ColorClip
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
    
    def create_video(self, image_paths, audio_path, output_path="./videos", fps=24, subtitles=None, aspect_ratio="9:16"):
        """
        Create a video from images and audio
        
        Args:
            image_paths (list): List of paths to image files
            audio_path (str): Path to audio file
            output_path (str): Directory to save the output video
            fps (int): Frames per second for the video
            subtitles (list): List of subtitle dictionaries with 'text', 'start', 'end' keys
            aspect_ratio (str): Aspect ratio of the video (default: "9:16" for vertical video)
            
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
        
        # Set dimensions based on aspect ratio
        if aspect_ratio == "9:16":  # Vertical video
            width, height = 720, 1280  # 720x1280 for vertical 9:16
        else:  # Default to 16:9
            width, height = 1280, 720  # 1280x720 for horizontal 16:9
        
        # Create image clips
        image_clips = []
        for img_path in valid_image_paths:
            try:
                img_clip = ImageClip(img_path).set_duration(image_duration)
                
                # Get original dimensions
                original_w, original_h = img_clip.size
                
                # Create a white background with target dimensions
                background = ColorClip(size=(width, height), color=(255, 255, 255)).set_duration(image_duration)
                
                # Resize image while maintaining aspect ratio
                if aspect_ratio == "9:16":  # Vertical video
                    orig_aspect = original_w / original_h
                    target_aspect = 9 / 16
                    
                    # Calculate new dimensions to fit within the frame while preserving aspect ratio
                    if orig_aspect > target_aspect:  # Image is wider than 9:16
                        # Scale based on width
                        new_width = width
                        new_height = int(original_h * (new_width / original_w))
                    else:  # Image is taller or same as 9:16
                        # Scale based on height
                        new_height = height
                        new_width = int(original_w * (new_height / original_h))
                else:  # 16:9 horizontal video
                    orig_aspect = original_w / original_h
                    target_aspect = 16 / 9
                    
                    # Calculate new dimensions to fit within the frame while preserving aspect ratio
                    if orig_aspect > target_aspect:  # Image is wider than 16:9
                        # Scale based on width
                        new_width = width
                        new_height = int(original_h * (new_width / original_w))
                    else:  # Image is taller or same as 16:9
                        # Scale based on height
                        new_height = height
                        new_width = int(original_w * (new_height / original_h))
                
                # Make sure we don't exceed the frame dimensions
                new_width = min(new_width, width)
                new_height = min(new_height, height)
                
                # Resize the image clip
                resized_clip = img_clip.resize((new_width, new_height))
                
                # Position the resized image at the center of the background
                img_pos = ('center', 'center')
                
                # Create a composite clip with white background and centered image
                clip = CompositeVideoClip([background, resized_clip.set_position(img_pos)], 
                                          size=(width, height))
                
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
        
        # Add subtitles if provided
        if subtitles:
            subtitle_clips = []
            
            for subtitle in subtitles:
                text = subtitle['text']
                start_time = subtitle['start']
                end_time = subtitle['end']
                duration = end_time - start_time
                
                # Create subtitle clip
                txt_clip = TextClip(
                    text, 
                    fontsize=30, 
                    color='white',
                    bg_color='black',
                    font='Arial',
                    method='caption',
                    align='center',
                    size=(video_clip.w * 0.9, None)  # 90% of video width
                ).set_position(('center', 'bottom')).set_duration(duration).set_start(start_time)
                
                subtitle_clips.append(txt_clip)
            
            # Add all subtitle clips to the video
            if subtitle_clips:
                video_clip = CompositeVideoClip([video_clip] + subtitle_clips)
        
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