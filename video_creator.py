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

logger = logging.getLogger()
logger.setLevel(logging.INFO)

class VideoCreator:
    def __init__(self):
        os.makedirs("/tmp/videos", exist_ok=True)
        os.makedirs("/tmp/images_resized", exist_ok=True)
        os.makedirs("/tmp/temp", exist_ok=True)
        try:
            ffmpeg_version = subprocess.check_output(['ffmpeg', '-version'], stderr=subprocess.STDOUT).decode('utf-8')
            logger.info(f"ffmpeg version: {ffmpeg_version.splitlines()[0]}")
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            logger.error(f"ffmpeg not found or not accessible: {str(e)}")
            raise RuntimeError("ffmpeg is required but not available")
    
    def resize_image(self, img_path, target_width, target_height, aspect_ratio="9:16"):
        """Resize image and save to a temporary location with white background padding."""
        try:
            filename = os.path.basename(img_path)
            resized_path = f"/tmp/images_resized/{uuid.uuid4()}_{filename}"
            
            img = Image.open(img_path)
            original_width, original_height = img.size
            
            if aspect_ratio == "9:16": 
                orig_aspect = original_width / original_height
                target_aspect = 9 / 16
                
                if orig_aspect > target_aspect:  
                    new_width = target_width
                    new_height = int(original_height * (new_width / original_width))
                else:  
                    new_height = target_height
                    new_width = int(original_width * (new_height / original_height))
            else:  
                orig_aspect = original_width / original_height
                target_aspect = 16 / 9
                
                if orig_aspect > target_aspect:  
                    new_width = target_width
                    new_height = int(original_height * (new_width / original_width))
                else:  
                    new_height = target_height
                    new_width = int(original_width * (new_height / original_height))
            
           
            new_width = min(new_width, target_width)
            new_height = min(new_height, target_height)
            
            img = img.resize((new_width, new_height), Image.LANCZOS)
            
            background = Image.new("RGB", (target_width, target_height), (255, 255, 255))
            
            position = ((target_width - new_width) // 2, (target_height - new_height) // 2)
            
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
            os.makedirs(output_path, exist_ok=True)
            
            valid_image_paths = [p for p in image_paths if not isinstance(p, Exception) and p is not None]
            
            if not valid_image_paths:
                raise ValueError("No valid image paths provided")
            
            valid_image_paths = [p for p in valid_image_paths if os.path.exists(p)]
            logger.info(f"Using {len(valid_image_paths)} valid images")
            
            if not valid_image_paths:
                raise ValueError("No valid image files found at the specified paths")

            if aspect_ratio == "9:16":  
                width, height = 720, 1280  
            else:  
                width, height = 1280, 720  
            
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
            
            image_list_path = f"{temp_dir}/image_list_{uuid.uuid4()}.txt"
            
            with open(image_list_path, 'w') as f:
                for img_path in resized_image_paths:
                    # Each image repeated based on image_duration and fps
                    # duration needs to be in seconds for -t option
                    f.write(f"file '{img_path}'\n")
                    f.write(f"duration {image_duration}\n")
         
                f.write(f"file '{resized_image_paths[-1]}'\n")
            
           
            timestamp = int(time.time())
            output_file = os.path.join(output_path, f"video_{timestamp}.mp4")
            
         
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
            
            subprocess.run(ffmpeg_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
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
