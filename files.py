from pathlib import Path

from fastapi import HTTPException
from logger import logger
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
    if drums:
        outputs["drums.mp3"] = ffmpeg_merge([drums], "drums.mp3")
    # 2. Drums + Bass
    if drums and bass:
        outputs["drums_bass.mp3"] = ffmpeg_merge([drums, bass], "drums_bass.mp3")
    # 3. Drums + Bass + Guitar
    if drums and bass and guitar:
        outputs["drums_bass_guitar.mp3"] = ffmpeg_merge(
            [drums, bass, guitar], "drums_bass_guitar.mp3"
        )
    # 4. Drums + Bass + Guitar + Other + Piano
    merged = [f for f in [drums, bass, guitar, other, piano] if f]
    if len(merged) >= 2:
        outputs["drums_bass_guitar_other_piano.mp3"] = ffmpeg_merge(
            merged, "drums_bass_guitar_other_piano.mp3"
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