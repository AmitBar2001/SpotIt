import unittest
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env in the project root
ROOT_DIR = Path(__file__).parent.parent
load_dotenv(dotenv_path=ROOT_DIR / ".env")

from app.spotify import search_spotify_track, get_random_track_from_playlist

class TestSpotify(unittest.TestCase):
    def test_search_spotify_track(self):
        # A well-known track
        query = "Never Gonna Give You Up Rick Astley"
        track = search_spotify_track(query)
        self.assertIsNotNone(track)
        self.assertEqual(track['name'], "Never Gonna Give You Up")
        self.assertEqual(track['artists'][0]['name'], "Rick Astley")

    def test_get_random_track_from_playlist(self):
        # Using the example playlist from app/spotify.py
        playlist_id = "324VWVYDNw9wQgBPboPNHh"
        track = get_random_track_from_playlist(playlist_id)
        self.assertIsNotNone(track)
        self.assertIn('name', track)
        self.assertIn('artists', track)

if __name__ == "__main__":
    unittest.main()
