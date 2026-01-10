from pathlib import Path
import re
import shutil

from fastapi import HTTPException
from app.logger import logger
from demucs.separate import main as demucs_separate
import subprocess


def run_demucs_separation(audio_path: Path, output_path: Path) -> Path:
    """Runs the Demucs separation process on a given audio file."""
    model_name = "htdemucs_6s"
    try:
        demucs_args = [
            "-d",
            "cpu",  # Use CPU for processing
            f"--out={str(output_path)}",
            f"--name={model_name}",
            "--shifts",
            "2",  # Use 2 shifts for better quality
            str(audio_path),
        ]
        logger.info(f"Running Demucs on {audio_path} with output {output_path}")
        logger.debug(f"Demucs args: {demucs_args}")
        demucs_separate(demucs_args)
        logger.info(f"Demucs separation completed for {audio_path}")
    except Exception as e:
        logger.error(f"An error occurred during Demucs processing: {e}")
        raise HTTPException(
            status_code=500, detail=f"An error occurred during Demucs processing: {e}"
        )

    separated_files_dir = output_path / model_name / Path(audio_path.stem)
    if not separated_files_dir.exists() or not any(separated_files_dir.iterdir()):
        logger.error("Audio separation failed. No output files were generated.")
        raise HTTPException(
            status_code=500,
            detail="Audio separation failed. No output files were generated.",
        )

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

    def get_non_silent(name):
        f = next((f for s, f in stem_files.items() if name in s), None)
        if f and is_wav_silent(f):
            logger.info(f"Stem {name} ({f}) is silent. Ignoring.")
            return None
        return f

    drums = get_non_silent("drums")
    bass = get_non_silent("bass")
    guitar = get_non_silent("guitar")
    other = get_non_silent("other")
    piano = get_non_silent("piano")
    # vocals = get("vocals")  # Not used in your requested mixes

    outputs = {}

    def ffmpeg_merge(inputs, outname):
        # Filter out None inputs (silent stems)
        valid_inputs = [f for f in inputs if f is not None]

        if not valid_inputs:
            logger.info(f"All inputs for {outname} are silent/missing. Skipping generation.")
            return None

        outpath = output_dir / outname
        cmd = [
            "ffmpeg",
            *sum([["-i", str(f)] for f in valid_inputs], []),
            "-filter_complex",
            f"amix=inputs={len(valid_inputs)}:duration=longest:dropout_transition=0",
            "-c:a",
            "libmp3lame",
            "-q:a",
            "2",
            "-y",
            str(outpath),
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        return outpath

    # 1. Drums only
    outputs["drums.mp3"] = ffmpeg_merge([drums], "drums.mp3")

    # 2. Drums + Bass
    outputs["drums_bass.mp3"] = ffmpeg_merge([drums, bass], "drums_bass.mp3")

    # 3. Drums + Bass + Guitar
    outputs["drums_bass_guitar.mp3"] = ffmpeg_merge(
        [drums, bass, guitar], "drums_bass_guitar.mp3"
    )

    # 4. Drums + Bass + Guitar + Other + Piano
    outputs["drums_bass_guitar_other_piano.mp3"] = ffmpeg_merge(
        [drums, bass, guitar, other, piano], "drums_bass_guitar_other_piano.mp3"
    )

    # 5. Original trimmed mp3
    # Convert trimmed wav to mp3
    orig_mp3 = output_dir / "original_trimmed.mp3"
    subprocess.run(
        [
            "ffmpeg",
            "-i",
            str(trimmed_audio_path),
            "-c:a",
            "libmp3lame",
            "-q:a",
            "2",
            "-y",
            str(orig_mp3),
        ],
        check=True,
        capture_output=True,
    )
    outputs["original_trimmed.mp3"] = orig_mp3

    return outputs


# --- Helper Functions ---
def is_wav_silent(file_path: Path) -> bool:
    """Checks if a WAV file is completely silent using ffmpeg volumedetect."""
    logger.info(f"Checking if {file_path} is silent")
    cmd = [
        "ffmpeg",
        "-i",
        str(file_path),
        "-af",
        "volumedetect",
        "-f",
        "null",
        "-",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        # Look for max_volume in stderr: max_volume: -91.0 dB or max_volume: -inf dB
        match = re.search(r"max_volume: ([\-\d\.]+|inf) dB", result.stderr)
        if match:
            max_vol_str = match.group(1)
            if max_vol_str == "-inf" or max_vol_str == "inf": # inf shouldn't happen for volume but just in case
                logger.info(f"File {file_path} is silent (-inf dB).")
                return True
            try:
                max_vol = float(max_vol_str)
                if max_vol <= -50.0:
                    logger.info(f"File {file_path} is silent ({max_vol} dB).")
                    return True
            except ValueError:
                pass
        return False
    except Exception as e:
        logger.error(f"Error checking silence for {file_path}: {e}")
        return False


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


def print_directory_tree(root_dir: Path):
    logger.info(f"Directory tree for {root_dir}:")
    for path in root_dir.rglob("*"):
        logger.info(f"  {path.resolve()}")
