import uuid
import shutil
import zipfile
import subprocess
import logging
import os
from pathlib import Path
from fastapi import FastAPI, File, UploadFile, HTTPException, Query, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel, HttpUrl
from demucs.separate import main as demucs_separate
import yt_dlp
import glob

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

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

def download_and_trim_youtube_audio(url: str, start_time: int, duration: int, download_path: Path) -> Path:
    """Downloads audio from a YouTube URL and trims it using ffmpeg."""
    logger.info(f"Starting download_and_trim_youtube_audio for URL: {url}, start_time: {start_time}, duration: {duration}, download_path: {download_path}")
    
    # yt-dlp options to download the best audio-only format
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': str(download_path),
        'noplaylist': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'wav', # Demucs works well with wav
        }],
        'logger': logger,
        'external_downloader': 'aria2c',
        'postprocessor_args': ['-ar', '44100', '-ac', '2'], # Ensure 44.1kHz, stereo
        'cookies': COOKIES_FILE_PATH if os.path.exists(COOKIES_FILE_PATH) else None,
    }

    # Securely add proxy from environment variable if it exists
    proxy_url = os.environ.get("YT_DLP_PROXY")
    if proxy_url:
        ydl_opts['proxy'] = proxy_url
        logger.info("Using proxy for yt-dlp.")

    try:
        logger.debug(f"yt_dlp options: {ydl_opts}")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        logger.info(f"Downloaded audio to {download_path.with_suffix('.wav')}")
    except Exception as e:
        logger.error(f"Failed to download audio from YouTube: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to download audio from YouTube: {e}")

    original_audio_path = download_path.with_suffix('.wav')
    trimmed_audio_path = download_path.parent / f"trimmed_{download_path.stem}.wav"

    # Use ffmpeg to trim the audio
    # The command is: ffmpeg -ss [start_time] -i [input_file] -t [duration] -c copy [output_file]
    try:
        subprocess.run(
            [
                "ffmpeg",
                "-ss", str(start_time),
                "-i", str(original_audio_path),
                "-t", str(duration),
                "-c:a", "pcm_s16le",
                "-y",
                "-loglevel", "error",
                str(trimmed_audio_path)
            ],
            check=True, capture_output=True
        )
        logger.info(f"Trimmed audio saved to {trimmed_audio_path}")
    except subprocess.CalledProcessError as e:
        cleanup_files(original_audio_path)
        error_message = e.stderr.decode()
        logger.error(f"Failed to trim audio with ffmpeg: {error_message}")
        raise HTTPException(status_code=500, detail=f"Failed to trim audio with ffmpeg: {error_message}")
    
    # Clean up the original full download
    cleanup_files(original_audio_path)
    
    return trimmed_audio_path

def run_demucs_separation(audio_path: Path, output_path: Path) -> Path:
    """Runs the Demucs separation process on a given audio file."""
    model_name = "htdemucs_6s"
    try:
        demucs_args = [
            "-d", "cpu",  # Use CPU for processing
            f"--out={str(output_path)}",
            f"--name={model_name}",
            "--shifts", "2", # Use 2 shifts for better quality
            str(audio_path)
        ]
        logger.info(f"Running Demucs on {audio_path} with output {output_path}")
        logger.debug(f"Demucs args: {demucs_args}")
        demucs_separate(demucs_args)
        logger.info(f"Demucs separation completed for {audio_path}")
    except Exception as e:
        logger.error(f"An error occurred during Demucs processing: {e}")
        raise HTTPException(status_code=500, detail=f"An error occurred during Demucs processing: {e}")

    separated_files_dir = output_path / model_name / Path(audio_path.stem)
    if not separated_files_dir.exists() or not any(separated_files_dir.iterdir()):
        logger.error("Audio separation failed. No output files were generated.")
        raise HTTPException(status_code=500, detail="Audio separation failed. No output files were generated.")

    logger.debug(f"Separated files directory: {separated_files_dir}")
    logger.debug(f"Separated files: {list(separated_files_dir.glob('*'))}")
    return separated_files_dir


