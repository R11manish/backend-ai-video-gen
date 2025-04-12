import os
import json
import asyncio
import requests
from dotenv import load_dotenv
from serpapi.google_search import GoogleSearch
from langchain_deepseek import ChatDeepSeek
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()


class VideoGeneration:
    def __init__(self):
        api_key = os.getenv("DEEPSEEK_API_KEY")
        serpapi_key = os.getenv("SERPAPI_API_KEY")

        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY environment variable is not set")
        if not serpapi_key:
            raise ValueError("SERPAPI_API_KEY environment variable is not set")

        self.llm = ChatDeepSeek(
            temperature=0,
            model="deepseek-chat",
            api_key=api_key
        )
        self.serpapi_key = serpapi_key
        self.concept = None  # Initialize concept as None

    async def script(self, query: str):
        self.concept = query
        tool_prompt = ChatPromptTemplate.from_messages([
            ("system", "Generate a short 60 sec engaging paragraph on user query. Just return the paragraph only."),
            ("user", "{query}")
        ])

        script = await self.llm.ainvoke(tool_prompt.format(query=query))
        return script

    def search_images(self, num_results: int = 1):
        if self.concept is None:
            raise ValueError("Concept is not set. Please run script() first.")

        params = {
            "engine": "google_images",
            "q": self.concept,
            "api_key": self.serpapi_key,
            "num": num_results
        }

        search = GoogleSearch(params)
        results = search.get_dict()
        return results.get("images_results", [])

    def download_image(self, image_url: str, save_path: str = None, filename: str = None):
        if save_path is None:
            save_path = "./images"
            
        os.makedirs(save_path, exist_ok=True)
        
        if filename is None:
            url_filename = os.path.basename(image_url.split('?')[0])
            if url_filename and '.' in url_filename:
                filename = url_filename
            else:
                filename = f"image_{int(asyncio.get_event_loop().time())}.jpg"
        
        file_path = os.path.join(save_path, filename)
        
        response = requests.get(image_url, stream=True)
        if response.status_code == 200:
            with open(file_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return file_path
        else:
            raise Exception(f"Failed to download image: HTTP status code {response.status_code}")
    
    async def download_image_async(self, image_url: str, save_path: str = None, filename: str = None):
        """Asynchronous version of download_image using aiohttp"""
        import aiohttp
        
        if save_path is None:
            save_path = "./images"
            
        os.makedirs(save_path, exist_ok=True)
        
        if filename is None:
            url_filename = os.path.basename(image_url.split('?')[0])
            if url_filename and '.' in url_filename:
                filename = url_filename
            else:
                filename = f"image_{int(asyncio.get_event_loop().time())}.jpg"
        
        file_path = os.path.join(save_path, filename)
        
        async with aiohttp.ClientSession() as session:
            async with session.get(image_url) as response:
                if response.status == 200:
                    with open(file_path, "wb") as f:
                        f.write(await response.read())
                    return file_path
                else:
                    raise Exception(f"Failed to download image: HTTP status code {response.status}")
    
    async def download_all_images(self, image_list, save_path=None):
        """Download all images in the list in parallel"""
        download_tasks = []
        for i, image in enumerate(image_list[:12]):
            image_url = image.get("original")
            if image_url:
                task = self.download_image_async(
                    image_url=image_url,
                    save_path=save_path,
                    filename=f"image_{i}.jpg"
                )
                download_tasks.append(task)
        
        return await asyncio.gather(*download_tasks, return_exceptions=True)


if __name__ == "__main__":
    video = VideoGeneration()
    
    async def main():
        paragraph = await video.script("ronaldo")
        images = video.search_images(num_results=1) 
        if images and len(images) > 0:
            # Download all images in parallel
            downloaded_paths = await video.download_all_images(images)
            print(f"Downloaded {len([p for p in downloaded_paths if not isinstance(p, Exception)])} images successfully")
            for i, result in enumerate(downloaded_paths):
                if isinstance(result, Exception):
                    print(f"Error downloading image {i}: {result}")
                else:
                    print(f"Image {i} saved to: {result}")
        else:
            print("No images found.")
    
    asyncio.run(main())