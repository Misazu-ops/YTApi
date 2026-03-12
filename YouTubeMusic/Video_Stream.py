import asyncio
import os
import logging

logger = logging.getLogger("YouTubeMusic.Video_Stream")


async def get_video_audio_urls(url: str, cookies: str | None = None):
    cmd = [
        "yt-dlp",
        "--js-runtimes", "node",
        "--remote-components", "ejs:github",
        "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]",
        "--no-playlist",
        "-g",
        url,
    ]

    # Use cookies file if provided, otherwise try Firefox cookies
    if cookies and os.path.exists(cookies):
        cmd.insert(1, "--cookies")
        cmd.insert(2, cookies)
    else:
        cmd.insert(1, "--cookies-from-browser")
        cmd.insert(2, "firefox")

    logger.info(f"[VIDEO_STREAM] Running: {' '.join(cmd)}")

    import time
    start = time.time()

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=40,
        )

    except asyncio.TimeoutError:
        logger.error(f"[VIDEO_STREAM] TIMEOUT after 40s for {url}")
        return None, None
    except Exception as e:
        logger.error(f"[VIDEO_STREAM] Exception: {e}")
        return None, None

    elapsed = round(time.time() - start, 2)

    if process.returncode != 0 or not stdout:
        stderr_text = stderr.decode().strip() if stderr else "no stderr"
        logger.error(f"[VIDEO_STREAM] ❌ Failed (exit={process.returncode}, {elapsed}s) — {url}")
        logger.error(f"[VIDEO_STREAM] stderr: {stderr_text[-500:]}")
        return None, None

    urls = stdout.decode().strip().split("\n")

    if len(urls) < 2:
        logger.error(f"[VIDEO_STREAM] ❌ Expected 2 URLs, got {len(urls)} — {url}")
        return None, None

    logger.info(f"[VIDEO_STREAM] ✅ Success ({elapsed}s)")
    logger.info(f"[VIDEO_STREAM] Video: {urls[0][:100]}...")
    logger.info(f"[VIDEO_STREAM] Audio: {urls[1][:100]}...")
    return urls[0], urls[1]


async def stream_merged(video_url: str, audio_url: str):
    ffmpeg_cmd = [
        "ffmpeg",
        "-loglevel", "error",
        "-i", video_url,
        "-i", audio_url,
        "-c:v", "copy",
        "-c:a", "copy",
        "-f", "mp4",
        "-movflags", "frag_keyframe+empty_moov+faststart",
        "pipe:1",
    ]

    logger.info(f"[MERGE] Starting ffmpeg merge")

    try:
        process = await asyncio.create_subprocess_exec(
            *ffmpeg_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        return process
    except Exception as e:
        logger.error(f"[MERGE] ffmpeg failed: {e}")
        return None
