from fastapi import FastAPI, Query, BackgroundTasks, Request, HTTPException, Header, Depends
from fastapi.responses import JSONResponse, FileResponse
from starlette.middleware.base import BaseHTTPMiddleware
import yt_dlp
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
import logging
import re
from collections import defaultdict
import datetime
from typing import Optional
import uvicorn
import threading
import redis
import string
import random
from pyrogram import Client,idle

# Telegram Bot Configuration
API_ID = 21856699
API_HASH = '73f10cf0979637857170f03d4c86f251'
BOT_TOKEN = '8246299769:AAF2jRzQBJmkOqL_146jKG0EjWbeTSC78eU'
GROUP = "nub_coder_s"
CHANNEL = "nub_coders"

# Import shared tools
from tools import (
    redis_client, generate_token, is_admin, get_user_token, 
    set_user_token, revoke_user_token, get_user_by_token,
    get_user_request_count, set_user_request_count, increment_user_requests
)

# Initialize Pyrogram client with plugins
telegram_app = Client(
    "ytdlp_bot", 
    api_id=API_ID, 
    api_hash=API_HASH, 
    bot_token=BOT_TOKEN,in_memory=True,
    plugins=dict(root="plugins"),
    device_model="Desktop",
    system_version="Windows 10",
    app_version="3.4.3 x64",
    lang_code="en",
    lang_pack="tdesktop"
)

def setup_bot_commands():
    """Set up bot commands menu"""
    from pyrogram.types import BotCommand

    commands = [
        BotCommand("start", "🚀 Get your API token and welcome message"),
        BotCommand("menu", "📋 Show main menu with options"),
        BotCommand("ping", "🏓 Check bot latency"),
        BotCommand("status", "📊 Check your usage statistics"),
        BotCommand("token", "🔑 View your current API token"),
        BotCommand("revoke", "🔄 Revoke your current token"),
        BotCommand("help", "❓ Get help and API documentation"),
    ]

    try:
        telegram_app.set_bot_commands(commands)
        print("✅ Bot commands set successfully")
    except Exception as e:
        print(f"⚠️ Failed to set bot commands: {e}")

telegram_app.start()
setup_bot_commands()
telegram_app.stop()



app = FastAPI(title="yt-dlp API", description="Optimized API for YouTube info with cookies support and Telegram bot integration")

@app.get("/")
async def read_root():
    """Serve the main webpage"""
    return FileResponse("index.html")

# Rate limiting storage - tracks daily requests per IP (fallback)
daily_request_counts = defaultdict(lambda: {"count": 0, "date": datetime.date.today()})
DAILY_LIMIT = 1000
ADMIN_LIMIT = 10000

async def get_current_user(token: Optional[str] = Query(None)):
    """Get current user from token"""
    if not token:
        return None

    try:
        user_id = get_user_by_token(token)
        return user_id
    except:
        return None

async def require_token(token: Optional[str] = Query(None, description="Your API token")):
    """Require valid token for protected endpoints"""
    user_id = await get_current_user(token)
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "Token required",
                "message": "Please get your token from the Telegram bot using /start command and add it as ?token=YOUR_TOKEN"
            }
        )
    return user_id

