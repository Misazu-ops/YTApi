from fastapi import FastAPI, Query, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import time
import asyncio
import logging
import datetime
from typing import Optional
from collections import defaultdict
import uvicorn
import threading
from pyrogram import Client, idle

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
    bot_token=BOT_TOKEN, in_memory=True,
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

try:
    telegram_app.start()
    setup_bot_commands()
    telegram_app.stop()
except Exception as e:
    print(f"Bot setup skipped (will retry at runtime): {e}")


# ─────────────────────────── FastAPI ───────────────────────────

app = FastAPI(
    title="YouTubeMusic API",
    description="API for YouTube Music search, streaming, and playlist extraction with Telegram bot integration"
)

# Rate limiting
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
        # Skip rate limiting for free endpoints
        free_paths = ["/", "/search", "/trending", "/suggest", "/health",
                      "/version", "/rate-limit-status", "/docs", "/openapi.json"]
        if request.url.path in free_paths:
            return await call_next(request)

        # Check for token authentication
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

        # Check rate limit
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

        # Increment counter only for successful requests
        if response.status_code == 200:
            new_count = await increment_user_requests(user_id)
            remaining = user_limit - new_count

            response.headers["X-RateLimit-Limit"] = str(user_limit)
            response.headers["X-RateLimit-Remaining"] = str(max(0, remaining))
            response.headers["X-RateLimit-Reset"] = str(
                int(datetime.datetime.combine(
                    datetime.date.today() + datetime.timedelta(days=1),
                    datetime.time.min
                ).timestamp())
            )

        return response


app.add_middleware(RateLimitMiddleware)


# ─────────────────────────── Endpoints ───────────────────────────

@app.get("/")
async def read_root():
    """API welcome page"""
    return {
        "name": "YouTubeMusic API",
        "version": "2026.3.12",
        "endpoints": {
            "/search": "Search songs via scrape or YouTube Data API (FREE)",
            "/trending": "Get trending music (FREE)",
            "/suggest": "Get song suggestions for a query (FREE)",
            "/stream": "Get audio or video stream URL (token required)",
            "/video-stream": "Get separate video + audio URLs (token required)",
            "/info": "Search + stream URL in one call (token required)",
            "/playlist": "Get all songs from a YouTube playlist (token required)",
            "/version": "Check library version info (FREE)",
            "/health": "Health check (FREE)",
            "/rate-limit-status": "Check your rate limit usage",
        },
        "free_endpoints": ["/search", "/trending", "/suggest", "/version", "/health"],
        "auth": "Get your token from the Telegram bot @ytdlp_nub_bot using /start"
    }


@app.get("/search")
async def search_songs(
    q: str = Query(..., description="Search query"),
    limit: int = Query(5, description="Number of results", ge=1, le=20),
    method: str = Query("scrape", description="Search method: 'scrape' (free) or 'api' (uses YouTube Data API)")
):
    """Search YouTube for songs — FREE (no token required)"""
    start_time = time.time()

    try:
        if method == "api":
            from YouTubeMusic.YtSearch import Search as YtApiSearch
            results = await YtApiSearch(q, limit=limit)
            elapsed = round(time.time() - start_time, 2)
            return JSONResponse(content={
                "query": q,
                "method": "youtube_data_api",
                "results": results,
                "total_results": len(results),
                "time_taken": f"{elapsed} sec"
            })
        else:
            from YouTubeMusic.Search import Search
            data = await Search(q, limit=limit)
            elapsed = round(time.time() - start_time, 2)
            return JSONResponse(content={
                "query": q,
                "method": "scrape",
                "results": data.get("main_results", []),
                "suggested": data.get("suggested", []),
                "total_results": len(data.get("main_results", [])),
                "time_taken": f"{elapsed} sec"
            })

    except Exception as e:
        elapsed = round(time.time() - start_time, 2)
        return JSONResponse(
            content={"error": str(e), "time_taken": f"{elapsed} sec"},
            status_code=400
        )


