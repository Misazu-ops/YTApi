import asyncio
import os
import hashlib
import json
import time
import logging
from urllib.parse import urlparse, parse_qs

__all__ = ["get_stream", "get_video_stream"]

logger = logging.getLogger("YouTubeMusic.Stream")

_CACHE_DIR = os.path.join(os.path.dirname(__file__), ".cache")
os.makedirs(_CACHE_DIR, exist_ok=True)

_MEM_CACHE = {}


def _key(url: str, prefix: str = "") -> str:
    return hashlib.md5((prefix + url).encode()).hexdigest()


def _cache_path(url: str, prefix: str = "") -> str:
    return os.path.join(_CACHE_DIR, _key(url, prefix) + ".json")


def _extract_expire(stream_url: str) -> int | None:
    try:
        q = parse_qs(urlparse(stream_url).query)
        expire = int(q.get("expire", [0])[0])
        return expire if expire > int(time.time()) else None
    except Exception:
        return None


def _read_cache(url: str, prefix: str = "") -> str | None:
    path = _cache_path(url, prefix)

    if not os.path.exists(path):
        return None

    try:
        with open(path, "r") as f:
            data = json.load(f)

        expire = data.get("expire", 0)

        if time.time() < expire - 15:
            logger.info(f"[CACHE HIT] {prefix}{url[:80]}... (expires in {int(expire - time.time())}s)")
            return data.get("url")

        logger.info(f"[CACHE EXPIRED] {prefix}{url[:80]}... removing")
        os.remove(path)

    except Exception:
        try:
            os.remove(path)
        except Exception:
            pass

    return None


def _write_cache(url: str, stream_url: str, prefix: str = ""):
    expire = _extract_expire(stream_url)
    if not expire:
        logger.warning(f"[CACHE SKIP] No expire found in stream URL for {url[:80]}")
        return

    try:
        with open(_cache_path(url, prefix), "w") as f:
            json.dump(
                {
                    "url": stream_url,
                    "expire": expire,
                },
                f,
            )
        logger.info(f"[CACHE WRITE] {prefix}{url[:80]}... (expires in {int(expire - time.time())}s)")
    except Exception as e:
        logger.error(f"[CACHE WRITE ERROR] {e}")


async def _run_yt_dlp(url: str, format_selector: str, cookies: str | None):
    cmd = [
        "yt-dlp",
        "--js-runtimes", "node",
        "--remote-components", "ejs:github",
        "-f", format_selector,
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

    logger.info(f"[YT-DLP] Running: {' '.join(cmd)}")
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
        logger.error(f"[YT-DLP] TIMEOUT after 40s for {url}")
        return None
    except Exception as e:
        logger.error(f"[YT-DLP] Exception: {e}")
        return None

    elapsed = round(time.time() - start, 2)

    if process.returncode == 0 and stdout:
        stream_url = stdout.decode().strip().split("\n")[0]
        logger.info(f"[YT-DLP] ✅ Success ({elapsed}s) — {stream_url[:100]}...")
        return stream_url

    stderr_text = stderr.decode().strip() if stderr else "no stderr"
    logger.error(f"[YT-DLP] ❌ Failed (exit={process.returncode}, {elapsed}s) — {url}")
    logger.error(f"[YT-DLP] stderr: {stderr_text[-500:]}")
    return None


async def get_stream(url: str, cookies: str | None = None) -> str | None:
    logger.info(f"[AUDIO] get_stream called: {url}")

    cached = _MEM_CACHE.get(("audio", url))
    if cached:
        expire = _extract_expire(cached)
        if expire and time.time() < expire - 15:
            logger.info(f"[AUDIO] MEM_CACHE hit for {url[:80]}")
            return cached

    cached = _read_cache(url, prefix="audio_")
    if cached:
        _MEM_CACHE[("audio", url)] = cached
        return cached

    logger.info(f"[AUDIO] No cache, extracting fresh stream...")
    stream = await _run_yt_dlp(
        url,
        "bestaudio[ext=m4a]/bestaudio/best",
        cookies,
    )

    if stream:
        _MEM_CACHE[("audio", url)] = stream
        _write_cache(url, stream, prefix="audio_")
    else:
        logger.warning(f"[AUDIO] Extraction returned None for {url}")

    return stream


async def get_video_stream(url: str, cookies: str | None = None) -> str | None:
    logger.info(f"[VIDEO] get_video_stream called: {url}")

    cached = _MEM_CACHE.get(("video", url))
    if cached:
        expire = _extract_expire(cached)
        if expire and time.time() < expire - 15:
            logger.info(f"[VIDEO] MEM_CACHE hit for {url[:80]}")
            return cached

    cached = _read_cache(url, prefix="video_")
    if cached:
        _MEM_CACHE[("video", url)] = cached
        return cached

    logger.info(f"[VIDEO] No cache, extracting fresh stream...")
    stream = await _run_yt_dlp(
        url,
        "best[ext=mp4][protocol=https]",
        cookies,
    )

    if stream:
        _MEM_CACHE[("video", url)] = stream
        _write_cache(url, stream, prefix="video_")
    else:
        logger.warning(f"[VIDEO] Extraction returned None for {url}")

    return stream
