
import asyncio
import os
from pathlib import Path
from app.youtube import download_and_trim_youtube_audio

async def test_download():
    # Use a search term instead of a direct URL
    test_search = "Baby Shark Pinkfong"
    download_path = Path("temp_test_download")
    
    # KEEP cookies for this test since ios/web might need them
    cookie_path = Path("yt_dlp_cookies.txt")
    
    # Temporarily bypass proxy for this local test
    from app.config import settings
    old_proxy = settings.yt_dlp_proxy
    settings.yt_dlp_proxy = None

    print(f"Testing download with search term: {test_search} (NO PROXY)")
    try:
        trimmed_path, info = download_and_trim_youtube_audio(
            url="",
            start_time=0,
            duration=5,
            download_path=download_path,
            search_term=test_search
        )
        print(f"Success! File downloaded and trimmed to: {trimmed_path}")
        print(f"File size: {os.path.getsize(trimmed_path)} bytes")
        
        # Cleanup
        if trimmed_path.exists():
            os.remove(trimmed_path)
        if download_path.exists():
            for f in download_path.iterdir():
                os.remove(f)
            download_path.rmdir()
            
    except Exception as e:
        print(f"Test failed: {e}")
    finally:
        settings.yt_dlp_proxy = old_proxy




if __name__ == "__main__":
    asyncio.run(test_download())
