from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import from tools module
from tools import (
    redis_client, generate_token, is_admin, get_user_token, 
    set_user_token, revoke_user_token, get_user_request_count,
    set_user_request_count, increment_user_requests
)

@Client.on_message(filters.command("start"))
async def start_command(client: Client, message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name

    # Check if user already has a token
    existing_token = await get_user_token(user_id)

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔑 View Token", callback_data="view_token"),
            InlineKeyboardButton("📊 Usage Status", callback_data="usage_status")
        ],
        [
            InlineKeyboardButton("🔄 Revoke Token", callback_data="revoke_token"),
            InlineKeyboardButton("❓ Help", callback_data="help")
        ]
    ])

    if existing_token:
        await message.reply_text(
            f"🎉 **Welcome back, {username}!**\n\n"
            f"✅ Your API is ready to use!\n"
            f"🔗 Token: `{existing_token}`\n\n"
            f"🌐 **API Base URL:**\n"
            f"`http://api.nub-coder.tech/`\n\n"
            f"📝 **Usage:**\n"
            f"Add your token as a query parameter:\n"
            f"`http://api.nub-coder.tech/info?token={existing_token}&q=VIDEO_URL`\n\n"
            f"📈 **Daily Limit:** 1000 requests\n"
            f"🔍 **Search:** Always free!",
            reply_markup=keyboard
        )
    else:
        # Generate new token
        new_token = generate_token()
        await set_user_token(user_id, new_token)

        await message.reply_text(
            f"🎉 **Welcome to YT-DLP API, {username}!**\n\n"
            f"🔑 Your API token: `{new_token}`\n\n"
            f"🌐 **API Base URL:**\n"
            f"`http://api.nub-coder.tech/`\n\n"
            f"📝 **How to use:**\n"
            f"Add your token as a query parameter:\n"
            f"`http://api.nub-coder.tech/info?token={new_token}&q=VIDEO_URL`\n\n"
            f"📈 **Daily Limit:** 1000 requests\n"
            f"🔍 **Search:** Always free!\n\n"
            f"🚀 **Get started:** Use the buttons below!",
            reply_markup=keyboard
        )

@Client.on_message(filters.command("menu"))
async def menu_command(client: Client, message: Message):
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔑 View Token", callback_data="view_token"),
            InlineKeyboardButton("📊 Usage Status", callback_data="usage_status")
        ],
        [
            InlineKeyboardButton("🔄 Revoke Token", callback_data="revoke_token"),
            InlineKeyboardButton("❓ Help", callback_data="help")
        ],
        [
            InlineKeyboardButton("📖 API Docs", callback_data="api_docs")
        ]
    ])

    await message.reply_text(
        "🤖 **YT-DLP API Bot Menu**\n\n"
        "Choose an option below:",
        reply_markup=keyboard
    )

