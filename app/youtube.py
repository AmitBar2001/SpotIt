from app.config import settings
from app.files import cleanup_files, print_directory_tree
from app.logger import logger


import yt_dlp
from fastapi import HTTPException


import os
import subprocess
from pathlib import Path


def download_and_trim_youtube_audio(
    url: str,
    start_time: int | None,
    duration: int,
    download_path: Path,
    search_term: str | None = None,
) -> tuple[Path, dict]:
    """Downloads audio from a YouTube URL and trims it using ffmpeg. If start_time is None, auto-pick using heatmap."""
    if search_term:
        logger.info(
            f"Starting download_and_trim_youtube_audio for search term: {search_term}, duration: {duration}, download_path: {download_path}"
        )
        youtube_url = f"ytsearch1: {search_term}"
    else:
        logger.info(
            f"Starting download_and_trim_youtube_audio for URL: {url}, start_time: {start_time}, duration: {duration}, download_path: {download_path}"
        )
        youtube_url = url

    # Ensure the download directory exists
    download_path.mkdir(parents=True, exist_ok=True)

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
                "preferredcodec": "wav",
            }
        ],
        "logger": logger,
        "postprocessor_args": ["-ar", "44100", "-ac", "2"],
        "writesubtitles": False,
        "writeinfojson": True,
        "keepvideo": False,
        "extractor_args": {"youtube": {"player_client": ['default'], "player_js_version": ['actual']}},
        "external_downloader": "aria2c",
        "cookiefile": (
            settings.yt_dlp_cookies_file_path
            if os.path.exists(settings.yt_dlp_cookies_file_path)
            else None
        ),
    }

    # Use proxy if configured
    if settings.yt_dlp_proxy is not None:
        ydl_opts["proxy"] = settings.yt_dlp_proxy
        logger.info("Using proxy for yt-dlp.")

    if settings.yt_dlp_proxy is not None:
        ydl_opts["proxy"] = settings.yt_dlp_proxy
        logger.info("Using proxy for yt-dlp.")

    try:
        logger.debug(f"yt_dlp options: {ydl_opts}")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            video_info_json = ydl.extract_info(youtube_url)

        if not video_info_json:
            logger.error("yt-dlp did not return video info.")
            raise Exception("yt-dlp did not return video info.")

        if search_term:
            video_info_json = video_info_json.get("entries")[0]
        requested_downloads = video_info_json.get("requested_downloads")

        if requested_downloads is None or not isinstance(requested_downloads, list):
            logger.error("Could not find requested_downloads in yt-dlp info JSON.")
            raise Exception("Could not find requested_downloads in yt-dlp info JSON.")

        original_audio_path = Path(requested_downloads[0]["filepath"]).resolve()

        logger.info(f"Downloaded audio to {original_audio_path}")

        if settings.log_level == "DEBUG":
            print_directory_tree(download_path)
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

    trimmed_audio_path = (
        download_path / f"trimmed_{original_audio_path.stem}.wav"
    ).resolve()

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
        cleanup_files(
            original_audio_path, original_audio_path.with_suffix(".info.json")
        )
        error_message = e.stderr.decode()
        logger.error(f"Failed to trim audio with ffmpeg: {error_message}")
        raise HTTPException(
            status_code=500, detail=f"Failed to trim audio with ffmpeg: {error_message}"
        )

    cleanup_files(original_audio_path, original_audio_path.with_suffix(".info.json"))

    return trimmed_audio_path, video_info_json