import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from app.logger import logger
from app.config import settings
import random
import functools


# Authenticate with Client Credentials Flow
sp = spotipy.Spotify(
    auth_manager=SpotifyClientCredentials(
        client_id=settings.spotify_client_id,
        client_secret=settings.spotify_client_secret,
    )
)


@functools.lru_cache(maxsize=5)
def __get_tracks_from_playlist(playlist_url_or_id):
    """Fetches all tracks from a given Spotify playlist."""

    # 1. Extract the playlist ID from the URL if a URL is provided
    if "spotify.com/playlist/" in playlist_url_or_id:
        playlist_id = playlist_url_or_id.split("/")[-1].split("?")[0]
    else:
        playlist_id = playlist_url_or_id  # Assume it's already an ID

    logger.info(f"Fetching tracks from playlist ID: {playlist_id}")

    tracks = []
    # Spotify API limits results to 100, so you need to loop for large playlists
    results = sp.playlist_tracks(playlist_id)
    tracks.extend(results["items"])

    logger.info(f"Fetched {len(results['items'])} tracks from playlist {playlist_id}.")

    # Handle pagination for playlists with more than 100 songs
    while results["next"]:
        logger.info(f"Fetching next page of tracks for playlist {playlist_id}...")
        results = sp.next(results)
        tracks.extend(results["items"])

    logger.info(f"Total tracks fetched: {len(tracks)}")

    return tracks
    # # Extract the song title and artist
    # song_list = []
    # for item in tracks:
    #     track = item['track']
    #     if track: # Check if the track object is not None (e.g., local files might be)
    #         artist = track['artists'][0]['name']
    #         title = track['name']
    #         song_list.append((title, artist))

    # return song_list


def get_random_track_from_playlist(playlist_url_or_id):
    tracks = __get_tracks_from_playlist(playlist_url_or_id)

    if not tracks:
        logger.error("No tracks found in the playlist.")
        raise ValueError("No tracks found in the playlist.")

    return random.choice(tracks)["track"]


# Example: Replace with your playlist link
PLAYLIST_LINK = (
    "https://open.spotify.com/playlist/324VWVYDNw9wQgBPboPNHh?si=5a97d8809c3f4940"
)