@Client.on_callback_query()
async def handle_callbacks(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    data = callback_query.data

    if data == "view_token":
        token = await get_user_token(user_id)
        if token:
            await callback_query.answer()
            await callback_query.edit_message_text(
                f"🔑 **Your API Token:**\n\n"
                f"`{token}`\n\n"
                f"📝 **Usage:**\n"
                f"```\n"
                f"http://api.nub-coder.tech/info?token={token}&q=VIDEO_URL\n"
                f"```\n\n"
                f"⚠️ Keep this token secure!",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_menu")]
                ])
            )
        else:
            await callback_query.answer("❌ No token found. Use /start to generate one.", show_alert=True)

    elif data == "usage_status":
        token = await get_user_token(user_id)
        if not token:
            await callback_query.answer("❌ No token found. Use /start to get one.", show_alert=True)
            return

        request_count = await get_user_request_count(user_id)
        limit = 10000 if is_admin(user_id) else 1000
        remaining = max(0, limit - request_count)

        status_text = (
            f"📊 **Usage Statistics**\n\n"
            f"🔑 Token: `{token}`\n"
            f"📈 Used today: **{request_count}**/{limit}\n"
            f"📉 Remaining: **{remaining}**\n"
            f"🕒 Reset: Midnight UTC\n"
        )

        if is_admin(user_id):
            status_text += "\n👑 **Admin privileges active**"

        # Progress bar
        progress = int((request_count / limit) * 10)
        bar = "🟩" * progress + "⬜" * (10 - progress)
        status_text += f"\n\n📊 Progress: {bar}"

        await callback_query.answer()
        await callback_query.edit_message_text(
            status_text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Refresh", callback_data="usage_status")],
                [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_menu")]
            ])
        )

    elif data == "revoke_token":
        await callback_query.answer()
        await callback_query.edit_message_text(
            "⚠️ **Are you sure?**\n\n"
            "This will revoke your current token and generate a new one.\n"
            "You'll need to update all your API calls with the new token.",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Yes, Revoke", callback_data="confirm_revoke"),
                    InlineKeyboardButton("❌ Cancel", callback_data="back_menu")
                ]
            ])
        )

    elif data == "confirm_revoke":
        # Revoke old token
        await revoke_user_token(user_id)

        # Generate new token
        new_token = generate_token()
        await set_user_token(user_id, new_token)

        await callback_query.answer("✅ Token revoked successfully!")
        await callback_query.edit_message_text(
            f"✅ **Token Revoked Successfully!**\n\n"
            f"🔑 Your new token: `{new_token}`\n\n"
            f"⚠️ **Important:** Update your API calls with the new token immediately.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_menu")]
            ])
        )

    elif data == "help":
        user_token = await get_user_token(user_id) or "YOUR_TOKEN"
        await callback_query.answer()
        await callback_query.edit_message_text(
            "❓ **Help & Commands**\n\n"
            "🤖 **Bot Commands:**\n"
            "• `/start` - Get your API token\n"
            "• `/menu` - Show main menu\n"
            "• `/status` - Check usage status\n"
            "• `/token` - View current token\n"
            "• `/revoke` - Revoke current token\n\n"
            "🌐 **API Base URL:**\n"
            "`http://api.nub-coder.tech/`\n\n"
            "🔗 **API Endpoints:**\n"
            "• `/info` - Get video info (requires token)\n"
            "• `/search` - Search videos (free)\n"
            "• `/batch-info` - Process multiple URLs\n"
            "• `/health` - Health check\n\n"
            "📝 **Usage:**\n"
            f"Example: `http://api.nub-coder.tech/info?token={user_token}&q=VIDEO_URL`\n\n"
            "🐍 **Python Example:**\n"
            "```python\n"
            "import requests\n"
            "response = requests.get(\n"
            "    'http://api.nub-coder.tech/info',\n"
            f"    params={{'token': '{user_token}', 'q': 'VIDEO_URL'}}\n"
            ")\n"
            "data = response.json()\n"
            "```",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📖 API Docs", callback_data="api_docs")],
                [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_menu")]
            ])
        )

    elif data == "api_docs":
        await callback_query.answer()
        await callback_query.edit_message_text(
            "📖 **API Documentation**\n\n"
            "🔗 **Base URL:** `http://api.nub-coder.tech/`\n\n"
            "📝 **Authentication:**\n"
            "Add your token as query parameter:\n"
            "```\n"
            "?token=YOUR_TOKEN\n"
            "```\n\n"
            "📊 **Rate Limits:**\n"
            "• Data endpoints: 1000/day\n"
            "• Search: Unlimited\n\n"
            "Select an endpoint to view detailed documentation:",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🎥 Video Info", callback_data="api_info"),
                    InlineKeyboardButton("🔍 Search", callback_data="api_search")
                ],
                [
                    InlineKeyboardButton("📦 Batch Processing", callback_data="api_batch"),
                    InlineKeyboardButton("📊 Rate Limit", callback_data="api_ratelimit")
                ],
                [
                    InlineKeyboardButton("❤️ Health Check", callback_data="api_health")
                ],
                [
                    InlineKeyboardButton("🔙 Back to Menu", callback_data="back_menu")
                ]
            ])
        )

    elif data == "api_info":
        user_token = await get_user_token(user_id) or "YOUR_TOKEN"
        await callback_query.answer()
        await callback_query.edit_message_text(
            "🎥 **Video Info Endpoint**\n\n"
            "**Endpoint:** `http://api.nub-coder.tech/info`\n"
            "**Method:** `GET`\n"
            "**Auth:** Token required\n\n"
            "**Parameters:**\n"
            "• `token` - Your API token\n"
            "• `q` - YouTube URL or search query\n"
            "• `max_results` - Max results (for search)\n\n"
            "Select example type:",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🌐 GET Examples", callback_data="api_info_get"),
                    InlineKeyboardButton("🐍 Python Implementation", callback_data="api_info_python")
                ],
                [InlineKeyboardButton("🔙 Back to API Docs", callback_data="api_docs")]
            ])
        )

    elif data == "api_info_get":
        user_token = await get_user_token(user_id) or "YOUR_TOKEN"
        await callback_query.answer()
        await callback_query.edit_message_text(
            "🌐 **Video Info - GET Examples**\n\n"
            "**1. Get info by URL:**\n"
            "```\n"
            f"GET http://api.nub-coder.tech/info?token={user_token}&q=https://youtube.com/watch?v=dQw4w9WgXcQ\n"
            "```\n\n"
            "**2. Search single video:**\n"
            "```\n"
            f"GET http://api.nub-coder.tech/info?token={user_token}&q=python tutorial&max_results=1\n"
            "```\n\n"
            "**3. Search multiple videos:**\n"
            "```\n"
            f"GET http://api.nub-coder.tech/info?token={user_token}&q=machine learning&max_results=5\n"
            "```\n\n"
            "**4. Using curl:**\n"
            "```bash\n"
            f"curl \"http://api.nub-coder.tech/info?token={user_token}&q=https://youtube.com/watch?v=VIDEO_ID\"\n"
            "```",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Video Info", callback_data="api_info")]
            ])
        )

    elif data == "api_info_python":
        user_token = await get_user_token(user_id) or "YOUR_TOKEN"
        await callback_query.answer()
        await callback_query.edit_message_text(
            "🐍 **Video Info - Python Implementation**\n\n"
            "**1. Get info by URL:**\n"
            "```python\n"
            "import requests\n\n"
            "url = 'http://api.nub-coder.tech/info'\n"
            "params = {\n"
            f"    'token': '{user_token}',\n"
            "    'q': 'https://youtube.com/watch?v=dQw4w9WgXcQ'\n"
            "}\n"
            "response = requests.get(url, params=params)\n"
            "data = response.json()\n"
            "print(f\"Title: {data['title']}\")\n"
            "print(f\"Duration: {data['duration']} seconds\")\n"
            "print(f\"Views: {data['views']}\")\n"
            "```\n\n"
            "**2. Search and get detailed info:**\n"
            "```python\n"
            "import requests\n\n"
            "params = {\n"
            f"    'token': '{user_token}',\n"
            "    'q': 'python tutorial',\n"
            "    'max_results': 1\n"
            "}\n"
            "response = requests.get(\n"
            "    'http://api.nub-coder.tech/info', \n"
            "    params=params\n"
            ")\n"
            "video = response.json()\n"
            "print(f\"Found: {video['title']}\")\n"
            "print(f\"Channel: {video['channel_name']}\")\n"
            "print(f\"Stream URL: {video['url']}\")\n"
            "```",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Video Info", callback_data="api_info")]
            ])
        )

    elif data == "api_search":
        await callback_query.answer()
        await callback_query.edit_message_text(
            "🔍 **Search Endpoint** (FREE)\n\n"
            "**Endpoint:** `http://api.nub-coder.tech/search`\n"
            "**Method:** `GET`\n"
            "**Auth:** No token required\n\n"
            "**Parameters:**\n"
            "• `q` - Search query\n"
            "• `max_results` - Number of results (1-20)\n\n"
            "Select example type:",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🌐 GET Examples", callback_data="api_search_get"),
                    InlineKeyboardButton("🐍 Python Implementation", callback_data="api_search_python")
                ],
                [InlineKeyboardButton("🔙 Back to API Docs", callback_data="api_docs")]
            ])
        )

    elif data == "api_search_get":
        await callback_query.answer()
        await callback_query.edit_message_text(
            "🌐 **Search - GET Examples**\n\n"
            "**1. Basic search (1 result):**\n"
            "```\n"
            "GET http://api.nub-coder.tech/search?q=python tutorial&max_results=1\n"
            "```\n\n"
            "**2. Multiple results:**\n"
            "```\n"
            "GET http://api.nub-coder.tech/search?q=machine learning&max_results=10\n"
            "```\n\n"
            "**3. URL encoded query:**\n"
            "```\n"
            "GET http://api.nub-coder.tech/search?q=how%20to%20code&max_results=5\n"
            "```\n\n"
            "**4. Using curl:**\n"
            "```bash\n"
            "curl \"http://api.nub-coder.tech/search?q=javascript tutorial&max_results=3\"\n"
            "```\n\n"
            "**5. Browser URL:**\n"
            "```\n"
            "http://api.nub-coder.tech/search?q=react js&max_results=20\n"
            "```",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Search", callback_data="api_search")]
            ])
        )

    elif data == "api_search_python":
        await callback_query.answer()
        await callback_query.edit_message_text(
            "🐍 **Search - Python Implementation**\n\n"
            "**1. Simple search:**\n"
            "```python\n"
            "import requests\n\n"
            "response = requests.get(\n"
            "    'http://api.nub-coder.tech/search',\n"
            "    params={'q': 'python tutorial', 'max_results': 1}\n"
            ")\n"
            "data = response.json()\n"
            "print(f\"Found {data['total_results']} results\")\n"
            "for video in data['results']:\n"
            "    print(f\"Title: {video['title']}\")\n"
            "    print(f\"Channel: {video['channel_name']}\")\n"
            "```\n\n"
            "**2. Advanced search with error handling:**\n"
            "```python\n"
            "import requests\n"
            "from typing import List, Dict\n\n"
            "def search_videos(query: str, max_results: int = 5) -> List[Dict]:\n"
            "    try:\n"
            "        response = requests.get(\n"
            "            'http://api.nub-coder.tech/search',\n"
            "            params={'q': query, 'max_results': max_results},\n"
            "            timeout=30\n"
            "        )\n"
            "        response.raise_for_status()\n"
            "        return response.json()['results']\n"
            "    except requests.RequestException as e:\n"
            "        print(f\"Error searching: {e}\")\n"
            "        return []\n\n"
            "# Usage\n"
            "videos = search_videos('machine learning', 10)\n"
            "for video in videos:\n"
            "    print(f\"{video['title']} - {video['duration']}s\")\n"
            "```",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Search", callback_data="api_search")]
            ])
        )

    elif data == "api_batch":
        await callback_query.answer()
        await callback_query.edit_message_text(
            "📦 **Batch Processing Endpoint**\n\n"
            "**Endpoint:** `http://api.nub-coder.tech/batch-info`\n"
            "**Method:** `POST`\n"
            "**Auth:** Token required\n\n"
            "**Parameters:**\n"
            "• `token` - Your API token (query param)\n"
            "• Request body: JSON array of URLs\n"
            "• **Limit:** Max 5 URLs per request\n\n"
            "Select example type:",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🌐 curl Examples", callback_data="api_batch_get"),
                    InlineKeyboardButton("🐍 Python Implementation", callback_data="api_batch_python")
                ],
                [InlineKeyboardButton("🔙 Back to API Docs", callback_data="api_docs")]
            ])
        )

    elif data == "api_batch_get":
        user_token = await get_user_token(user_id) or "YOUR_TOKEN"
        await callback_query.answer()
        await callback_query.edit_message_text(
            "🌐 **Batch Processing - curl Examples**\n\n"
            "**1. Basic batch request:**\n"
            "```bash\n"
            f"curl -X POST \"http://api.nub-coder.tech/batch-info?token={user_token}\" \\\n"
            "  -H \"Content-Type: application/json\" \\\n"
            "  -d '[\n"
            "    \"https://youtube.com/watch?v=dQw4w9WgXcQ\",\n"
            "    \"https://youtube.com/watch?v=9bZkp7q19f0\"\n"
            "  ]'\n"
            "```\n\n"
            "**2. Multiple URLs (max 5):**\n"
            "```bash\n"
            f"curl -X POST \"http://api.nub-coder.tech/batch-info?token={user_token}\" \\\n"
            "  -H \"Content-Type: application/json\" \\\n"
            "  -d '[\n"
            "    \"https://youtube.com/watch?v=VIDEO1\",\n"
            "    \"https://youtube.com/watch?v=VIDEO2\",\n"
            "    \"https://youtube.com/watch?v=VIDEO3\",\n"
            "    \"https://youtube.com/watch?v=VIDEO4\",\n"
            "    \"https://youtube.com/watch?v=VIDEO5\"\n"
            "  ]'\n"
            "```\n\n"
            "**3. With timeout and verbose output:**\n"
            "```bash\n"
            f"curl -v --max-time 60 \\\n"
            f"  -X POST \"http://api.nub-coder.tech/batch-info?token={user_token}\" \\\n"
            "  -H \"Content-Type: application/json\" \\\n"
            "  -d '[\"https://youtube.com/watch?v=ID\"]'\n"
            "```",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Batch", callback_data="api_batch")]
            ])
        )

    elif data == "api_batch_python":
        user_token = await get_user_token(user_id) or "YOUR_TOKEN"
        await callback_query.answer()
        await callback_query.edit_message_text(
            "🐍 **Batch Processing - Python Implementation**\n\n"
            "**1. Simple batch processing:**\n"
            "```python\n"
            "import requests\n"
            "import json\n\n"
            "urls = [\n"
            "    \"https://youtube.com/watch?v=dQw4w9WgXcQ\",\n"
            "    \"https://youtube.com/watch?v=9bZkp7q19f0\"\n"
            "]\n\n"
            "response = requests.post(\n"
            f"    'http://api.nub-coder.tech/batch-info?token={user_token}',\n"
            "    headers={'Content-Type': 'application/json'},\n"
            "    json=urls\n"
            ")\n\n"
            "if response.status_code == 200:\n"
            "    data = response.json()\n"
            "    print(f\"Processed {len(data['results'])} videos\")\n"
            "    for result in data['results']:\n"
            "        if 'error' in result:\n"
            "            print(f\"Error for {result['url']}: {result['error']}\")\n"
            "        else:\n"
            "            print(f\"Title: {result['title']}\")\n"
            "            print(f\"Duration: {result['duration']}s\")\n"
            "else:\n"
            "    print(f\"Error: {response.status_code}\")\n"
            "```",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("➡️ More Examples", callback_data="api_batch_python2"),
                    InlineKeyboardButton("🔙 Back to Batch", callback_data="api_batch")
                ]
            ])
        )

    elif data == "api_batch_python2":
        user_token = await get_user_token(user_id) or "YOUR_TOKEN"
        await callback_query.answer()
        await callback_query.edit_message_text(
            "🐍 **Advanced Batch Processing**\n\n"
            "**2. Function with error handling:**\n"
            "```python\n"
            "import requests\n"
            "from typing import List, Dict\n\n"
            "def batch_process_videos(urls: List[str], token: str) -> Dict:\n"
            "    # Limit to 5 URLs\n"
            "    urls = urls[:5]\n"
            "    \n"
            "    try:\n"
            "        response = requests.post(\n"
            "            f'http://api.nub-coder.tech/batch-info?token={token}',\n"
            "            headers={'Content-Type': 'application/json'},\n"
            "            json=urls,\n"
            "            timeout=60\n"
            "        )\n"
            "        response.raise_for_status()\n"
            "        return response.json()\n"
            "    except requests.exceptions.RequestException as e:\n"
            "        return {'error': str(e)}\n\n"
            "# Usage\n"
            "video_urls = [\n"
            "    'https://youtube.com/watch?v=VIDEO1',\n"
            "    'https://youtube.com/watch?v=VIDEO2'\n"
            "]\n\n"
            f"result = batch_process_videos(video_urls, '{user_token}')\n"
            "if 'error' not in result:\n"
            "    print(f\"Processing took: {result['total_time']}\")\n"
            "    for video in result['results']:\n"
            "        print(f\"✅ {video.get('title', 'Unknown')}\")\n"
            "```",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Batch", callback_data="api_batch")]
            ])
        )

    elif data == "api_ratelimit":
        await callback_query.answer()
        await callback_query.edit_message_text(
            "📊 **Rate Limit Status Endpoint**\n\n"
            "**Endpoint:** `http://api.nub-coder.tech/rate-limit-status`\n"
            "**Method:** `GET`\n"
            "**Auth:** Token required\n\n"
            "**Parameters:**\n"
            "• `token` - Your API token\n\n"
            "Select example type:",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🌐 GET Examples", callback_data="api_ratelimit_get"),
                    InlineKeyboardButton("🐍 Python Implementation", callback_data="api_ratelimit_python")
                ],
                [InlineKeyboardButton("🔙 Back to API Docs", callback_data="api_docs")]
            ])
        )

    elif data == "api_ratelimit_get":
        user_token = await get_user_token(user_id) or "YOUR_TOKEN"
        await callback_query.answer()
        await callback_query.edit_message_text(
            "🌐 **Rate Limit - GET Examples**\n\n"
            "**1. Check your quota:**\n"
            "```\n"
            f"GET http://api.nub-coder.tech/rate-limit-status?token={user_token}\n"
            "```\n\n"
            "**2. Using curl:**\n"
            "```bash\n"
            f"curl \"http://api.nub-coder.tech/rate-limit-status?token={user_token}\"\n"
            "```\n\n"
            "**3. With formatted output:**\n"
            "```bash\n"
            f"curl -s \"http://api.nub-coder.tech/rate-limit-status?token={user_token}\" | jq .\n"
            "```\n\n"
            "**4. Browser URL:**\n"
            "```\n"
            f"http://api.nub-coder.tech/rate-limit-status?token={user_token}\n"
            "```\n\n"
            "**Example Response:**\n"
            "```json\n"
            "{\n"
            "  \"user_id\": 123456,\n"
            "  \"daily_limit\": 1000,\n"
            "  \"requests_used\": 50,\n"
            "  \"requests_remaining\": 950,\n"
            "  \"reset_time\": \"Midnight UTC\",\n"
            "  \"is_admin\": false,\n"
            "  \"auth_method\": \"token\"\n"
            "}\n"
            "```",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Rate Limit", callback_data="api_ratelimit")]
            ])
        )

    elif data == "api_ratelimit_python":
        user_token = await get_user_token(user_id) or "YOUR_TOKEN"
        await callback_query.answer()
        await callback_query.edit_message_text(
            "🐍 **Rate Limit - Python Implementation**\n\n"
            "**1. Check quota status:**\n"
            "```python\n"
            "import requests\n\n"
            f"token = '{user_token}'\n"
            "response = requests.get(\n"
            f"    f'http://api.nub-coder.tech/rate-limit-status?token={{token}}'\n"
            ")\n\n"
            "if response.status_code == 200:\n"
            "    data = response.json()\n"
            "    print(f\"Used: {data['requests_used']}/{data['daily_limit']}\")\n"
            "    print(f\"Remaining: {data['requests_remaining']}\")\n"
            "    print(f\"Reset: {data['reset_time']}\")\n"
            "    if data['is_admin']:\n"
            "        print('👑 Admin privileges active')\n"
            "else:\n"
            "    print(f'Error: {response.status_code}')\n"
            "```\n\n"
            "**2. Quota monitoring function:**\n"
            "```python\n"
            "import requests\n"
            "from typing import Dict, Optional\n\n"
            "def check_quota(token: str) -> Optional[Dict]:\n"
            "    try:\n"
            "        response = requests.get(\n"
            "            'http://api.nub-coder.tech/rate-limit-status',\n"
            "            params={'token': token},\n"
            "            timeout=10\n"
            "        )\n"
            "        response.raise_for_status()\n"
            "        return response.json()\n"
            "    except requests.RequestException as e:\n"
            "        print(f'Error checking quota: {e}')\n"
            "        return None\n\n"
            "# Usage\n"
            f"quota = check_quota('{user_token}')\n"
            "if quota and quota['requests_remaining'] < 100:\n"
            "    print('⚠️ Low quota warning!')\n"
            "```",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Rate Limit", callback_data="api_ratelimit")]
            ])
        )

    elif data == "api_health":
        await callback_query.answer()
        await callback_query.edit_message_text(
            "❤️ **Health Check Endpoint**\n\n"
            "**Endpoint:** `http://api.nub-coder.tech/health`\n"
            "**Method:** `GET`\n"
            "**Auth:** No token required\n"
            "**Rate Limit:** None\n\n"
            "Select example type:",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🌐 GET Examples", callback_data="api_health_get"),
                    InlineKeyboardButton("🐍 Python Implementation", callback_data="api_health_python")
                ],
                [InlineKeyboardButton("🔙 Back to API Docs", callback_data="api_docs")]
            ])
        )

    elif data == "api_health_get":
        await callback_query.answer()
        await callback_query.edit_message_text(
            "🌐 **Health Check - GET Examples**\n\n"
            "**1. Simple health check:**\n"
            "```\n"
            "GET http://api.nub-coder.tech/health\n"
            "```\n\n"
            "**2. Using curl:**\n"
            "```bash\n"
            "curl http://api.nub-coder.tech/health\n"
            "```\n\n"
            "**3. With timing information:**\n"
            "```bash\n"
            "curl -w \"Response time: %{time_total}s\\n\" http://api.nub-coder.tech/health\n"
            "```\n\n"
            "**4. Test connectivity:**\n"
            "```bash\n"
            "curl -f -s http://api.nub-coder.tech/health && echo \"API is healthy\" || echo \"API is down\"\n"
            "```\n\n"
            "**5. Browser URL:**\n"
            "```\n"
            "http://api.nub-coder.tech/health\n"
            "```\n\n"
            "**Example Response:**\n"
            "```json\n"
            "{\n"
            "  \"status\": \"ok\"\n"
            "}\n"
            "```\n\n"
            "**Expected Response Time:** < 100ms",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Health Check", callback_data="api_health")]
            ])
        )

    elif data == "api_health_python":
        await callback_query.answer()
        await callback_query.edit_message_text(
            "🐍 **Health Check - Python Implementation**\n\n"
            "**1. Simple health check:**\n"
            "```python\n"
            "import requests\n\n"
            "response = requests.get('http://api.nub-coder.tech/health')\n"
            "if response.status_code == 200:\n"
            "    data = response.json()\n"
            "    if data['status'] == 'ok':\n"
            "        print('✅ API is healthy')\n"
            "    else:\n"
            "        print('⚠️ API status unknown')\n"
            "else:\n"
            "    print('❌ API is down')\n"
            "```\n\n"
            "**2. Health check with timing:**\n"
            "```python\n"
            "import requests\n"
            "import time\n\n"
            "def check_api_health():\n"
            "    try:\n"
            "        start_time = time.time()\n"
            "        response = requests.get(\n"
            "            'http://api.nub-coder.tech/health',\n"
            "            timeout=5\n"
            "        )\n"
            "        end_time = time.time()\n"
            "        \n"
            "        response_time = round((end_time - start_time) * 1000, 2)\n"
            "        \n"
            "        if response.status_code == 200:\n"
            "            print(f'✅ API healthy ({response_time}ms)')\n"
            "            return True\n"
            "        else:\n"
            "            print(f'❌ API error: {response.status_code}')\n"
            "            return False\n"
            "    except requests.RequestException as e:\n"
            "        print(f'❌ Connection error: {e}')\n"
            "        return False\n\n"
            "# Usage\n"
            "if check_api_health():\n"
            "    print('Proceeding with API requests...')\n"
            "```",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("➡️ More Examples", callback_data="api_health_python2"),
                    InlineKeyboardButton("🔙 Back to Health", callback_data="api_health")
                ]
            ])
        )

    elif data == "api_health_python2":
        await callback_query.answer()
        await callback_query.edit_message_text(
            "🐍 **Advanced Health Monitoring**\n\n"
            "**3. Continuous monitoring:**\n"
            "```python\n"
            "import requests\n"
            "import time\n"
            "from datetime import datetime\n\n"
            "def monitor_api(interval=60, duration=300):\n"
            "    \"\"\"Monitor API health for specified duration\"\"\"\n"
            "    start = time.time()\n"
            "    successful = 0\n"
            "    total = 0\n"
            "    \n"
            "    while time.time() - start < duration:\n"
            "        try:\n"
            "            response = requests.get(\n"
            "                'http://api.nub-coder.tech/health',\n"
            "                timeout=10\n"
            "            )\n"
            "            total += 1\n"
            "            \n"
            "            if response.status_code == 200:\n"
            "                successful += 1\n"
            "                status = '✅'\n"
            "            else:\n"
            "                status = '❌'\n"
            "                \n"
            "            uptime = (successful / total) * 100\n"
            "            timestamp = datetime.now().strftime('%H:%M:%S')\n"
            "            print(f'{timestamp} {status} Uptime: {uptime:.1f}% ({successful}/{total})')\n"
            "            \n"
            "        except requests.RequestException:\n"
            "            total += 1\n"
            "            uptime = (successful / total) * 100\n"
            "            print(f'{timestamp} ❌ Connection failed. Uptime: {uptime:.1f}%')\n"
            "        \n"
            "        time.sleep(interval)\n\n"
            "# Monitor for 5 minutes, check every minute\n"
            "monitor_api(interval=60, duration=300)\n"
            "```",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Health Check", callback_data="api_health")]
            ])
        )

    elif data == "back_menu":
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔑 View Token", callback_data="view_token"),
                InlineKeyboardButton("📊 Usage Status", callback_data="usage_status")
            ],
            [
                InlineKeyboardButton("🔄 Revoke Token", callback_data="revoke_token"),
                InlineKeyboardButton("❓ Help", callback_data="help")
            ],
            [
                InlineKeyboardButton("📖 API Docs", callback_data="api_docs")
            ]
        ])

        await callback_query.answer()
        await callback_query.edit_message_text(
            "🤖 **YT-DLP API Bot Menu**\n\n"
            "Choose an option below:",
            reply_markup=keyboard
        )