@app.get("/stream")
async def get_stream_url(
    q: str = Query(..., description="YouTube video URL"),
    mode: str = Query("audio", description="Mode: 'audio' or 'video'"),
    token: str = Query(..., description="Your API token"),
    user_id: int = Depends(require_token)
):
    """Get stream URL for a YouTube video.

    Modes:
    - `audio`: Best audio stream (m4a)
    - `video`: Best combined video+audio (mp4, 360p)
    """
    start_time = time.time()

    try:
        if mode == "video":
            from YouTubeMusic.Stream import get_video_stream
            stream_url = await get_video_stream(q)
        else:
            from YouTubeMusic.Stream import get_stream
            stream_url = await get_stream(q)

        elapsed = round(time.time() - start_time, 2)

        if stream_url:
            return JSONResponse(content={
                "url": q,
                "mode": mode,
                "stream_url": stream_url,
                "time_taken": f"{elapsed} sec"
            })
        else:
            return JSONResponse(
                content={"error": "Failed to extract stream URL", "time_taken": f"{elapsed} sec"},
                status_code=500
            )

    except Exception as e:
        elapsed = round(time.time() - start_time, 2)
        return JSONResponse(
            content={"error": str(e), "time_taken": f"{elapsed} sec"},
            status_code=400
        )


@app.get("/video-stream")
async def video_stream_urls(
    q: str = Query(..., description="YouTube video URL"),
    token: str = Query(..., description="Your API token"),
    user_id: int = Depends(require_token)
):
    """Get separate best-quality video and audio URLs.

    Returns two URLs: bestvideo (mp4) + bestaudio (m4a).
    Use these with ffmpeg or a player that supports dual-source playback.
    """
    start_time = time.time()

    try:
        from YouTubeMusic.Video_Stream import get_video_audio_urls
        video_url, audio_url = await get_video_audio_urls(q)
        elapsed = round(time.time() - start_time, 2)

        if video_url and audio_url:
            return JSONResponse(content={
                "url": q,
                "video_url": video_url,
                "audio_url": audio_url,
                "time_taken": f"{elapsed} sec"
            })
        else:
            return JSONResponse(
                content={"error": "Failed to extract video+audio URLs", "time_taken": f"{elapsed} sec"},
                status_code=500
            )

    except Exception as e:
        elapsed = round(time.time() - start_time, 2)
        return JSONResponse(
            content={"error": str(e), "time_taken": f"{elapsed} sec"},
            status_code=400
        )


@app.get("/info")
async def video_info(
    q: str = Query(..., description="YouTube video URL or search query"),
    max_results: int = Query(1, description="Max results for search queries", ge=1, le=10),
    mode: str = Query("audio", description="Mode: 'audio' for audio-only, 'video' for video stream"),
    token: str = Query(..., description="Your API token"),
    user_id: int = Depends(require_token)
):
    """Get video info + stream URL (token required)"""
    start_time = time.time()

    try:
        # Check if it's a YouTube URL
        import re
        yt_url_pattern = re.compile(r'(youtube\.com|youtu\.be)')
        is_url = bool(yt_url_pattern.search(q))

        if is_url:
            # Direct URL — get stream
            if mode == "video":
                from YouTubeMusic.Stream import get_video_stream
                stream_url = await get_video_stream(q)
            else:
                from YouTubeMusic.Stream import get_stream
                stream_url = await get_stream(q)

            # Also get search info for title/details
            from YouTubeMusic.Search import Search
            search_data = await Search(q.split("v=")[-1].split("&")[0] if "v=" in q else q, limit=1)
            info = search_data.get("main_results", [{}])[0] if search_data.get("main_results") else {}

            elapsed = round(time.time() - start_time, 2)
            return JSONResponse(content={
                "query_type": "url",
                "title": info.get("title"),
                "duration": info.get("duration"),
                "youtube_link": q,
                "channel_name": info.get("channel"),
                "views": info.get("views"),
                "video_id": info.get("video_id"),
                "stream_url": stream_url,
                "thumbnail": info.get("thumbnail"),
                "time_taken": f"{elapsed} sec"
            })
        else:
            # Search query
            from YouTubeMusic.Search import Search
            search_data = await Search(q, limit=max_results)

            if max_results == 1 and search_data.get("main_results"):
                # Single result — also get stream URL
                result = search_data["main_results"][0]
                video_url = result.get("url", "")

                if mode == "video":
                    from YouTubeMusic.Stream import get_video_stream
                    stream_url = await get_video_stream(video_url)
                else:
                    from YouTubeMusic.Stream import get_stream
                    stream_url = await get_stream(video_url)

                elapsed = round(time.time() - start_time, 2)
                return JSONResponse(content={
                    "query_type": "search",
                    "query": q,
                    "title": result.get("title"),
                    "duration": result.get("duration"),
                    "youtube_link": result.get("url"),
                    "channel_name": result.get("channel"),
                    "views": result.get("views"),
                    "video_id": result.get("video_id"),
                    "stream_url": stream_url,
                    "thumbnail": result.get("thumbnail"),
                    "time_taken": f"{elapsed} sec"
                })
            else:
                # Multiple results — return list only
                elapsed = round(time.time() - start_time, 2)
                results = search_data.get("main_results", [])
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
            content={"error": str(e), "time_taken": f"{elapsed} sec"},
            status_code=400
        )


