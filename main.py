from fastapi import FastAPI, Query, BackgroundTasks, Request, HTTPException, Header, Depends
from fastapi.responses import JSONResponse
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
import redis
import string
import random
from pyrogram import Client

# Telegram Bot Configuration
API_ID = 21869707
API_HASH = '31ec80a4adad7aaad9262e894e3654e6'
BOT_TOKEN = '8246299769:AAHD8gd49wwlMuq9lBXmKtCNOxWDFjKR694'
GROUP = "nub_coder_s"
CHANNEL = "nub_coders"

# Redis Configuration
redis_client = redis.Redis(
    host='redis-15440.c93.us-east-1-3.ec2.redns.redis-cloud.com',
    port=15440,
    decode_responses=True,
    username="default",
    password="Af1Y9RyLA2mSlpuEfoR99YfvBx0YmRvS"
)

# Initialize Pyrogram client with plugins
telegram_app = Client(
    "ytdlp_bot", 
    api_id=API_ID, 
    api_hash=API_HASH, 
    bot_token=BOT_TOKEN,
    plugins=dict(root="plugins")
)

def load_admin_ids():
    """Load admin user IDs from admin.txt"""
    try:
        with open('admin.txt', 'r') as f:
            return [int(line.strip()) for line in f if line.strip().isdigit()]
    except FileNotFoundError:
        return []

def generate_token():
    """Generate a 10-character alphanumeric token"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=10))

def is_admin(user_id):
    """Check if user is admin"""
    admin_ids = load_admin_ids()
    return int(user_id) in admin_ids

async def get_user_token(user_id):
    """Get user's token"""
    return redis_client.get(f"user_token:{user_id}")

async def set_user_token(user_id, token):
    """Set user's token"""
    redis_client.set(f"user_token:{user_id}", token)
    redis_client.set(f"token_user:{token}", user_id)

async def revoke_user_token(user_id):
    """Revoke user's token"""
    old_token = redis_client.get(f"user_token:{user_id}")
    if old_token:
        redis_client.delete(f"token_user:{old_token}")
    redis_client.delete(f"user_token:{user_id}")

def get_user_by_token(token):
    """Get user ID by token"""
    user_id = redis_client.get(f"token_user:{token}")
    return int(user_id) if user_id else None

async def get_user_request_count(user_id):
    """Get user's daily request count"""
    return int(redis_client.get(f"user_requests:{user_id}") or 0)

async def set_user_request_count(user_id, count):
    """Set user's daily request count"""
    redis_client.setex(f"user_requests:{user_id}", 86400, count)  # 24 hours TTL

async def increment_user_requests(user_id):
    """Increment user's daily request count"""
    key = f"user_requests:{user_id}"
    current = int(redis_client.get(key) or 0)
    redis_client.setex(key, 86400, current + 1)
    return current + 1

async def start_bot():
    """Start the Telegram bot"""
    await telegram_app.start()
    print("✅ Telegram bot started successfully!")
    print("🔌 Plugins loaded from plugins/ directory")
    
    # Send startup message to channel
    try:
        await telegram_app.send_message(
            CHANNEL, 
            "🤖 YT-DLP API Bot is now online!\n\n"
            "✨ Features:\n"
            "• Interactive buttons\n"
            "• Token management\n"
            "• Usage tracking\n"
            "• Admin panel\n\n"
            "Use /start to get your API token!"
        )
    except Exception as e:
        print(f"Could not send startup message: {e}")

async def stop_bot():
    """Stop the Telegram bot"""
    await telegram_app.stop()
    print("🛑 Telegram bot stopped")

app = FastAPI(title="yt-dlp API", description="Optimized API for YouTube info with cookies support and Telegram bot integration")

# Rate limiting storage - tracks daily requests per IP (fallback)
daily_request_counts = defaultdict(lambda: {"count": 0, "date": datetime.date.today()})
DAILY_LIMIT = 1000
ADMIN_LIMIT = 10000

async def get_current_user(authorization: Optional[str] = Header(None)):
    """Get current user from token"""
    if not authorization:
        return None
    
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            return None
        
        user_id = get_user_by_token(token)
        return user_id
    except:
        return None

async def require_token(authorization: Optional[str] = Header(None)):
    """Require valid token for protected endpoints"""
    user_id = await get_current_user(authorization)
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "Token required",
                "message": "Please get your token from @YourBotUsername on Telegram using /start command"
            }
        )
    return user_id

