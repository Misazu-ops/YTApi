import asyncio
import os


async def get_video_audio_urls(url: str, cookies: str | None = None):
    cmd = [
        "yt-dlp",
        "--js-runtimes",
        "node",
        "--remote-components",
        "ejs:github",
        "-f",
        "bestvideo[ext=mp4]+bestaudio[ext=m4a]",
        "--no-playlist",
        "-g",
        url,
    ]

    if cookies:
        if os.path.exists(cookies):
            cmd.insert(1, "--cookies")
            cmd.insert(2, cookies)
        else:
            return None, None

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, _ = await asyncio.wait_for(
            process.communicate(),
            timeout=40,
        )

    except Exception:
        return None, None

    if process.returncode != 0 or not stdout:
        return None, None

    urls = stdout.decode().strip().split("\n")

    if len(urls) < 2:
        return None, None

    return urls[0], urls[1]


async def stream_merged(video_url: str, audio_url: str):
    ffmpeg_cmd = [
        "ffmpeg",
        "-loglevel",
        "error",
        "-i",
        video_url,
        "-i",
        audio_url,
        "-c:v",
        "copy",
        "-c:a",
        "copy",
        "-f",
        "mp4",
        "-movflags",
        "frag_keyframe+empty_moov+faststart",
        "pipe:1",
    ]

    try:
        process = await asyncio.create_subprocess_exec(
            *ffmpeg_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        return process
    except Exception:
        return None