def merge_stems_and_export(stems_dir: Path, trimmed_audio_path: Path, output_dir: Path):
    """
    Merges stems as requested and exports them as mp3 files.
    Returns a dict of {label: mp3_path}.
    """
    # Map stem names to files
    logger.info(f"Merging stems in {stems_dir} and exporting to {output_dir}")
    stem_files = {stem.stem: stem for stem in stems_dir.glob("*.wav")}
    logger.debug(f"Found stem files: {stem_files}")
    # Demucs 6s stem order: drums, bass, vocals, other, guitar, piano
    # We'll use the actual file names to be robust
    get = lambda name: next((f for s, f in stem_files.items() if name in s), None)

    drums = get("drums")
    bass = get("bass")
    guitar = get("guitar")
    other = get("other")
    piano = get("piano")
    # vocals = get("vocals")  # Not used in your requested mixes

    outputs = {}

    def ffmpeg_merge(inputs, outname):
        outpath = output_dir / outname
        cmd = [
            "ffmpeg",
            *sum([["-i", str(f)] for f in inputs], []),
            "-filter_complex",
            f"amix=inputs={len(inputs)}:duration=longest:dropout_transition=0",
            "-c:a", "libmp3lame",
            "-q:a", "2",
            "-y",
            str(outpath)
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        return outpath

    # 1. Drums only
    if drums:
        outputs["drums.mp3"] = ffmpeg_merge([drums], "drums.mp3")
    # 2. Drums + Bass
    if drums and bass:
        outputs["drums_bass.mp3"] = ffmpeg_merge([drums, bass], "drums_bass.mp3")
    # 3. Drums + Bass + Guitar
    if drums and bass and guitar:
        outputs["drums_bass_guitar.mp3"] = ffmpeg_merge([drums, bass, guitar], "drums_bass_guitar.mp3")
    # 4. Drums + Bass + Guitar + Other + Piano
    merged = [f for f in [drums, bass, guitar, other, piano] if f]
    if len(merged) >= 2:
        outputs["drums_bass_guitar_other_piano.mp3"] = ffmpeg_merge(merged, "drums_bass_guitar_other_piano.mp3")
    # 5. Original trimmed mp3
    # Convert trimmed wav to mp3
    orig_mp3 = output_dir / "original_trimmed.mp3"
    subprocess.run([
        "ffmpeg", "-i", str(trimmed_audio_path),
        "-c:a", "libmp3lame", "-q:a", "2", "-y", str(orig_mp3)
    ], check=True, capture_output=True)
    outputs["original_trimmed.mp3"] = orig_mp3

    return outputs

def zip_merged_mp3s(mp3s: dict, zip_path: Path):
    """Zips the merged mp3s and returns the path to the zip file."""
    logger.info(f"Zipping merged mp3s to {zip_path}")
    logger.debug(f"MP3s to zip: {mp3s}")
    try:
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for name, mp3_path in mp3s.items():
                zipf.write(mp3_path, arcname=name)
        logger.info(f"Created zip file {zip_path}")
    except Exception as e:
        logger.error(f"Failed to create zip file {zip_path}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create zip file: {e}")

    return FileResponse(
        path=zip_path,
        media_type='application/zip',
        filename=zip_path.name,
    )

# --- API Endpoints ---
@app.get("/", summary="Root Endpoint", description="A simple root endpoint to check if the service is running.")
async def root():
    logger.info("Root endpoint called")
    return {"message": "Welcome to the Demucs Audio Separator API."}

@app.post("/separate-from-youtube/", summary="Separate Audio from YouTube", description="Provide a YouTube URL and get separated audio stems.")
def separate_from_youtube(
    request: YouTubeLinkRequest,
    start_time: int = Query(0, ge=0, description="Start time in seconds for the audio clip."),
    duration: int = Query(30, gt=0, le=300, description="Duration of the audio clip in seconds (max 300)."),
    background_tasks: BackgroundTasks = None
):
    request_id = str(uuid.uuid4())
    temp_download_path = DOWNLOAD_DIR / request_id
    temp_output_path = OUTPUT_DIR / request_id
    temp_zip_path = ZIP_DIR / f"{request_id}.zip"

    trimmed_audio_path = None
    try:
        logger.info(f"Processing YouTube separation request {request_id} for URL: {request.url}")
        logger.debug(f"Start time: {start_time}, Duration: {duration}, Download path: {temp_download_path}")
        trimmed_audio_path = download_and_trim_youtube_audio(str(request.url), start_time, duration, temp_download_path)
        logger.debug(f"Trimmed audio path: {trimmed_audio_path}")
        separated_files_dir = run_demucs_separation(trimmed_audio_path, temp_output_path)
        logger.debug(f"Separated files dir: {separated_files_dir}")
        mp3s = merge_stems_and_export(separated_files_dir, trimmed_audio_path, temp_output_path)
        logger.debug(f"MP3s dict: {mp3s}")
        response = zip_merged_mp3s(mp3s, temp_zip_path)
        if background_tasks is not None:
            background_tasks.add_task(cleanup_files, trimmed_audio_path, temp_output_path, temp_zip_path)
        logger.info(f"Returning response for request {request_id}")
        return response
    except Exception as e:
        logger.error(f"Error processing YouTube URL {request.url}: {e}")
        logger.info(f"Cleaning up files for request {request_id}")
        cleanup_files(trimmed_audio_path, temp_output_path, temp_zip_path)
        raise

@app.post("/separate-from-file/", summary="Separate Audio from File", description="Upload an audio file to separate it into stems.")
def separate_from_file(file: UploadFile = File(...), background_tasks: BackgroundTasks = None):
    request_id = str(uuid.uuid4())
    temp_upload_path = UPLOAD_DIR / f"{request_id}_{file.filename}"
    temp_output_path = OUTPUT_DIR / request_id
    temp_zip_path = ZIP_DIR / f"{request_id}.zip"

    supported_formats = ['.mp3', '.wav', '.flac', '.ogg']
    if Path(file.filename).suffix.lower() not in supported_formats:
        logger.warning(f"Unsupported file format: {file.filename}")
        raise HTTPException(status_code=400, detail=f"Unsupported file format. Supported: {', '.join(supported_formats)}")

    try:
        logger.info(f"Received file upload: {file.filename} (request {request_id})")
        logger.debug(f"Temp upload path: {temp_upload_path}, Output path: {temp_output_path}, Zip path: {temp_zip_path}")
        with temp_upload_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        logger.info(f"File saved to {temp_upload_path}")
        separated_files_dir = run_demucs_separation(temp_upload_path, temp_output_path)
        logger.debug(f"Separated files dir: {separated_files_dir}")
        mp3s = merge_stems_and_export(separated_files_dir, temp_upload_path, temp_output_path)
        logger.debug(f"MP3s dict: {mp3s}")
        response = zip_merged_mp3s(mp3s, temp_zip_path)
        if background_tasks is not None:
            background_tasks.add_task(cleanup_files, temp_upload_path, temp_output_path, temp_zip_path)
        logger.info(f"Returning response for request {request_id}")
        return response
    except Exception as e:
        logger.error(f"Error processing file upload {file.filename}: {e}")
        logger.info(f"Cleaning up files for request {request_id}")
        cleanup_files(temp_upload_path, temp_output_path, temp_zip_path)
        raise

COOKIES_FILE_PATH = "yt_dlp_cookies.txt"
cookies_content = os.environ.get("YT_DLP_COOKIES")
if cookies_content:
    with open(COOKIES_FILE_PATH, "w") as f:
        f.write(cookies_content)
    logger.info(f"Wrote yt-dlp cookies to {COOKIES_FILE_PATH}")
else:
    logger.info("No YT_DLP_COOKIES environment variable found; not writing cookies file.")