class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for search endpoints and health check
        if request.url.path in ["/", "/search", "/health", "/clear-cache", "/rate-limit-status"]:
            return await call_next(request)

        # Check for token authentication from query parameter
        token = request.query_params.get("token")
        user_id = await get_current_user(token)

        if not user_id:
            return JSONResponse(
                status_code=401,
                content={
                    "error": "Token required",
                    "message": "Please get your token from the Telegram bot using /start command and add it as ?token=YOUR_TOKEN"
                }
            )

        # Get user's request count and limit
        request_count = await get_user_request_count(user_id)
        user_limit = ADMIN_LIMIT if is_admin(user_id) else DAILY_LIMIT

        # Check if user has exceeded daily limit
        if request_count >= user_limit:
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Daily limit exceeded",
                    "message": f"You have exceeded your daily limit of {user_limit} requests. Search functionality remains free.",
                    "remaining_requests": 0,
                    "reset_time": "Resets at midnight UTC"
                }
            )

        # Process the request
        response = await call_next(request)

        # Increment counter only for successful data requests (not errors)
        if response.status_code == 200:
            new_count = await increment_user_requests(user_id)
            remaining = user_limit - new_count

            # Add rate limit headers to response
            response.headers["X-RateLimit-Limit"] = str(user_limit)
            response.headers["X-RateLimit-Remaining"] = str(max(0, remaining))
            response.headers["X-RateLimit-Reset"] = str(int((datetime.datetime.combine(datetime.date.today() + datetime.timedelta(days=1), datetime.time.min).timestamp())))

        return response

# Add the rate limiting middleware
app.add_middleware(RateLimitMiddleware)

# Thread pool for CPU-bound operations
executor = ThreadPoolExecutor(max_workers=8)

# Cookies file path (exported from Firefox by entrypoint.sh)
COOKIES_FILE = "/app/cookies/cookies.txt"
import os
_cookie_opt = {"cookiefile": COOKIES_FILE} if os.path.exists(COOKIES_FILE) else {"cookiesfrombrowser": ("firefox",)}

# Disable yt-dlp logging for better performance
logging.getLogger('yt_dlp').setLevel(logging.ERROR)

# Cache video info for 5 minutes to avoid repeated requests
@lru_cache(maxsize=100)
def get_cached_info(url: str, cache_key: int):
    """Cache wrapper - cache_key changes every 5 minutes"""
    return _extract_info(url)

def _extract_info(url: str):
    """Extract only essential video information using Firefox cookies - optimized"""
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best",
        **_cookie_opt,

        # Skip unnecessary metadata
        "extract_flat": False,
        "writethumbnail": False,
        "writeinfojson": False,
        "writedescription": False,
        "writesubtitles": False,
        "writeautomaticsub": False,
        "noplaylist": True,

        # Speed tweaks
        "retries": 1,
        "fragment_retries": 1,
        "socket_timeout": 10,
        "geo_bypass": True,
        "skip_playlist_after_errors": 1,
        "extractor_args": {
            "youtube": {
                "skip": ["translated_subs"],
            }
        },
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        return ydl.extract_info(url, download=False)

def _search_videos(query: str, max_results: int = 1):
    """Search YouTube videos by query"""
    search_url = f"ytsearch{max_results}:{query}"

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best",
        **_cookie_opt,
        "extract_flat": True,  # Only get basic info for search
        "socket_timeout": 10,
        "geo_bypass": True,
        "noplaylist": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        return ydl.extract_info(search_url, download=False)

def is_youtube_url(text: str) -> bool:
    """Check if text is a YouTube URL"""
    youtube_patterns = [
        r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=[\w-]+',
        r'(?:https?://)?(?:www\.)?youtu\.be/[\w-]+',
        r'(?:https?://)?(?:www\.)?youtube\.com/embed/[\w-]+',
        r'(?:https?://)?(?:m\.)?youtube\.com/watch\?v=[\w-]+',
    ]

    for pattern in youtube_patterns:
        if re.match(pattern, text.strip()):
            return True
    return False

# Cache search results for 10 minutes
@lru_cache(maxsize=50)
def get_cached_search_results(query: str, max_results: int, cache_key: int):
    """Cache wrapper for search results"""
    return _search_videos(query, max_results)

