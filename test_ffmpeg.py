import os
import subprocess
import json
from PIL import Image
import uuid
import tempfile
import shutil

def test_ffmpeg_version():
    """Test that ffmpeg is installed and working."""
    try:
        result = subprocess.run(['ffmpeg', '-version'], 
                               stdout=subprocess.PIPE, 
                               stderr=subprocess.PIPE,
                               check=True)
        print(f"ffmpeg version: {result.stdout.decode('utf-8').splitlines()[0]}")
        return True
    except Exception as e:
        print(f"Error checking ffmpeg: {str(e)}")
        return False

def test_ffprobe():
    output_file = "/tmp/test_video.mp4"
    
    try:
        cmd = [
            'ffmpeg', '-y', '-f', 'lavfi', '-i', 'testsrc=duration=5:size=1280x720:rate=30', 
            '-c:v', 'libx264', '-pix_fmt', 'yuv420p', output_file
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Now test ffprobe
        probe_cmd = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json',
            '-show_format', '-show_streams', output_file
        ]
        result = subprocess.run(probe_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Parse the JSON output
        video_info = json.loads(result.stdout.decode('utf-8'))
        print(f"Video duration: {video_info['format']['duration']} seconds")
        print(f"Video size: {video_info['format']['size']} bytes")
        
        # Cleanup
        if os.path.exists(output_file):
            os.remove(output_file)
            
        return True
    except Exception as e:
        print(f"Error testing ffprobe: {str(e)}")
        if os.path.exists(output_file):
            os.remove(output_file)
        return False

def test_image_slideshow():
    """Test creating a simple slideshow with ffmpeg."""
    # Create some test images
    image_dir = "/tmp/test_images"
    output_file = "/tmp/test_slideshow.mp4"
    image_list_file = "/tmp/image_list.txt"
    
    os.makedirs(image_dir, exist_ok=True)
    
    try:
        # Create 3 test images
        image_paths = []
        for i in range(3):
            img = Image.new('RGB', (640, 480), color=(i*80, 100, 200))
            img_path = f"{image_dir}/image_{i}.jpg"
            img.save(img_path)
            image_paths.append(img_path)
        
        # Create image list file for ffmpeg
        with open(image_list_file, 'w') as f:
            for img_path in image_paths:
                f.write(f"file '{img_path}'\n")
                f.write(f"duration 1\n")
            # Add the last image again (required by ffmpeg)
            f.write(f"file '{image_paths[-1]}'\n")
        
        # Create slideshow
        cmd = [
            'ffmpeg', '-y',
            '-f', 'concat',
            '-safe', '0',
            '-i', image_list_file,
            '-c:v', 'libx264',
            '-pix_fmt', 'yuv420p',
            '-r', '30',
            output_file
        ]
        
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Verify the output file exists and has correct duration
        if os.path.exists(output_file):
            probe_cmd = [
                'ffprobe', '-v', 'quiet', '-print_format', 'json',
                '-show_format', output_file
            ]
            result = subprocess.run(probe_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            video_info = json.loads(result.stdout.decode('utf-8'))
            print(f"Slideshow duration: {video_info['format']['duration']} seconds")
            
            # Cleanup
            for img_path in image_paths:
                if os.path.exists(img_path):
                    os.remove(img_path)
            if os.path.exists(image_list_file):
                os.remove(image_list_file)
            if os.path.exists(output_file):
                os.remove(output_file)
            shutil.rmtree(image_dir, ignore_errors=True)
            
            return True
    except Exception as e:
        print(f"Error testing image slideshow: {str(e)}")
        # Cleanup
        shutil.rmtree(image_dir, ignore_errors=True)
        if os.path.exists(image_list_file):
            os.remove(image_list_file)
        if os.path.exists(output_file):
            os.remove(output_file)
        return False

if __name__ == "__main__":
    print("Testing ffmpeg functionality...")
    
    ffmpeg_ok = test_ffmpeg_version()
    print(f"ffmpeg installation test: {'PASSED' if ffmpeg_ok else 'FAILED'}")
    
    if ffmpeg_ok:
        ffprobe_ok = test_ffprobe()
        print(f"ffprobe test: {'PASSED' if ffprobe_ok else 'FAILED'}")
        
        slideshow_ok = test_image_slideshow()
        print(f"Slideshow test: {'PASSED' if slideshow_ok else 'FAILED'}")
        
    print("All tests completed.") 