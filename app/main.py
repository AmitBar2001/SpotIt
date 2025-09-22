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

# --- Configuration ---
# Create directories for temporary file storage
UPLOAD_DIR = Path("temp_uploads")
OUTPUT_DIR = Path("separated_output")
ZIP_DIR = Path("temp_zips")
DOWNLOAD_DIR = Path("temp_downloads")

for dir_path in [UPLOAD_DIR, OUTPUT_DIR, ZIP_DIR, DOWNLOAD_DIR]:
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
    """Sanitize a string to be safe for use as a directory or file name."""
    return re.sub(r"[^a-zA-Z0-9_\-\.]", "_", name)


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
    url: str, start_time: int, duration: int, download_path: Path
) -> Path:
    """Downloads audio from a YouTube URL and trims it using ffmpeg."""
    logger.info(
        f"Starting download_and_trim_youtube_audio for URL: {url}, start_time: {start_time}, duration: {duration}, download_path: {download_path}"
    )

    # yt-dlp options to download the best audio-only format
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": str(download_path),
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
        "cookiefile": COOKIES_FILE_PATH if os.path.exists(COOKIES_FILE_PATH) else None,
    }

    # Securely add proxy from environment variable if it exists
    proxy_url = os.environ.get("YT_DLP_PROXY")
    if proxy_url:
        ydl_opts["proxy"] = proxy_url
        logger.info("Using proxy for yt-dlp.")

    try:
        logger.debug(f"yt_dlp options: {ydl_opts}")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        logger.info(f"Downloaded audio to {download_path.with_suffix('.wav')}")
    except Exception as e:
        logger.error(f"Failed to download audio from YouTube: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to download audio from YouTube: {e}"
        )

    original_audio_path = download_path.with_suffix(".wav")
    trimmed_audio_path = download_path.parent / f"trimmed_{download_path.stem}.wav"

    # Use ffmpeg to trim the audio
    # The command is: ffmpeg -ss [start_time] -i [input_file] -t [duration] -c copy [output_file]
    try:
        subprocess.run(
            [
                "ffmpeg",
                "-ss",
                str(start_time),
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
    start_time: int = Query(
        0, ge=0, description="Start time in seconds for the audio clip."
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
            str(request.url), start_time, duration, DOWNLOAD_DIR / "temp"
        )
        # Use the trimmed file's stem (which is the video title) for directory naming
        dir_name = sanitize_filename(trimmed_audio_path.stem.replace("trimmed_", ""))
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
            cleanup_files(trimmed_audio_path, temp_output_path)
            raise HTTPException(status_code=500, detail=f"Object storage error: {e}")

        # Cleanup in background
        if background_tasks is not None:
            background_tasks.add_task(
                cleanup_files, trimmed_audio_path, temp_output_path
            )
            logger.info(
                f"Scheduled cleanup for: {trimmed_audio_path}, {temp_output_path}"
            )

        return {"urls": urls}
    except Exception as e:
        logger.error(f"Error processing YouTube URL {request.url}: {e}")
        cleanup_files(trimmed_audio_path, temp_output_path)
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

        base_name = sanitize_filename(Path(file.filename).stem)
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


# --- yt-dlp Cookies Handling ---
COOKIES_FILE_PATH = "yt_dlp_cookies.txt"
cookies_content = os.environ.get("YT_DLP_COOKIES")
if cookies_content and not os.path.exists(COOKIES_FILE_PATH):
    with open(COOKIES_FILE_PATH, "w") as f:
        f.write(cookies_content)
    logger.info(f"Wrote yt-dlp cookies to {COOKIES_FILE_PATH}")
else:
    if cookies_content:
        logger.info(
            f"YT_DLP_COOKIES environment variable found but {COOKIES_FILE_PATH} already exists; not overwriting."
        )
    else:
        logger.info(
            "No YT_DLP_COOKIES environment variable found; not writing cookies file."
        )
