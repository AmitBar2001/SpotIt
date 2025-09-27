import shutil
import subprocess
import os
from pathlib import Path
from fastapi import FastAPI, File, UploadFile, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, HttpUrl
import yt_dlp
import re
from app.files import merge_stems_and_export, run_demucs_separation
from app.s3 import upload_and_get_presigned_urls, S3UploadError, S3PresignedUrlError
from app.logger import logger
from app import s3
from app.config import settings

# --- Configuration ---
# Create directories for temporary file storage
UPLOAD_DIR = Path("temp_uploads")
OUTPUT_DIR = Path("separated_output")
DOWNLOAD_DIR = Path("temp_downloads")

for dir_path in [UPLOAD_DIR, OUTPUT_DIR, DOWNLOAD_DIR]:
    dir_path.mkdir(exist_ok=True)


# --- Pydantic Models ---
class YouTubeLinkRequest(BaseModel):
    url: HttpUrl


# --- FastAPI App Initialization ---
app = FastAPI(
    title="Demucs Audio Separator",
    description="An API to separate audio files into their instrumental stems (drums, bass, vocals, other) using the Demucs model. Can process direct file uploads or audio from YouTube links.",
    version="1.1.0",
)


# --- Helper Functions ---
def sanitize_filename(name: str) -> str:
    """Sanitize a string to be safe for use as a directory or file name, allowing Unicode (including Hebrew) characters."""
    # Allow Unicode letters, numbers, underscore, dash, and dot
    # u0590-u05FFFF covers all Unicode code points
    return re.sub(r"[^\w\-\.\u0590-\u05FF]", "_", name, flags=re.UNICODE)


def cleanup_files(*paths):
    """Removes files and directories to free up space after processing."""
    for path in paths:
        try:
            if path is None:
                logger.debug("cleanup_files: Skipping None path.")
                continue
            if path.is_dir():
                shutil.rmtree(path)
                logger.info(f"Removed directory: {path}")
            elif path.exists():
                path.unlink()
                logger.info(f"Removed file: {path}")
            else:
                logger.debug(f"cleanup_files: Path does not exist: {path}")
        except Exception as e:
            logger.error(f"Error cleaning up {path}: {e}")


# --- Business Logic Functions ---