@app.get("/trending")
async def trending_songs(
    limit: int = Query(10, description="Number of trending songs", ge=1, le=20)
):
    """Get trending songs — FREE (no token required)"""
    start_time = time.time()

    try:
        from YouTubeMusic.Search import Trending
        results = await Trending(limit=limit)
        elapsed = round(time.time() - start_time, 2)

        return JSONResponse(content={
            "results": results,
            "total_results": len(results),
            "time_taken": f"{elapsed} sec"
        })

    except Exception as e:
        elapsed = round(time.time() - start_time, 2)
        return JSONResponse(
            content={"error": str(e), "time_taken": f"{elapsed} sec"},
            status_code=400
        )


@app.get("/suggest")
async def suggest_songs(
    q: str = Query(..., description="Search query"),
    limit: int = Query(5, description="Number of suggestions", ge=1, le=20)
):
    """Get song suggestions — FREE (no token required)"""
    start_time = time.time()

    try:
        from YouTubeMusic.Search import Suggest
        results = await Suggest(q, limit=limit)
        elapsed = round(time.time() - start_time, 2)

        return JSONResponse(content={
            "query": q,
            "results": results,
            "total_results": len(results),
            "time_taken": f"{elapsed} sec"
        })

    except Exception as e:
        elapsed = round(time.time() - start_time, 2)
        return JSONResponse(
            content={"error": str(e), "time_taken": f"{elapsed} sec"},
            status_code=400
        )


@app.get("/playlist")
async def playlist_songs(
    url: str = Query(..., description="YouTube playlist URL or playlist ID (e.g. PLxxxxxxx, RDxxxxxx)"),
    token: str = Query(..., description="Your API token"),
    user_id: int = Depends(require_token)
):
    """Get all songs from a YouTube playlist.

    Supports normal playlists (PL...), auto-generated playlists (OL..., UU...),
    and YouTube Mix playlists (RD...).
    """
    start_time = time.time()

    try:
        from YouTubeMusic.Playlist import get_playlist_songs
        songs = await get_playlist_songs(url)
        elapsed = round(time.time() - start_time, 2)

        return JSONResponse(content={
            "playlist_url": url,
            "songs": songs,
            "total_songs": len(songs),
            "time_taken": f"{elapsed} sec"
        })

    except ValueError as e:
        elapsed = round(time.time() - start_time, 2)
        return JSONResponse(
            content={"error": str(e), "time_taken": f"{elapsed} sec"},
            status_code=400
        )
    except Exception as e:
        elapsed = round(time.time() - start_time, 2)
        return JSONResponse(
            content={"error": str(e), "time_taken": f"{elapsed} sec"},
            status_code=500
        )


@app.get("/version")
async def version_info():
    """Get YouTubeMusic library version info — FREE"""
    try:
        from YouTubeMusic.Startup import get_startup_info
        info = await get_startup_info()
        return JSONResponse(content=info)
    except Exception as e:
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
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


# ─────────────────────────── Run Services ───────────────────────────

def start_services():
    print("🌐 Starting FastAPI server on http://0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info", loop="asyncio")


if __name__ == "__main__":
    try:
        import asyncio
        threading.Thread(target=start_services, daemon=True).start()
        try:
            telegram_app.run()
        except Exception as e:
            print(f"Bot failed: {e}, API still running...")
            import time as _time
            while True:
                _time.sleep(3600)
    except KeyboardInterrupt:
        print("Services stopped by user")
    except Exception as e:
        print(f"Error starting services: {e}")
