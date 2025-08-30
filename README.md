
# yt-dlp API with Telegram Bot

A FastAPI-based web service that provides an optimized interface to yt-dlp for extracting YouTube video information with cookies support and integrated Telegram bot for token management.

## Features

- **Video Info Extraction**: Get detailed information about YouTube videos including title, duration, views, and streaming URLs
- **Search Functionality**: Search YouTube and get video results
- **Cookie Support**: Uses Chrome browser cookies for enhanced access
- **Caching**: Built-in caching system to improve performance
- **Batch Processing**: Process multiple URLs concurrently
- **Optimized Performance**: Thread pool execution and format optimization for faster responses
- **Telegram Bot Integration**: Token-based authentication and user management via Telegram
- **Rate Limiting**: Per-user daily request limits with admin controls
- **Redis Storage**: User tokens and request counts stored in Redis

## API Endpoints

### `/info`
Get video information or search results
- **Parameter**: `q` (required) - YouTube URL or search query
- **Parameter**: `max_results` (optional) - Maximum results for search queries (1-10, default: 1)
- **Headers**: `Authorization: Bearer YOUR_TOKEN` (required)

### `/search`
Search YouTube videos without detailed info extraction
- **Parameter**: `q` (required) - Search query
- **Parameter**: `max_results` (optional) - Number of results (1-20, default: 5)
- **Headers**: `Authorization: Bearer YOUR_TOKEN` (required)

### `/batch-info`
Process multiple YouTube URLs concurrently (POST)
- **Body**: JSON array of URLs (max 5)
- **Headers**: `Authorization: Bearer YOUR_TOKEN` (required)

### `/health`
Health check endpoint (no authentication required)

### `/rate-limit-status`
Check current rate limit status
- **Headers**: `Authorization: Bearer YOUR_TOKEN` (optional)

### `/clear-cache`
Clear all caches (POST, no authentication required)

## Telegram Bot Commands

- `/start` - Generate API token and get welcome message
- `/menu` - Show main menu with options
- `/status` - Check usage statistics
- `/token` - View your API token
- `/admin` - Admin panel (admin users only)

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables:
   - `API_ID` - Telegram API ID
   - `API_HASH` - Telegram API Hash
   - `BOT_TOKEN` - Telegram Bot Token
   - `REDIS_URL` - Redis connection URL (optional, defaults to localhost)

3. Run the application:
```bash
python main.py
```

The API will be available at `http://0.0.0.0:5000`

## Authentication

Get your API token by messaging the Telegram bot with `/start`. Use the token in the Authorization header:

```
Authorization: Bearer YOUR_TOKEN
```

## Usage Examples

### Get video info by URL:
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
     "http://localhost:5000/info?q=https://youtube.com/watch?v=VIDEO_ID"
```

### Search for videos:
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
     "http://localhost:5000/info?q=python tutorial&max_results=5"
```

### Batch processing:
```bash
curl -X POST \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '["https://youtube.com/watch?v=VIDEO1", "https://youtube.com/watch?v=VIDEO2"]' \
     "http://localhost:5000/batch-info"
```

## Rate Limits

- **Regular Users**: 1,000 requests per day
- **Admin Users**: 10,000 requests per day
- Limits reset at midnight UTC

## Performance Features

- LRU caching with time-based expiration
- Thread pool execution for non-blocking operations
- Optimized yt-dlp configuration for faster extraction
- Format selection limited to 720p for better performance
- Chrome cookie integration for enhanced access
- Redis-based user management and rate limiting

## Admin Features

Admins can:
- View bot statistics
- Manage user tokens
- Grant additional requests
- View user information
- Access admin panel via `/admin` command

## Requirements

- Python 3.8+
- Chrome browser (for cookie support)
- Redis server
- Telegram Bot Token and API credentials

## Environment Setup

Create a `.env` file or set environment variables:
```
API_ID=your_telegram_api_id
API_HASH=your_telegram_api_hash
BOT_TOKEN=your_bot_token
REDIS_URL=redis://localhost:6379/0
```

## License

MIT License