def download_and_trim_youtube_audio(
    url: str, start_time: int | None, duration: int, download_path: Path
) -> Path:
    """Downloads audio from a YouTube URL and trims it using ffmpeg. If start_time is None, auto-pick using heatmap."""
    logger.info(
        f"Starting download_and_trim_youtube_audio for URL: {url}, start_time: {start_time}, duration: {duration}, download_path: {download_path}"
    )

    # Use yt-dlp template to get video title as filename (safe)
    # We'll use download_path as the directory, and let yt-dlp set the filename
    outtmpl = str(download_path / "%(title)s.%(ext)s")
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": outtmpl,
        "noplaylist": True,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "wav",  # Demucs works well with wav
            }
        ],
        "logger": logger,
        "external_downloader": "aria2c",
        "postprocessor_args": ["-ar", "44100", "-ac", "2"],  # Ensure 44.1kHz, stereo
        "cookiefile": (
            settings.yt_dlp_cookies_file_path
            if os.path.exists(settings.yt_dlp_cookies_file_path)
            else None
        ),
        "writesubtitles": False,
        "writeinfojson": True,  # Download info JSON
        "keepvideo": False,
    }

    if settings.yt_dlp_proxy is not None:
        ydl_opts["proxy"] = settings.yt_dlp_proxy
        logger.info("Using proxy for yt-dlp.")

    try:
        logger.debug(f"yt_dlp options: {ydl_opts}")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            video_info_json = ydl.extract_info(url, download=True)

        if not video_info_json:
            logger.error("yt-dlp did not return video info.")
            raise Exception("yt-dlp did not return video info.")

        # Find the downloaded file path
        title = video_info_json.get("title")

        if not title:
            logger.error("Could not extract video title from yt-dlp info.")
            raise Exception("Could not extract video title from yt-dlp info.")

        original_audio_path = download_path / f"{title}.wav"
        logger.info(f"Downloaded audio to {original_audio_path}")
    except Exception as e:
        logger.error(f"Failed to download audio from YouTube: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to download audio from YouTube: {e}"
        )

    # If start_time is None, auto-pick using heatmap
    auto_start_time = None

    if start_time is None:
        try:
            heatmap = video_info_json.get("heatmap")
            if not heatmap or len(heatmap) < 4:
                raise Exception("No or insufficient heatmap data in info JSON.")
            # Exclude the first interval (starts at 0)
            intervals = heatmap[1:]

            # Find window of 3 consecutive intervals with highest average value
            max_avg = -1
            max_idx = 0
            for i in range(len(intervals) - 2):
                avg = sum(intervals[j]["value"] for j in range(i, i + 3)) / 3
                if avg > max_avg:
                    max_avg = avg
                    max_idx = i

            # Start time is 10 seconds before the start of the best window
            best_start = int(intervals[max_idx]["start_time"])
            auto_start_time = max(0, best_start - 10)
            logger.info(f"Auto-picked start_time from heatmap: {auto_start_time}")
        except Exception as e:
            logger.error(f"Failed to auto-pick start_time from heatmap: {e}")
            auto_start_time = 0
    else:
        auto_start_time = start_time

    trimmed_audio_path = download_path / f"trimmed_{original_audio_path.stem}.wav"

    # TODO: check if replacing this with "--download-sections" in yt-dlp would work faster
    # Use ffmpeg to trim the audio
    # The command is: ffmpeg -ss [start_time] -i [input_file] -t [duration] -c [output_file]
    try:
        subprocess.run(
            [
                "ffmpeg",
                "-ss",
                str(auto_start_time),
                "-i",
                str(original_audio_path),
                "-t",
                str(duration),
                "-c:a",
                "pcm_s16le",
                "-y",
                "-loglevel",
                "error",
                str(trimmed_audio_path),
            ],
            check=True,
            capture_output=True,
        )
        logger.info(f"Trimmed audio saved to {trimmed_audio_path}")
    except subprocess.CalledProcessError as e:
        cleanup_files(original_audio_path)
        error_message = e.stderr.decode()
        logger.error(f"Failed to trim audio with ffmpeg: {error_message}")
        raise HTTPException(
            status_code=500, detail=f"Failed to trim audio with ffmpeg: {error_message}"
        )

    # Clean up the original full download
    cleanup_files(original_audio_path)

    return trimmed_audio_path


# --- API Endpoints ---
@app.get(
    "/",
    summary="Root Endpoint",
    description="A simple root endpoint to check if the service is running.",
)
async def root():
    logger.info("Root endpoint called")
    return {"message": "Welcome to the Demucs Audio Separator API."}


@app.post(
    "/separate-from-youtube/",
    summary="Separate Audio from YouTube",
    description="Provide a YouTube URL and get separated audio stems.",
)
def separate_from_youtube(
    request: YouTubeLinkRequest,
    start_time: int | None = Query(
        None,
        ge=0,
        description="Start time in seconds for the audio clip. If not specified, will be auto-picked using the heatmap.",
    ),
    duration: int = Query(
        30, gt=0, le=300, description="Duration of the audio clip in seconds (max 300)."
    ),
    background_tasks: BackgroundTasks = None,
):
    trimmed_audio_path = None
    temp_output_path = None
    try:
        logger.info(
            f"Received YouTube separation request: url={request.url}, start_time={start_time}, duration={duration}"
        )

        # Download and trim audio
        trimmed_audio_path = download_and_trim_youtube_audio(
            str(request.url), start_time, duration, DOWNLOAD_DIR
        )
        # The original audio file is named after the video title, so get the title from the trimmed file name
        if trimmed_audio_path.stem.startswith("trimmed_"):
            video_title = trimmed_audio_path.stem.replace("trimmed_", "")
        else:
            video_title = trimmed_audio_path.stem
        logger.debug(f"Extracted video title: {video_title}")
        # Sanitize title for directory name
        dir_name = sanitize_filename(video_title)
        logger.debug(f"Sanitized directory name: {dir_name}")
        temp_output_path = OUTPUT_DIR / dir_name

        logger.info(f"Using output directory: {temp_output_path}")

        separated_files_dir = run_demucs_separation(
            trimmed_audio_path, temp_output_path
        )
        logger.info(f"Demucs separation complete. Output at: {separated_files_dir}")

        mp3s = merge_stems_and_export(
            separated_files_dir, trimmed_audio_path, temp_output_path
        )
        logger.info(f"Stems merged and exported as mp3s: {list(mp3s.keys())}")

        # Upload to S3/OCI and get presigned URLs
        logger.info(
            f"Uploading merged mp3s to object storage from {temp_output_path}..."
        )
        try:
            urls = upload_and_get_presigned_urls(temp_output_path)
            logger.info(f"Uploaded mp3s to object storage. Presigned URLs: {urls}")
        except (S3UploadError, S3PresignedUrlError) as e:
            logger.error(
                f"Object storage upload or presigned URL generation failed: {e}"
            )
            cleanup_files(trimmed_audio_path, temp_output_path, trimmed_audio_path.replace(".wav", ".info.json"))
            raise HTTPException(status_code=500, detail=f"Object storage error: {e}")

        # Cleanup in background
        if background_tasks is not None:
            background_tasks.add_task(
                cleanup_files, trimmed_audio_path, temp_output_path, trimmed_audio_path.replace(".wav", ".info.json")
            )
            logger.info(
                f"Scheduled cleanup for: {trimmed_audio_path}, {temp_output_path}"
            )

        return {"urls": urls}
    except Exception as e:
        logger.error(f"Error processing YouTube URL {request.url}: {e}")
        cleanup_files(trimmed_audio_path, temp_output_path, trimmed_audio_path.replace(".wav", ".info.json"))
        raise


