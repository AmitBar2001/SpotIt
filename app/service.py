from pathlib import Path
from fastapi import HTTPException
from pydantic import HttpUrl, BaseModel
import asyncio
import httpx

from app.files import cleanup_files, merge_stems_and_export, run_demucs_separation, sanitize_filename
from app.s3 import upload_and_get_presigned_urls
from app.logger import logger
from app import s3
from app.spotify import get_random_track_from_playlist
from app.youtube import download_and_trim_youtube_audio
from app.schema import TaskStatusUpdate, UpdateTaskBody, SongMetadata
from app.config import settings

# --- Configuration ---
# Create directories for temporary file storage
UPLOAD_DIR = Path("temp_uploads")
OUTPUT_DIR = Path("separated_output")
DOWNLOAD_DIR = Path("temp_downloads")

for dir_path in [UPLOAD_DIR, OUTPUT_DIR, DOWNLOAD_DIR]:
    dir_path.mkdir(exist_ok=True)

async def update_task_status(url: str, data: BaseModel):
    async with httpx.AsyncClient() as client:
        try:
            # Pydantic v1 uses .dict()
            response = await client.post(url, json=data.dict(), headers={"x-api-key": settings.callback_api_key})
            response.raise_for_status()
            logger.info(f"Callback sent to {url}: {response.status_code}")
        except Exception as e:
            logger.error(f"Failed to send callback to {url}: {e}")

async def process_link_separation_task(
    url: HttpUrl,
    start_time: int | None,
    duration: int,
    callback_url: HttpUrl,
):
    trimmed_audio_path = None
    temp_output_path = None
    callback_url_str = str(callback_url)
    loop = asyncio.get_running_loop()

    # Initial Status
    asyncio.create_task(update_task_status(callback_url_str, TaskStatusUpdate(status="pending", message="Task started")))

    try:
        url_str = str(url)
        logger.info(f"Processing task for {url_str}")

        # Download
        # Using asyncio.to_thread for blocking download
        def _download():
             # Spotify detection logic moved here to ensure thread safety if needed, 
             # though strictly not required if get_random_track_from_playlist is sync and safe.
             # However, we need to modify search term based on it.
             _search_term = None
             if "spotify.com" in url_str:
                logger.info(f"Detected Spotify link: {url_str}")
                try:
                    asyncio.run_coroutine_threadsafe(
                        update_task_status(callback_url_str, TaskStatusUpdate(status="in_progress", message="Searching Spotify track")),
                        loop
                    )
                    track = get_random_track_from_playlist(url_str)
                    track_name = track["name"]
                    track_artist = track["artists"][0]["name"]
                    logger.info(f"Selected track: {track_name} by {track_artist}")
                    _search_term = f"{track_artist} - {track_name}"
                except Exception as e:
                    logger.error(f"Failed to fetch track from Spotify: {e}")
                    raise HTTPException(
                        status_code=500, detail=f"Failed to fetch track from Spotify: {e}"
                    )
             
             asyncio.run_coroutine_threadsafe(
                 update_task_status(callback_url_str, TaskStatusUpdate(status="in_progress", message="Downloading audio from YouTube")),
                 loop
             )
        
             return download_and_trim_youtube_audio(
                url_str, start_time, duration, DOWNLOAD_DIR, _search_term
             )

        trimmed_audio_path, video_info = await asyncio.to_thread(_download)
        
        asyncio.create_task(update_task_status(callback_url_str, TaskStatusUpdate(status="in_progress", message="Separating audio")))

        # ... Setup paths ...
        if trimmed_audio_path.stem.startswith("trimmed_"):
            video_title = trimmed_audio_path.stem.replace("trimmed_", "")
        else:
            video_title = trimmed_audio_path.stem
        dir_name = sanitize_filename(video_title)
        temp_output_path = OUTPUT_DIR / dir_name
        
        logger.info(f"Using output directory: {temp_output_path}")

        # Separation
        separated_files_dir = await asyncio.to_thread(
            run_demucs_separation, trimmed_audio_path, temp_output_path
        )

        asyncio.create_task(update_task_status(callback_url_str, TaskStatusUpdate(status="in_progress", message="Merging and Uploading")))

        # Merge
        mp3s = await asyncio.to_thread(
            merge_stems_and_export, separated_files_dir, trimmed_audio_path, temp_output_path
        )

        # Upload
        valid_mp3s = [f for f in mp3s.values() if f]
        urls = await asyncio.to_thread(
            upload_and_get_presigned_urls, valid_mp3s, temp_output_path.name
        )

        # Map filenames to schema keys
        file_key_mapping = {
            "drums.mp3": "drums",
            "drums_bass.mp3": "bass",
            "drums_bass_guitar.mp3": "guitar",
            "drums_bass_guitar_other_piano.mp3": "other",
            "original_trimmed.mp3": "original"
        }

        final_urls = {}
        for filename, key in file_key_mapping.items():
            if filename in urls:
                final_urls[key] = urls[filename]
            else:
                # If not in urls, it might be because it was silent (None in mp3s) or failed upload
                # In either case, we can set it to None if that's the desired behavior for "missing" files
                final_urls[key] = None

        # Construct Metadata
        metadata = SongMetadata(
            title=video_info.get("title", "Unknown Title"),
            artists=[video_info.get("artist") or video_info.get("uploader") or "Unknown Artist"],
            album=video_info.get("album") or "Unknown Album",
            duration=int(video_info.get("duration", 0)),
            youtube_views=int(video_info.get("view_count", 0)),
            year=int(video_info.get("upload_date")[:4]) if video_info.get("upload_date") else 0
        )

        # Final Success Callback
        result_body = UpdateTaskBody(
            task_status=TaskStatusUpdate(status="completed", message="Process complete"),
            song_metadata=metadata,
            file_keys=final_urls 
        )
        
        asyncio.create_task(update_task_status(callback_url_str, result_body))
        
        # Cleanup
        if trimmed_audio_path and temp_output_path:
             cleanup_files(trimmed_audio_path, temp_output_path)

    except Exception as e:
        logger.error(f"Task failed: {e}")
        asyncio.create_task(update_task_status(callback_url_str, TaskStatusUpdate(status="failed", message=str(e))))
        # Only cleanup if paths were assigned
        if trimmed_audio_path or temp_output_path:
             cleanup_files(trimmed_audio_path, temp_output_path)

def list_bucket_directories(directory: str | None):
    return s3.list_directories(directory)