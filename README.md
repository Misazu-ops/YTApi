# yt-dlp API with Telegram Bot

A FastAPI-based web service that provides an optimized interface to yt-dlp for extracting YouTube video information with cookies support and integrated Telegram bot for token management.

## Features

- **Video Info Extraction**: Get detailed information about YouTube videos including title, duration, views, and streaming URLs
- **Search Functionality**: Search YouTube and get video results (no rate limit)
- **Cookie Support**: Uses Chrome browser cookies for enhanced access
- **Caching**: Built-in LRU caching system with time-based expiration for improved performance
- **Batch Processing**: Process multiple URLs concurrently (up to 5 URLs)
- **Optimized Performance**: Thread pool execution and format optimization for faster responses
- **Telegram Bot Integration**: Token-based authentication and user management via Telegram
- **Rate Limiting**: Per-user daily request limits with admin controls
- **Redis Storage**: User tokens and request counts stored in Redis for persistence

## API Endpoints

### `/info`
Get video information or search results
- **Parameter**: `q` (required) - YouTube URL or search query
- **Parameter**: `max_results` (optional) - Maximum results for search queries (1-10, default: 1)
- **Parameter**: `token` (required) - Your API token

### `/search`
Search YouTube videos without detailed info extraction - **FREE (no rate limit)**
- **Parameter**: `q` (required) - Search query
- **Parameter**: `max_results` (optional) - Number of results (1-20, default: 5)
- No authentication required

### `/batch-info`
Process multiple YouTube URLs concurrently (POST)
- **Body**: JSON array of URLs (max 5)
- **Parameter**: `token` (required) - Your API token

### `/health`
Health check endpoint (no authentication required)

### `/rate-limit-status`
Check current rate limit status
- **Parameter**: `token` (optional) - Your API token

### `/clear-cache`
Clear all caches (POST, no authentication required)

## Telegram Bot Commands

- `/start` - Generate API token and get welcome message
- `/menu` - Show main menu with options
- `/status` - Check usage statistics and view progress bar
- `/token` - View your API token
- `/admin` - Admin panel (admin users only)

### Admin Commands
- `/stats` - View bot statistics
- `/user <user_id>` - Get user information
- `/grant <user_id> <amount>` - Grant extra requests
- `/revoke <user_id>` - Revoke user token
- `/listusers` - List recent users
- `/adminhelp` - Show admin help message

## Installation & Setup

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Set up environment variables or update main.py:**
   - `API_ID` - Telegram API ID (currently: 21869707)
   - `API_HASH` - Telegram API Hash
   - `BOT_TOKEN` - Telegram Bot Token
   - `REDIS_URL` - Redis connection URL (optional, defaults to localhost)

3. **Run the application:**
```bash
python main.py
```

The API will be available at `http://0.0.0.0:8000`

## Authentication

Get your API token by messaging the Telegram bot with `/start`. Use the token as a query parameter:

```
?token=YOUR_TOKEN
```

## Usage Examples

### Get video info by URL:
```bash
curl "http://localhost:8000/info?token=YOUR_TOKEN&q=https://youtube.com/watch?v=VIDEO_ID"
```

### Search for videos (no token required):
```bash
curl "http://localhost:8000/search?q=python tutorial&max_results=5"
```

### Get detailed info from search:
```bash
curl "http://localhost:8000/info?token=YOUR_TOKEN&q=python tutorial&max_results=1"
```

### Batch processing:
```bash
curl -X POST \
     -H "Content-Type: application/json" \
     -d '["https://youtube.com/watch?v=VIDEO1", "https://youtube.com/watch?v=VIDEO2"]' \
     "http://localhost:8000/batch-info?token=YOUR_TOKEN"
```

### Check rate limit status:
```bash
curl "http://localhost:8000/rate-limit-status?token=YOUR_TOKEN"
```

## Rate Limits

- **Regular Users**: 1,000 requests per day for data endpoints
- **Admin Users**: 10,000 requests per day for data endpoints
- **Search endpoint**: Unlimited for all users
- Limits reset at midnight UTC
- Rate limit headers included in responses

## Performance Features

- **Caching**: LRU caching with 5-minute expiration for video info and 10-minute for search
- **Concurrency**: Thread pool execution for non-blocking operations
- **Optimization**: yt-dlp configured for faster extraction (720p max, reduced retries)
- **Format Selection**: Intelligent format URL extraction with fallbacks
- **Cookie Integration**: Chrome browser cookies for enhanced access
- **Redis Backend**: Persistent storage for user management and rate limiting

## Response Format

### Video Info Response:
```json
{
  "query_type": "url",
  "title": "Video Title",
  "duration": 180,
  "youtube_link": "https://youtube.com/watch?v=VIDEO_ID",
  "channel_name": "Channel Name",
  "views": 1000000,
  "video_id": "VIDEO_ID",
  "url": "https://streaming-url.com",
  "time_taken": "1.2 sec"
}
```

### Search Response:
```json
{
  "query": "search term",
  "results": [
    {
      "title": "Video Title",
      "video_id": "VIDEO_ID",
      "channel_name": "Channel Name",
      "duration": 180,
      "views": 1000000,
      "youtube_link": "https://youtube.com/watch?v=VIDEO_ID",
      "thumbnail": "https://thumbnail-url.jpg"
    }
  ],
  "total_results": 1,
  "time_taken": "0.8 sec"
}
```

## Admin Features

Admins can:
- View comprehensive bot statistics
- Manage user tokens and permissions
- Grant additional requests to users
- View user information and usage
- Access admin panel via `/admin` command
- List recent users and activity

## Requirements

- Python 3.8+
- Chrome browser (for cookie support)
- Redis server (local or remote)
- Telegram Bot Token and API credentials
- yt-dlp library with dependencies

## Environment Setup

Create environment variables or update the constants in main.py:
```python
API_ID = your_telegram_api_id
API_HASH = "your_telegram_api_hash"
BOT_TOKEN = "your_bot_token"
GROUP = "your_telegram_group"
CHANNEL = "your_telegram_channel"
```

## File Structure

```
├── main.py              # Main FastAPI application
├── tools.py             # Shared utilities and Redis functions
├── plugins/             # Telegram bot command handlers
│   ├── __init__.py
│   ├── commands.py      # Basic bot commands
│   ├── status.py        # Status and token management
│   └── admin.py         # Admin commands
├── requirements.txt     # Python dependencies
└── README.md           # This file
```

## Error Handling

The API includes comprehensive error handling:
- Invalid URLs or search queries
- Rate limit exceeded responses
- Token validation errors
- yt-dlp extraction failures
- Network timeout handling

## Security Features

- Token-based authentication
- Rate limiting per user
- Admin privilege separation
- Redis-backed session management
- Input validation and sanitization

## License

MIT License

# Dockerfile

FROM python:3.9-slim-buster

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Expose port (FastAPI runs on port 8000)
EXPOSE 8000

# Health check for FastAPI endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application (both FastAPI and Telegram bot)
CMD ["python3", "main.py"]