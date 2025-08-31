
# YT-DLP API with Telegram Bot

A FastAPI-based web service that provides an optimized interface to yt-dlp for extracting YouTube video information with cookies support and integrated Telegram bot for token management.

## Features

- 🚀 Fast YouTube video info extraction using yt-dlp
- 🤖 Integrated Telegram bot for token management
- 🔒 Token-based authentication system
- 📊 Rate limiting (1000 requests/day for users, 10000 for admins)
- 🔍 Free unlimited search functionality
- 🎯 Chrome cookie support for enhanced access
- 📈 Redis-backed user management
- ⚡ Concurrent batch processing
- 🛡️ Admin panel with user management
- 📱 Interactive Telegram bot interface

## API Endpoints

### `/info`
Extract detailed video information or search YouTube
- **Parameter**: `q` (required) - YouTube URL or search query
- **Parameter**: `max_results` (optional) - For search queries (1-10, default: 1)
- **Parameter**: `token` (required) - Your API token
- **Rate limit**: Counted towards daily limit

### `/search`
Search YouTube videos without detailed info extraction - **FREE (no rate limit)**
- **Parameter**: `q` (required) - Search query
- **Parameter**: `max_results` (optional) - Number of results (1-20, default: 5)
- No authentication required

### `/batch-info`
Process multiple YouTube URLs concurrently (POST)
- **Body**: JSON array of URLs (max 5)
- **Parameter**: `token` (required) - Your API token
- **Rate limit**: Each URL counts towards daily limit

### `/health`
Health check endpoint (no authentication required)

### `/rate-limit-status`
Check current rate limit status
- **Parameter**: `token` (optional) - Your API token

### `/clear-cache`
Clear all caches (POST, no authentication required)

## Response Examples

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

## Telegram Bot Commands

### User Commands
- `/start` - Generate API token and get welcome message
- `/menu` - Show main menu with interactive buttons
- `/status` - Check usage statistics with progress bar
- `/token` - View your current API token

### Admin Commands
- `/stats` - View comprehensive bot statistics
- `/user <user_id>` - Get detailed user information
- `/grant <user_id> <amount>` - Grant extra requests to users
- `/revoke <user_id>` - Revoke user's token
- `/listusers` - List recent users and their activity
- `/adminhelp` - Show admin command reference

## Installation & Setup

### Local Installation

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Set up Redis connection in tools.py:**
```python
redis_client = redis.Redis(
    host='your_redis_host',
    port=your_redis_port,
    username="your_username",
    password="your_password"
)
```

3. **Create admin.txt file with admin user IDs:**
```
123456789
987654321
```

4. **Run the application:**
```bash
python main.py
```

The API will be available at `http://0.0.0.0:8000`

### Docker Installation

1. **Build the Docker image:**
```bash
docker build --no-cache -t yt-dlp-api .
```

2. **Run with Chrome data mounting (recommended for cookie support):**
```bash
docker run -d --name yt-dlp-api -p 8000:8000 --mount type=bind,source=$HOME/.config/google-chrome,target=/root/.config/google-chrome yt-dlp-api
```

**Note about Chrome data mounting:**
- The Chrome data mounting allows yt-dlp to use your Chrome cookies for enhanced access to YouTube content
- The `:ro` flag ensures the container can only read the data, not modify it
- Make sure Chrome/Chromium is installed on your host system and you're logged into your accounts
- This is particularly useful for accessing age-restricted or region-locked content
- Without Chrome data, the API will still work but with limited access to some YouTube content

**Docker Management Commands:**
```bash
# View logs
docker logs yt-dlp-api

# Stop the container
docker stop yt-dlp-api

# Start the container
docker start yt-dlp-api

# Remove the container
docker rm yt-dlp-api

# Update and restart
docker stop yt-dlp-api && docker rm yt-dlp-api && docker rmi-f yt-dlp-api
docker build --no-cache -t yt-dlp-api .
docker run -d --name yt-dlp-api -p 8000:8000 --mount type=bind,source=$HOME/.config/google-chrome,target=/root/.config/google-chrome yt-dlp-api
```

## Authentication

Get your API token by messaging the Telegram bot with `/start`. Use the token as a query parameter:

```
?token=YOUR_TOKEN
```

## Usage Examples

### Get video info by URL:
```bash
curl "http://0.0.0.0:8000/info?token=YOUR_TOKEN&q=https://youtube.com/watch?v=VIDEO_ID"
```

### Search videos:
```bash
curl "http://0.0.0.0:8000/search?q=python tutorial&max_results=5"
```

### Check rate limit status:
```bash
curl "http://0.0.0.0:8000/rate-limit-status?token=YOUR_TOKEN"
```

### Batch processing:
```bash
curl -X POST "http://0.0.0.0:8000/batch-info?token=YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '["https://youtube.com/watch?v=VIDEO1", "https://youtube.com/watch?v=VIDEO2"]'
```

## File Structure

```
├── main.py              # Main FastAPI application with bot integration
├── tools.py             # Shared utilities and Redis functions
├── plugins/             # Telegram bot command handlers
│   ├── __init__.py      # Plugin initialization
│   ├── commands.py      # Basic bot commands and callbacks
│   ├── status.py        # Status and token management commands
│   └── admin.py         # Admin-only commands
├── requirements.txt     # Python dependencies
├── admin.txt           # Admin user IDs (one per line)
├── Dockerfile          # Docker configuration
└── README.md           # This documentation
```

## Dependencies

- **fastapi** - Web framework
- **uvicorn[standard]** - ASGI server
- **yt-dlp** - YouTube video extraction
- **python-multipart** - Form data support
- **pyrogram** - Telegram bot framework
- **tgcrypto** - Telegram encryption
- **redis** - Redis client for data storage

## Rate Limiting

- **Regular users**: 1000 requests per day
- **Admin users**: 10000 requests per day
- **Search endpoint**: Unlimited (free)
- **Reset time**: Midnight UTC daily

## Admin Features

Admins (defined in `admin.txt`) have access to:
- Enhanced rate limits (10x higher)
- User management commands
- Bot statistics and analytics
- Token management for all users
- Request quota adjustments
- User activity monitoring

## Error Handling

The API includes comprehensive error handling for:
- Invalid URLs or malformed requests
- Rate limit exceeded responses
- Token validation and authentication errors
- yt-dlp extraction failures and timeouts
- Network connectivity issues
- Redis connection problems

## Security Features

- **Token-based authentication** with secure random generation
- **Rate limiting** per authenticated user
- **Admin privilege separation** with file-based configuration
- **Redis-backed session management** with TTL
- **Input validation** and URL sanitization
- **Non-root Docker user** for container security

## Performance Optimizations

- **LRU caching** for video info and search results (5-10 minutes)
- **Thread pool execution** for CPU-bound yt-dlp operations
- **Concurrent batch processing** with asyncio
- **Chrome cookie integration** for enhanced access
- **Optimized yt-dlp settings** for faster extraction
- **Redis connection pooling** for database operations

## Monitoring & Health

- **Health check endpoint** at `/health`
- **Rate limit status endpoint** for usage monitoring
- **Admin statistics** for bot analytics
- **Docker health checks** with curl
- **Console logging** for debugging and monitoring

## License

MIT License

## Support

For support and questions:
- Use the Telegram bot's `/help` command
- Check the `/status` command for usage information
- Admins can use `/adminhelp` for management commands
