import unittest
import os
import shutil
from pathlib import Path
from app.youtube import download_and_trim_youtube_audio
from app.config import settings

class TestYouTubeSearch(unittest.TestCase):
    def setUp(self):
        self.download_path = Path("tests/temp_test_search_download")
        if self.download_path.exists():
            shutil.rmtree(self.download_path)
        self.download_path.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        if self.download_path.exists():
            shutil.rmtree(self.download_path)

    def test_download_and_trim_by_search(self):
        # Use a search term
        test_search = "Baby Shark Pinkfong"
        duration = 5
        
        trimmed_path, info = download_and_trim_youtube_audio(
            url="",
            start_time=0,
            duration=duration,
            download_path=self.download_path,
            search_term=test_search
        )
        
        self.assertTrue(trimmed_path.exists(), f"Trimmed file {trimmed_path} does not exist")
        self.assertTrue(os.path.getsize(trimmed_path) > 0, "Trimmed file is empty")
        self.assertEqual(trimmed_path.suffix, ".wav", "Output should be a .wav file")
        self.assertIn("title", info, "Video info should contain 'title'")

if __name__ == "__main__":
    unittest.main()
