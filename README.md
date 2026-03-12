# YouTubeMusic

Async YouTube Music search and stream extraction library for Python.

Designed for developers who need fast YouTube search, metadata extraction,
playlist parsing, and direct stream URLs — without mandatory API keys.

---

## Features

- Fully async architecture
- YouTube search (scraping-based)
- Optional YouTube Data API search
- Audio stream extraction (powered by yt-dlp)
- Video + audio stream support
- Playlist & Mix support
- Built-in CLI
- No forced external services
- Production-ready design
- No console output on import

---

## Installation

```bash
pip install YouTubeMusic
```

---

## Quick Start

### Basic Search

```python
import asyncio
from YouTubeMusic.Search import Search

async def main():
    results = await Search("Kesariya", limit=1)

    if results and results.get("main_results"):
        item = results["main_results"][0]
        print(item)

asyncio.run(main())
```

---

### Get Audio Stream URL

```python
import asyncio
from YouTubeMusic.Stream import get_stream
cookies_path = ""

async def main():
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    stream_url = await get_stream(url, cookies_path)
    print(stream_url)

asyncio.run(main())
```

---

### Search Using YouTube Data API (Optional)

If you want to use official YouTube API:

Set environment variable:

```bash
export YOUTUBE_API_KEYS="key1,key2,key3"
```

Then:

```python
import asyncio
from YouTubeMusic.YtSearch import Search as YtSearch

async def main():
    results = await YtSearch("Kesariya", limit=1)
    print(results)

asyncio.run(main())
```

If no API key is configured, it safely returns an empty list.

---

### Get Playlist Songs

```python
import asyncio
from YouTubeMusic.Playlist import get_playlist_songs

async def main():
    songs = await get_playlist_songs(
        "https://www.youtube.com/playlist?list=PLxxxxxxxx"
    )
    print(len(songs))

asyncio.run(main())
```

---

### Extract Video + Audio URLs

```python
import asyncio
from YouTubeMusic.Video_Stream import get_video_audio_urls
cookies_path = ""
async def main():
    video_url, audio_url = await get_video_audio_urls(
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ", cookies_path
    )
    print(video_url)
    print(audio_url)

asyncio.run(main())
```

---

## CLI Usage

After installation:

### Basic Search

```bash
ytmusic "Kesariya"
```

### Extract Audio Stream (requires cookies file)

```bash
ytmusic "Kesariya" --stream --cookies cookies.txt
```

### Show Package Info

```bash
ytmusic --info
```

---

## Special Thanks

Special thanks to the **yt-dlp** project for providing reliable and powerful
media extraction capabilities used internally for stream URL handling.

yt-dlp is an open-source project maintained by its contributors.
Learn more at: https://github.com/yt-dlp/yt-dlp

p
---

## Why Use YouTubeMusic?

- No mandatory YouTube API usage
- Fully async and scalable
- Lightweight and modular
- Suitable for Telegram bots, web apps, and automation
- Clean public API
- No forced logging
- Production-safe design

---

## Requirements

- Python 3.8+
- httpx (with http2)
- orjson
- yt-dlp

---

## Project Structure

```
YouTubeMusic/
    Search.py
    YtSearch.py
    Stream.py
    Video_Stream.py
    Playlist.py
    Models.py
    Utils.py
    cli.py
```

---

## License

MIT License

---

## Repository

https://github.com/YouTubeMusicAPI/YouTubeMusic

---

## Author

Abhishek Thakur
