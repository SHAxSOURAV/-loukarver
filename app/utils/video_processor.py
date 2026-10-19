import os
import shutil
import asyncio
import logging
from typing import Tuple, Optional

logger = logging.getLogger("video_processor")

VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".webm", ".mkv", ".avi", ".3gp", ".ts"}

def get_ffmpeg_binary() -> Optional[str]:
    """
    Finds the FFmpeg binary path.
    Checks system PATH first, then falls back to imageio_ffmpeg bundled binary.
    """
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return system_ffmpeg
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as e:
        logger.warning(f"Could not resolve imageio_ffmpeg binary: {e}")
        return None

def is_video_file(filename: str, content_type: Optional[str] = None) -> bool:
    """Checks if a file is a video based on content type or file extension."""
    if content_type and content_type.lower().startswith("video/"):
        return True
    ext = os.path.splitext(filename)[1].lower() if filename else ""
    return ext in VIDEO_EXTENSIONS

async def optimize_video_file(
    input_path: str,
    output_path: str,
    crf: int = 26,
    preset: str = "fast"
) -> bool:
    """
    Optimizes a video file for ultra-fast mobile streaming:
    - Scales down high-res video (max 720x1280 portrait or 1280x720 landscape)
    - Compresses with H.264 (libx264, yuv420p for universal mobile compatibility)
    - Encodes audio to AAC 96k
    - Moves 'moov' atom to the front (+faststart) for immediate zero-buffer playback
    """
    ffmpeg_exe = get_ffmpeg_binary()
    if not ffmpeg_exe:
        logger.warning("FFmpeg binary not available. Skipping video optimization.")
        return False

    # Universal scaling filter:
    # Landscape: scale to max 1280w x 720h, portrait: scale to max 720w x 1280h
    # Both width and height guaranteed even for libx264 yuv420p
    vf_filter = "scale='if(gt(iw,ih),min(1280,iw),min(720,iw))':-2"

    cmd = [
        ffmpeg_exe,
        "-y",
        "-i", input_path,
        "-vf", vf_filter,
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-crf", str(crf),
        "-preset", preset,
        "-c:a", "aac",
        "-b:a", "96k",
        "-movflags", "+faststart",
        output_path
    ]

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        _, stderr = await process.communicate()

        if process.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            orig_size = os.path.getsize(input_path)
            new_size = os.path.getsize(output_path)
            savings = ((orig_size - new_size) / orig_size) * 100 if orig_size > 0 else 0
            logger.info(
                f"[VideoProcessor] Successfully optimized {os.path.basename(input_path)}: "
                f"{orig_size / (1024*1024):.2f}MB -> {new_size / (1024*1024):.2f}MB ({savings:.1f}% reduction, +faststart)"
            )
            return True
        else:
            logger.warning(f"[VideoProcessor] FFmpeg failed (code {process.returncode}): {stderr.decode(errors='ignore')[-500:]}")
            return False
    except Exception as e:
        logger.error(f"[VideoProcessor] Exception during optimization: {e}")
        return False
