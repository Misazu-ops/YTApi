
# yt-dlp API

A FastAPI-based web service that provides an optimized interface to yt-dlp for extracting YouTube video information with cookies support.

## Features

- **Video Info Extraction**: Get detailed information about YouTube videos including title, duration, views, and streaming URLs
- **Search Functionality**: Search YouTube and get video results
- **Cookie Support**: Uses Chrome browser cookies for enhanced access
- **Caching**: Built-in caching system to improve performance
- **Batch Processing**: Process multiple URLs concurrently
- **Optimized Performance**: Thread pool execution and format optimization for faster responses

## API Endpoints

### `/info`
Get video information or search results
- **Parameter**: `q` (required) - YouTube URL or search query
- **Parameter**: `max_results` (optional) - Maximum results for search queries (1-10, default: 1)

### `/search`
Search YouTube videos without detailed info extraction
- **Parameter**: `q` (required) - Search query
- **Parameter**: `max_results` (optional) - Number of results (1-20, default: 5)

### `/batch-info`
Process multiple YouTube URLs concurrently (POST)
- **Body**: JSON array of URLs (max 5)

### `/health`
Health check endpoint

### `/clear-cache`
Clear all caches (POST)

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the application:
```bash
uvicorn main:app --host 0.0.0.0 --port 5000
```

## Usage Examples

### Get video info by URL:
```
GET /info?q=https://youtube.com/watch?v=VIDEO_ID
```

### Search for videos:
```
GET /info?q=python tutorial&max_results=5
```

### Health check:
```
GET /health
```

## Performance Features

- LRU caching with 5-minute TTL
- Thread pool execution for non-blocking operations
- Optimized yt-dlp configuration for faster extraction
- Format selection limited to 720p for better performance
- Chrome cookie integration for enhanced access

## Requirements

- Python 3.8+
- Chrome browser (for cookie support)
- FastAPI
- yt-dlp
- uvicorn

## License

MIT License
