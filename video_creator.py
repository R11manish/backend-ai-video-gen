import os
import time
import subprocess
import json
import cv2
from PIL import Image
import tempfile
import shutil
import uuid
import logging

# Configure the logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

class VideoCreator:
    def __init__(self):
        os.makedirs("/tmp/videos", exist_ok=True)
        os.makedirs("/tmp/images_resized", exist_ok=True)
        os.makedirs("/tmp/temp", exist_ok=True)
        # Check if ffmpeg is installed and accessible
        try:
            ffmpeg_version = subprocess.check_output(['ffmpeg', '-version'], stderr=subprocess.STDOUT).decode('utf-8')
            logger.info(f"ffmpeg version: {ffmpeg_version.splitlines()[0]}")
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            logger.error(f"ffmpeg not found or not accessible: {str(e)}")
            raise RuntimeError("ffmpeg is required but not available")
    
    def resize_image(self, img_path, target_width, target_height, aspect_ratio="9:16"):
        """Resize image and save to a temporary location with white background padding."""
        try:
            # Create a unique filename for the resized image
            filename = os.path.basename(img_path)
            resized_path = f"/tmp/images_resized/{uuid.uuid4()}_{filename}"
            
            # Open the image
            img = Image.open(img_path)
            original_width, original_height = img.size
            
            # Calculate new dimensions while preserving aspect ratio
            if aspect_ratio == "9:16":  # Vertical video
                orig_aspect = original_width / original_height
                target_aspect = 9 / 16
                
                if orig_aspect > target_aspect:  # Image is wider than 9:16
                    new_width = target_width
                    new_height = int(original_height * (new_width / original_width))
                else:  # Image is taller or same as 9:16
                    new_height = target_height
                    new_width = int(original_width * (new_height / original_height))
            else:  # 16:9 horizontal video
                orig_aspect = original_width / original_height
                target_aspect = 16 / 9
                
                if orig_aspect > target_aspect:  # Image is wider than 16:9
                    new_width = target_width
                    new_height = int(original_height * (new_width / original_width))
                else:  # Image is taller or same as 16:9
                    new_height = target_height
                    new_width = int(original_width * (new_height / original_height))
            
            # Make sure we don't exceed the target dimensions
            new_width = min(new_width, target_width)
            new_height = min(new_height, target_height)
            
            # Resize the image
            img = img.resize((new_width, new_height), Image.LANCZOS)
            
            # Create a new white background image
            background = Image.new("RGB", (target_width, target_height), (255, 255, 255))
            
            # Calculate position to center the image on the background
            position = ((target_width - new_width) // 2, (target_height - new_height) // 2)
            
            # Paste the resized image onto the background
            background.paste(img, position)
            
            # Save the result
            background.save(resized_path)
            return resized_path
        except Exception as e:
            logger.error(f"Error resizing image {img_path}: {str(e)}")
            return None
    
    def create_video(self, image_paths, audio_path, output_path="/tmp/videos", fps=24, subtitles=None, aspect_ratio="9:16"):
        """Create a video from images and audio using ffmpeg directly."""
        try:
            # Create output directory if it doesn't exist
            os.makedirs(output_path, exist_ok=True)
            
            # Filter out any paths that are exceptions
            valid_image_paths = [p for p in image_paths if not isinstance(p, Exception) and p is not None]
            
            if not valid_image_paths:
                raise ValueError("No valid image paths provided")
            
            # Verify image paths exist
            valid_image_paths = [p for p in valid_image_paths if os.path.exists(p)]
            logger.info(f"Using {len(valid_image_paths)} valid images")
            
            if not valid_image_paths:
                raise ValueError("No valid image files found at the specified paths")

            # Set dimensions based on aspect ratio
            if aspect_ratio == "9:16":  # Vertical video
                width, height = 720, 1280  # 720x1280 for vertical 9:16
            else:  # Default to 16:9
                width, height = 1280, 720  # 1280x720 for horizontal 16:9
            
            # Get audio duration using ffprobe
            audio_info_cmd = [
                'ffprobe', '-v', 'quiet', '-print_format', 'json',
                '-show_format', '-show_streams', audio_path
            ]
            audio_info = json.loads(subprocess.check_output(audio_info_cmd).decode('utf-8'))
            audio_duration = float(audio_info['format']['duration'])
            logger.info(f"Audio duration: {audio_duration} seconds")
            
            # Calculate duration for each image
            image_duration = audio_duration / len(valid_image_paths)
            
            # Create a temporary directory for the image list file
            temp_dir = "/tmp/temp"
            os.makedirs(temp_dir, exist_ok=True)
            
            # Resize images to match video dimensions
            resized_image_paths = []
            for img_path in valid_image_paths:
                resized_path = self.resize_image(img_path, width, height, aspect_ratio)
                if resized_path:
                    resized_image_paths.append(resized_path)
            
            if not resized_image_paths:
                raise ValueError("No images could be resized successfully")
            
            # Create a temporary file for the image list
            image_list_path = f"{temp_dir}/image_list_{uuid.uuid4()}.txt"
            
            with open(image_list_path, 'w') as f:
                for img_path in resized_image_paths:
                    # Each image repeated based on image_duration and fps
                    # duration needs to be in seconds for -t option
                    f.write(f"file '{img_path}'\n")
                    f.write(f"duration {image_duration}\n")
                
                # Add the last image one more time without duration
                # This is needed because the last duration is ignored by ffmpeg
                f.write(f"file '{resized_image_paths[-1]}'\n")
            
            # Generate output filename
            timestamp = int(time.time())
            output_file = os.path.join(output_path, f"video_{timestamp}.mp4")
            
            # Build the ffmpeg command
            ffmpeg_cmd = [
                'ffmpeg',
                '-y',  # Overwrite output file if it exists
                '-f', 'concat',
                '-safe', '0',
                '-i', image_list_path,
                '-i', audio_path,
                '-c:v', 'libx264',
                '-pix_fmt', 'yuv420p',
                '-preset', 'medium',
                '-r', str(fps),
                '-c:a', 'aac',
                '-b:a', '192k',
                '-shortest',  # End when the shortest input stream ends
                output_file
            ]
            
            logger.info(f"Running ffmpeg command: {' '.join(ffmpeg_cmd)}")
            
            # Execute the ffmpeg command
            subprocess.run(ffmpeg_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Clean up temporary files
            os.remove(image_list_path)
            for img_path in resized_image_paths:
                if os.path.exists(img_path):
                    os.remove(img_path)
            
            logger.info(f"Video successfully created: {output_file}")
            return output_file
            
        except subprocess.CalledProcessError as e:
            logger.error(f"ffmpeg error: {e.stderr.decode('utf-8') if e.stderr else str(e)}")
            raise RuntimeError(f"ffmpeg command failed: {str(e)}")
        except Exception as e:
            logger.error(f"Error creating video: {str(e)}")
            raise
