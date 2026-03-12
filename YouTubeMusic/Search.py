from urllib.parse import quote_plus, quote
import httpx
import re
import orjson
import asyncio
import os

UPSTASH_REDIS_REST_URL = os.getenv("UPSTASH_REDIS_REST_URL")
UPSTASH_REDIS_REST_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN")

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "en-US,en;q=0.9",
}

YOUTUBE_SEARCH_URL = "https://www.youtube.com/results?search_query={}"
YOUTUBE_TRENDING_URL = "https://www.youtube.com/feed/trending"

YT_REGEX = re.compile(r"ytInitialData\s*=\s*(\{.+?\});", re.DOTALL)

_client = httpx.AsyncClient(http2=True, timeout=15, headers=HEADERS)

MEMORY_CACHE = {}
LOCKS = {}


# ---------------- COMMON HELPERS ----------------

def normalize(q: str) -> str:
    return re.sub(r"\s+", " ", q.lower().strip())


def format_views(text: str) -> str:
    return text.replace(" views", "").replace(" view", "")


def extract_channel_name(v: dict) -> str:
    for key in ("ownerText", "longBylineText", "shortBylineText"):
        data = v.get(key, {})
        if data.get("runs"):
            return data["runs"][0].get("text", "Unknown")
    return "Unknown"


def safe_get(obj, *keys):
    for key in keys:
        if not isinstance(obj, dict):
            return {}
        obj = obj.get(key, {})
    return obj


async def fetch_yt_data(url: str):
    r = await _client.get(url)
    match = YT_REGEX.search(r.text)
    if not match:
        return None
    return orjson.loads(match.group(1))


# ---------------- REDIS ----------------

async def redis_get(key: str):
    if not UPSTASH_REDIS_REST_URL or not UPSTASH_REDIS_REST_TOKEN:
        return None

    try:
        headers = {"Authorization": f"Bearer {UPSTASH_REDIS_REST_TOKEN}"}
        key = quote(key)

        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                f"{UPSTASH_REDIS_REST_URL}/get/{key}",
                headers=headers,
            )

        if r.status_code == 200:
            return r.json().get("result")
    except Exception:
        pass

    return None


async def redis_set(key: str, value):
    if not UPSTASH_REDIS_REST_URL or not UPSTASH_REDIS_REST_TOKEN:
        return

    try:
        headers = {"Authorization": f"Bearer {UPSTASH_REDIS_REST_TOKEN}"}
        key = quote(key)

        if isinstance(value, bytes):
            value = value.decode()

        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(
                f"{UPSTASH_REDIS_REST_URL}/set/{key}",
                headers=headers,
                json={"value": value},
            )
    except Exception:
        pass


async def close_client():
    await _client.aclose()


# ---------------- SEARCH ----------------

async def Search(query: str, limit: int = 1):
    if not query:
        return {"main_results": [], "suggested": []}

    qkey = "search_" + normalize(query)

    if qkey in MEMORY_CACHE:
        return MEMORY_CACHE[qkey]

    cached = await redis_get(qkey)
    if cached:
        data = orjson.loads(cached.encode())
        MEMORY_CACHE[qkey] = data
        return data

    lock = LOCKS.setdefault(qkey, asyncio.Lock())

    async with lock:
        try:
            url = YOUTUBE_SEARCH_URL.format(quote_plus(query))
            raw = await fetch_yt_data(url)

            if not raw:
                return {"main_results": [], "suggested": []}

            contents = safe_get(
                raw,
                "contents",
                "twoColumnSearchResultsRenderer",
                "primaryContents",
                "sectionListRenderer",
                "contents",
            )

            results = []

            for section in contents:
                items = safe_get(section, "itemSectionRenderer", "contents")

                for item in items:
                    v = item.get("videoRenderer")
                    if not v:
                        continue

                    video_id = v.get("videoId")
                    if not video_id:
                        continue

                    title_data = safe_get(v, "title", "runs")
                    title = title_data[0]["text"] if title_data else "Unknown"

                    results.append({
                        "title": title,
                        "video_id": video_id,
                        "url": f"https://www.youtube.com/watch?v={video_id}",
                        "duration": v.get("lengthText", {}).get("simpleText", "LIVE"),
                        "channel": extract_channel_name(v),
                        "views": format_views(
                            v.get("viewCountText", {}).get("simpleText", "0 views")
                        ),
                        "thumbnail": f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
                    })

                    if len(results) >= limit + 5:
                        break

            output = {
                "main_results": results[:limit],
                "suggested": results[limit : limit + 5],
            }

            MEMORY_CACHE[qkey] = output
            await redis_set(qkey, orjson.dumps(output))

            return output

        finally:
            LOCKS.pop(qkey, None)


# ---------------- TRENDING MUSIC (STABLE METHOD) ----------------

# ---------------- TRENDING MUSIC (STABLE SEARCH BASED) ----------------

async def Trending(limit: int = 10):

    key = "trending_music_search"

    if key in MEMORY_CACHE:
        return MEMORY_CACHE[key]

    cached = await redis_get(key)
    if cached:
        data = orjson.loads(cached.encode())
        MEMORY_CACHE[key] = data
        return data

    # Use search instead of feed scraping
    trending_query = "music trending india"

    data = await Search(trending_query, limit=limit)

    if not data or not data.get("main_results"):
        return []

    results = data.get("main_results", []) + data.get("suggested", [])
    results = results[:limit]

    MEMORY_CACHE[key] = results
    await redis_set(key, orjson.dumps(results))

    return results
    
# ---------------- SUGGEST ----------------

async def Suggest(query: str, limit: int = 10):
    data = await Search(query, limit=limit)
    return data.get("suggested", [])


__all__ = ["Search", "Trending", "Suggest", "close_client"]
