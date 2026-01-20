import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from app.logger import logger
from app.config import settings
import random
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry


# Authenticate with Client Credentials Flow
# Configure retry strategy to handle ReadTimeouts
retry_strategy = Retry(
    total=3,
    backoff_factor=0.3,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["HEAD", "GET", "OPTIONS", "POST", "PUT", "DELETE"],
    read=3,  # Enable retries for ReadTimeout errors
)
session = requests.Session()
adapter = HTTPAdapter(max_retries=retry_strategy)
session.mount("https://", adapter)
session.mount("http://", adapter)

sp = spotipy.Spotify(
    auth_manager=SpotifyClientCredentials(
        client_id=settings.spotify_client_id,
        client_secret=settings.spotify_client_secret,
    ),
    requests_session=session,
    requests_timeout=15,
)


def get_random_track_from_playlist(playlist_url_or_id):
    """Fetches a random track from a given Spotify playlist efficiently."""

    # 1. Extract the playlist ID from the URL if a URL is provided
    if "spotify.com/playlist/" in playlist_url_or_id:
        playlist_id = playlist_url_or_id.split("/")[-1].split("?")[0]
    else:
        playlist_id = playlist_url_or_id  # Assume it's already an ID

    logger.info(f"Fetching random track from playlist ID: {playlist_id}")

    try:
        # 2. Get the total number of tracks
        response = sp.playlist_tracks(playlist_id, fields="total", limit=1)
        if not response:
             logger.error("Failed to fetch playlist details.")
             raise ValueError("Failed to fetch playlist details.")
        
        total_tracks = response["total"]

        if total_tracks == 0:
            logger.error("No tracks found in the playlist.")
            raise ValueError("No tracks found in the playlist.")

        logger.info(f"Total tracks in playlist: {total_tracks}")

        # Retry logic in case we hit a local/null track
        max_retries = 5
        for _ in range(max_retries):
            # 3. Pick a random index
            random_offset = random.randint(0, total_tracks - 1)
            # logger.info(f"Selected random offset: {random_offset}")

            # 4. Fetch the specific track
            # Fetching specific fields to minimize data transfer
            fields = "items(track(name,artists(name),album(name,images(url),release_date),duration_ms))"
            response = sp.playlist_tracks(
                playlist_id, fields=fields, limit=1, offset=random_offset
            )

            if not response:
                logger.warning(
                    f"No response from Spotify at offset {random_offset}, retrying..."
                )
                continue

            items = response.get("items", [])
            if not items:
                continue

            track_item = items[0]
            track = track_item.get("track")

            if track:
                return track

            logger.warning(
                f"Track at offset {random_offset} was None (likely local file), retrying..."
            )

        raise ValueError("Failed to find a valid track after multiple attempts.")

    except Exception as e:
        logger.error(f"Error getting random track: {e}")
        raise


def search_spotify_track(query):
    """Searches for a track on Spotify."""
    logger.info(f"Searching Spotify for: {query}")
    results = sp.search(q=query, type="track", limit=1)
    items = results["tracks"]["items"]
    if not items:
        return None
    return items[0]


# Example: Replace with your playlist link
PLAYLIST_LINK = (
    "https://open.spotify.com/playlist/324VWVYDNw9wQgBPboPNHh?si=5a97d8809c3f4940"
)