@app.post(
    "/separate-from-file/",
    summary="Separate Audio from File",
    description="Upload an audio file to separate it into stems.",
)
def separate_from_file(
    file: UploadFile = File(...), background_tasks: BackgroundTasks = None
):
    supported_formats = [".mp3", ".wav", ".flac", ".ogg"]
    temp_upload_path = None
    temp_output_path = None
    try:
        logger.info(f"Received file separation request: filename={file.filename}")

        if Path(file.filename).suffix.lower() not in supported_formats:
            logger.warning(f"Unsupported file format: {file.filename}")
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file format. Supported: {', '.join(supported_formats)}",
            )

        logger.debug(f"input file name: {Path(file.filename).stem}")
        # Sanitize filename for safe storage
        base_name = sanitize_filename(Path(file.filename).stem)
        logger.debug(f"Sanitized base name: {base_name}")
        temp_upload_path = UPLOAD_DIR / f"{base_name}_{file.filename}"
        temp_output_path = OUTPUT_DIR / base_name

        logger.info(f"Saving uploaded file to: {temp_upload_path}")
        with temp_upload_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        logger.info(f"Running Demucs separation for: {temp_upload_path}")
        separated_files_dir = run_demucs_separation(temp_upload_path, temp_output_path)
        logger.info(f"Demucs separation complete. Output at: {separated_files_dir}")

        mp3s = merge_stems_and_export(
            separated_files_dir, temp_upload_path, temp_output_path
        )
        logger.info(f"Stems merged and exported as mp3s: {list(mp3s.keys())}")

        logger.info(
            f"Uploading merged mp3s to object storage from {temp_output_path}..."
        )
        try:
            urls = upload_and_get_presigned_urls(temp_output_path)
            logger.info(f"Uploaded mp3s to object storage. Presigned URLs: {urls}")
        except (S3UploadError, S3PresignedUrlError) as e:
            logger.error(
                f"Object storage upload or presigned URL generation failed: {e}"
            )
            cleanup_files(temp_upload_path, temp_output_path)
            raise HTTPException(status_code=500, detail=f"Object storage error: {e}")

        if background_tasks is not None:
            background_tasks.add_task(cleanup_files, temp_upload_path, temp_output_path)
            logger.info(
                f"Scheduled cleanup for: {temp_upload_path}, {temp_output_path}"
            )

        return {"urls": urls}
    except Exception as e:
        logger.error(f"Error processing file upload {file.filename}: {e}")
        cleanup_files(temp_upload_path, temp_output_path)
        raise


@app.get(
    "/list-directories/",
    summary="List Directories in Bucket",
    description="Lists all directories in the mp3files bucket or objects inside a specific directory.",
)
def list_directories(
    directory: str | None = Query(
        None,
        description="The directory to list objects from. If not specified, lists all directories.",
    )
):
    return s3.list_directories(directory)
