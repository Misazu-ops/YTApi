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
import redis
import string
import random
from tools import (
    redis_client, generate_token, is_admin, get_user_token, 
    set_user_token, revoke_user_token, get_user_by_token,
    get_user_request_count, set_user_request_count, increment_user_requests
)

app = FastAPI(title="yt-dlp API", description="Optimized API for YouTube info with cookies support and Telegram bot integration")

@app.get("/")
async def read_root():
    return FileResponse("index.html")

# ...existing API endpoints and logic...

def run_api():
    print("🌐 Starting FastAPI server on http://0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info", loop="asyncio")

if __name__ == "__main__":
    run_api()