def get_cache_key():
    """Generate cache key that changes every 5 minutes"""
    return int(time.time() // 300)  # 300 seconds = 5 minutes

async def extract_video_info_async(url: str):
    """Run yt-dlp in thread pool to avoid blocking"""
    loop = asyncio.get_event_loop()
    cache_key = get_cache_key()

    # Run in thread pool since yt-dlp is CPU/IO bound
    info = await loop.run_in_executor(
        executor, 
        get_cached_info, 
        url, 
        cache_key
    )
    return info

def extract_best_format(formats):
    """Return best quality video+audio URLs. Handles both progressive and DASH streams."""
    if not formats:
        return None, None, {}

    def is_video_only(f):
        return f.get("vcodec") != "none" and f.get("acodec") == "none" and f.get("url")

    def is_audio_only(f):
        return f.get("acodec") != "none" and f.get("vcodec") == "none" and f.get("url")

    def is_progressive(f):
        return (
            f.get("acodec") != "none"
            and f.get("vcodec") != "none"
            and f.get("url")
        )

    # Sort formats by quality (height desc, then tbr desc)
    sorted_formats = sorted(
        formats,
        key=lambda f: (f.get("height") or 0, f.get("tbr") or 0),
        reverse=True
    )

    # Try to find best separate video + audio (DASH - highest quality)
    best_video = next((f for f in sorted_formats if is_video_only(f)), None)
    best_audio = next((f for f in sorted_formats if is_audio_only(f)), None)

    if best_video and best_audio:
        headers = best_video.get("http_headers", {})
        return best_video.get("url"), best_audio.get("url"), headers

    # Fallback: best progressive (single file, audio+video)
    best_progressive = next((f for f in sorted_formats if is_progressive(f)), None)
    if best_progressive:
        return best_progressive.get("url"), None, best_progressive.get("http_headers", {})

    # Last resort: first available URL
    first = next((f for f in formats if f.get("url")), None)
    if first:
        return first.get("url"), None, first.get("http_headers", {})

    return None, None, {}

@app.get("/info")
async def video_info(
    q: str = Query(..., description="YouTube video URL or search query"),
    max_results: int = Query(1, description="Max results for search queries", ge=1, le=10),
    token: str = Query(..., description="Your API token"),
    user_id: int = Depends(require_token)
):
    start_time = time.time()

    try:
        if is_youtube_url(q):
            # Handle as URL
            info = await extract_video_info_async(q)
            video_url, audio_url, format_headers = extract_best_format(info.get("formats", []))

            elapsed = round(time.time() - start_time, 2)

            return JSONResponse(content={
                "query_type": "url",
                "title": info.get("title"),
                "duration": info.get("duration"),
                "youtube_link": info.get("webpage_url"),
                "channel_name": info.get("uploader"),
                "views": info.get("view_count"),
                "video_id": info.get("id"),
                "video_url": video_url,
                "audio_url": audio_url,
                "headers": format_headers,
                "thumbnail": info.get("thumbnail"),
                "time_taken": f"{elapsed} sec"
            })
        else:
            # Handle as search query
            loop = asyncio.get_event_loop()
            cache_key = get_cache_key()

            search_results = await loop.run_in_executor(
                executor,
                get_cached_search_results,
                q,
                max_results,
                cache_key
            )

            # Get detailed info for each result
            if max_results == 1 and search_results.get("entries"):
                # Single result - return detailed info
                first_result = search_results["entries"][0]
                video_url = first_result.get("url") or f"https://youtube.com/watch?v={first_result.get('id')}"

                detailed_info = await extract_video_info_async(video_url)
                d_video_url, d_audio_url, format_headers = extract_best_format(detailed_info.get("formats", []))

                elapsed = round(time.time() - start_time, 2)

                return JSONResponse(content={
                    "query_type": "search",
                    "query": q,
                    "title": detailed_info.get("title"),
                    "duration": detailed_info.get("duration"),
                    "youtube_link": detailed_info.get("webpage_url"),
                    "channel_name": detailed_info.get("uploader"),
                    "views": detailed_info.get("view_count"),
                    "video_id": detailed_info.get("id"),
                    "video_url": d_video_url,
                    "audio_url": d_audio_url,
                    "headers": format_headers,
                    "thumbnail": detailed_info.get("thumbnail"),
                    "time_taken": f"{elapsed} sec"
                })
            else:
                # Multiple results - return search list
                elapsed = round(time.time() - start_time, 2)

                results = []
                for entry in search_results.get("entries", []):
                    results.append({
                        "title": entry.get("title"),
                        "video_id": entry.get("id"),
                        "channel_name": entry.get("uploader"),
                        "duration": entry.get("duration"),
                        "views": entry.get("view_count"),
                        "youtube_link": f"https://youtube.com/watch?v={entry.get('id')}",
                        "thumbnail": entry.get("thumbnail")
                    })

                return JSONResponse(content={
                    "query_type": "search",
                    "query": q,
                    "results": results,
                    "total_results": len(results),
                    "time_taken": f"{elapsed} sec"
                })

    except Exception as e:
        elapsed = round(time.time() - start_time, 2)
        return JSONResponse(
            content={
                "error": str(e),
                "time_taken": f"{elapsed} sec"
            }, 
            status_code=400
        )

# Optional: Search-only endpoint
@app.get("/search")
async def search_videos(
    q: str = Query(..., description="Search query"),
    max_results: int = Query(1, description="Number of results to return", ge=1, le=20)
):
    """Search YouTube videos without getting detailed info - FREE (no rate limit)"""
    start_time = time.time()

    try:
        loop = asyncio.get_event_loop()
        cache_key = get_cache_key()

        search_results = await loop.run_in_executor(
            executor,
            get_cached_search_results,
            q,
            max_results,
            cache_key
        )

        elapsed = round(time.time() - start_time, 2)

        results = []
        for entry in search_results.get("entries", []):
            results.append({
                "title": entry.get("title"),
                "video_id": entry.get("id"),
                "channel_name": entry.get("uploader"),
                "duration": entry.get("duration"),
                "views": entry.get("view_count"),
                "youtube_link": f"https://youtube.com/watch?v={entry.get('id')}",
                "thumbnail": entry.get("thumbnails")
            })

        return JSONResponse(content={
            "query": q,
            "results": results,
            "total_results": len(results),
            "time_taken": f"{elapsed} sec"
        })

    except Exception as e:
        elapsed = round(time.time() - start_time, 2)
        return JSONResponse(
            content={
                "error": str(e),
                "time_taken": f"{elapsed} sec"
            },
            status_code=400
        )

@app.get("/health")
async def health_check():
    """Quick health check endpoint"""
    return {"status": "ok"}

@app.get("/rate-limit-status")
async def rate_limit_status(token: Optional[str] = Query(None, description="Your API token")):
    """Check current rate limit status"""
    user_id = await get_current_user(token)
    if user_id:
        # Token-based user
        used = await get_user_request_count(user_id)
        limit = ADMIN_LIMIT if is_admin(user_id) else DAILY_LIMIT

        return {
            "user_id": user_id,
            "daily_limit": limit,
            "requests_used": used,
            "requests_remaining": max(0, limit - used),
            "reset_time": "Resets at midnight UTC",
            "is_admin": is_admin(user_id),
            "auth_method": "token"
        }
    else:
        return {
            "error": "No token provided",
            "message": "Please get your token from the Telegram bot using /start command and add it as ?token=YOUR_TOKEN",
            "auth_method": "none"
        }

# Optional: Clear cache endpoint
@app.post("/clear-cache")
async def clear_cache():
    """Clear both info and search caches"""
    get_cached_info.cache_clear()
    get_cached_search_results.cache_clear()
    return {"message": "All caches cleared"}








def start_services():
    print("🌐 Starting FastAPI server on http://0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info",loop="asyncio")



if __name__ == "__main__":
    try:
        import asyncio
        threading.Thread(target=start_services).start()
        telegram_app.run()
    except KeyboardInterrupt:
        print("🛑 Services stopped by user")
    except Exception as e:
        print(f"❌ Error starting services: {e}")