class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for search endpoints and health check
        if request.url.path in ["/search", "/health", "/clear-cache", "/rate-limit-status"]:
            return await call_next(request)
        
        # Check for token authentication
        authorization = request.headers.get("authorization")
        user_id = await get_current_user(authorization)
        
        if not user_id:
            return JSONResponse(
                status_code=401,
                content={
                    "error": "Token required",
                    "message": "Please get your token from the Telegram bot using /start command"
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
executor = ThreadPoolExecutor(max_workers=4)

# Disable yt-dlp logging for better performance
logging.getLogger('yt_dlp').setLevel(logging.ERROR)

# Cache video info for 5 minutes to avoid repeated requests
@lru_cache(maxsize=100)
def get_cached_info(url: str, cache_key: int):
    """Cache wrapper - cache_key changes every 5 minutes"""
    return _extract_info(url)

def _extract_info(url: str):
    """Extract only essential video information using Chrome cookies - optimized"""
    ydl_opts = {
        # Only get what we need - much faster
        "format": "best[height<=720]",  # Limit quality for faster processing
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "cookiesfrombrowser": ("chrome",),
        
        # Performance optimizations
        "extract_flat": False,  # We need full info
        "writethumbnail": False,
        "writeinfojson": False,
        "writedescription": False,
        "writesubtitles": False,
        "writeautomaticsub": False,
        
        # Faster format selection
        "format_sort": ["res:720", "fps", "br"],
        "format_sort_force": True,
        
        # Network optimizations  
        "http_chunk_size": 10485760,  # 10MB chunks
        "retries": 1,  # Reduce retries for speed
        "fragment_retries": 1,
        
        # Skip unnecessary processing
        "skip_playlist_after_errors": 1,
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        return ydl.extract_info(url, download=False)

def _search_videos(query: str, max_results: int = 5):
    """Search YouTube videos by query"""
    search_url = f"ytsearch{max_results}:{query}"
    
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "cookiesfrombrowser": ("chrome",),
        "extract_flat": True,  # Only get basic info for search
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

def extract_best_format_url(formats):
    """Optimized format URL extraction"""
    if not formats:
        return None
    
    # Priority: combined format > video+audio > video only
    for f in formats:
        if (f.get("acodec") != "none" and 
            f.get("vcodec") != "none" and 
            f.get("url")):
            return f.get("url")
    
    # Fallback to first available URL
    for f in formats:
        if f.get("url"):
            return f.get("url")
    
    return None

@app.get("/info")
async def video_info(
    q: str = Query(..., description="YouTube video URL or search query"),
    max_results: int = Query(1, description="Max results for search queries", ge=1, le=10),
    user_id: int = Depends(require_token)
):
    start_time = time.time()
    
    try:
        if is_youtube_url(q):
            # Handle as URL
            info = await extract_video_info_async(q)
            format_url = extract_best_format_url(info.get("formats", []))
            
            elapsed = round(time.time() - start_time, 2)
            
            return JSONResponse(content={
                "query_type": "url",
                "title": info.get("title"),
                "duration": info.get("duration"),
                "youtube_link": info.get("webpage_url"),
                "channel_name": info.get("uploader"),
                "views": info.get("view_count"),
                "video_id": info.get("id"),
                "url": format_url,
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
                format_url = extract_best_format_url(detailed_info.get("formats", []))
                
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
                    "url": format_url,
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
    max_results: int = Query(5, description="Number of results to return", ge=1, le=20)
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
                "thumbnail": entry.get("thumbnail")
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
async def rate_limit_status(user_id: Optional[int] = Depends(get_current_user)):
    """Check current rate limit status"""
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
            "message": "Please get your token from the Telegram bot using /start command",
            "auth_method": "none"
        }

# Optional: Clear cache endpoint
@app.post("/clear-cache")
async def clear_cache():
    """Clear both info and search caches"""
    get_cached_info.cache_clear()
    get_cached_search_results.cache_clear()
    return {"message": "All caches cleared"}

@app.on_event("startup")
async def startup_event():
    """Start the Telegram bot when FastAPI starts"""
    try:
        await start_bot()
        print("✅ FastAPI and Telegram bot started successfully!")
    except Exception as e:
        print(f"❌ Failed to start Telegram bot: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Stop the Telegram bot when FastAPI shuts down"""
    try:
        await stop_bot()
        print("✅ Telegram bot stopped successfully!")
    except Exception as e:
        print(f"❌ Error stopping Telegram bot: {e}")

if __name__ == "__main__":
    print("🚀 Starting YT-DLP API with Telegram Bot...")
    uvicorn.run(app, host="0.0.0.0", port=5000)

# Optional: Batch processing endpoint
@app.post("/batch-info")
async def batch_video_info(urls: list[str], user_id: int = Depends(require_token)):
    """Process multiple URLs concurrently"""
    start_time = time.time()
    
    try:
        # Process all URLs concurrently
        tasks = [extract_video_info_async(url) for url in urls[:5]]  # Limit to 5 URLs
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    "url": urls[i],
                    "error": str(result)
                })
            else:
                format_url = extract_best_format_url(result.get("formats", []))
                processed_results.append({
                    "url": urls[i],
                    "title": result.get("title"),
                    "duration": result.get("duration"),
                    "youtube_link": result.get("webpage_url"),
                    "channel_name": result.get("uploader"),
                    "views": result.get("view_count"),
                    "video_id": result.get("id"),
                    "stream_url": format_url,
                })
        
        elapsed = round(time.time() - start_time, 2)
        return JSONResponse(content={
            "results": processed_results,
            "total_time": f"{elapsed} sec"
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
