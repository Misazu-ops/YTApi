from fastapi import FastAPI, Query, BackgroundTasks, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.base import BaseHTTPMiddleware
import yt_dlp
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
import logging
import re
from collections import defaultdict
import datetime

app = FastAPI(title="yt-dlp API", description="Optimized API for YouTube info with cookies support")

# Rate limiting storage - tracks daily requests per IP
daily_request_counts = defaultdict(lambda: {"count": 0, "date": datetime.date.today()})
DAILY_LIMIT = 1000

class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for search endpoints and health check
        if request.url.path in ["/search", "/health", "/clear-cache"]:
            return await call_next(request)
        
        client_ip = request.client.host
        today = datetime.date.today()
        
        # Reset counter if it's a new day
        if daily_request_counts[client_ip]["date"] != today:
            daily_request_counts[client_ip] = {"count": 0, "date": today}
        
        # Check if user has exceeded daily limit
        if daily_request_counts[client_ip]["count"] >= DAILY_LIMIT:
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Daily limit exceeded",
                    "message": f"You have exceeded the daily limit of {DAILY_LIMIT} requests. Search functionality remains free.",
                    "remaining_requests": 0,
                    "reset_time": "Resets at midnight UTC"
                }
            )
        
        # Process the request
        response = await call_next(request)
        
        # Increment counter only for successful data requests (not errors)
        if response.status_code == 200:
            daily_request_counts[client_ip]["count"] += 1
        
        # Add rate limit headers to response
        remaining = DAILY_LIMIT - daily_request_counts[client_ip]["count"]
        response.headers["X-RateLimit-Limit"] = str(DAILY_LIMIT)
        response.headers["X-RateLimit-Remaining"] = str(max(0, remaining))
        response.headers["X-RateLimit-Reset"] = str(int((datetime.datetime.combine(today + datetime.timedelta(days=1), datetime.time.min).timestamp())))
        
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
    max_results: int = Query(1, description="Max results for search queries", ge=1, le=10)
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
async def rate_limit_status(request: Request):
    """Check current rate limit status for the requesting IP"""
    client_ip = request.client.host
    today = datetime.date.today()
    
    # Reset counter if it's a new day
    if daily_request_counts[client_ip]["date"] != today:
        daily_request_counts[client_ip] = {"count": 0, "date": today}
    
    used = daily_request_counts[client_ip]["count"]
    remaining = DAILY_LIMIT - used
    
    return {
        "daily_limit": DAILY_LIMIT,
        "requests_used": used,
        "requests_remaining": max(0, remaining),
        "reset_time": "Resets at midnight UTC",
        "client_ip": client_ip
    }

# Optional: Clear cache endpoint
@app.post("/clear-cache")
async def clear_cache():
    """Clear both info and search caches"""
    get_cached_info.cache_clear()
    get_cached_search_results.cache_clear()
    return {"message": "All caches cleared"}

# Optional: Batch processing endpoint
@app.post("/batch-info")
async def batch_video_info(urls: list[str]):
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
