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
            InlineKeyboardButton("🔧 API Implementation", callback_data="api_implementation"),
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
            InlineKeyboardButton("🔧 API Implementation", callback_data="api_implementation"),
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

    if data == "api_implementation":
        token = await get_user_token(user_id)
        if token:
            await callback_query.answer()
            await callback_query.edit_message_text(
                f"🔧 **API Implementation Guide**\n\n"
                f"🔑 **Your Token:** `{token}`\n\n"
                f"Choose implementation method:",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("🌐 GET Examples", callback_data="impl_get_all"),
                        InlineKeyboardButton("🐍 Python Implement", callback_data="impl_python_all")
                    ],
                    [
                        InlineKeyboardButton("📋 Quick Reference", callback_data="impl_quick_ref"),
                        InlineKeyboardButton("🔙 Back to Menu", callback_data="back_menu")
                    ]
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
            "• `/info` - Get video info + streamable URL (requires token)\n"
            "• `/search` - Search videos (free, no URLs)\n"
            "• `/batch-info` - Process multiple URLs + streamable URLs\n"
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

    elif data == "impl_get_all":
        user_token = await get_user_token(user_id) or "YOUR_TOKEN"
        await callback_query.answer()
        await callback_query.edit_message_text(
            "🌐 **All API Endpoints - GET Examples**\n\n"
            "**1. Video Info:**\n"
            "```\n"
            f"GET http://api.nub-coder.tech/info?token={user_token}&q=https://youtube.com/watch?v=dQw4w9WgXcQ\n"
            "```\n\n"
            "**2. Search Videos (Free):**\n"
            "```\n"
            f"GET http://api.nub-coder.tech/search?q=python tutorial&max_results=5\n"
            "```\n\n"
            "**3. Batch Processing:**\n"
            "```bash\n"
            f"curl -X POST \"http://api.nub-coder.tech/batch-info?token={user_token}\" \\\n"
            "  -H \"Content-Type: application/json\" \\\n"
            "  -d '[\"https://youtube.com/watch?v=ID1\", \"https://youtube.com/watch?v=ID2\"]'\n"
            "```\n\n"
            "**4. Rate Limit Status:**\n"
            "```\n"
            f"GET http://api.nub-coder.tech/rate-limit-status?token={user_token}\n"
            "```\n\n"
            "**5. Health Check:**\n"
            "```\n"
            "GET http://api.nub-coder.tech/health\n"
            "```",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Implementation", callback_data="api_implementation")]
            ])
        )

    elif data == "impl_python_all":
        user_token = await get_user_token(user_id) or "YOUR_TOKEN"
        await callback_query.answer()
        await callback_query.edit_message_text(
            "🐍 **Python Examples**\n\n"
            "```python\n"
            "import requests\n\n"
            f"TOKEN = '{user_token}'\n"
            "BASE = 'http://api.nub-coder.tech'\n\n"
            "# Search (free)\n"
            "r = requests.get(f'{BASE}/search', \n"
            "    params={'q': 'python tutorial', 'max_results': 5})\n"
            "results = r.json()['results']\n\n"
            "# Get info\n" 
            "r = requests.get(f'{BASE}/info',\n"
            "    params={'token': TOKEN, 'q': 'VIDEO_URL'})\n"
            "data = r.json()\n\n"
            "# Batch processing\n"
            "urls = ['URL1', 'URL2']\n"
            "r = requests.post(f'{BASE}/batch-info?token={TOKEN}',\n"
            "    json=urls)\n"
            "batch_data = r.json()\n"
            "```",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Implementation", callback_data="api_implementation")]
            ])
        )

    elif data == "impl_quick_ref":
        user_token = await get_user_token(user_id) or "YOUR_TOKEN"
        await callback_query.answer()
        await callback_query.edit_message_text(
            "📋 **Quick Reference**\n\n"
            f"🔑 **Token:** `{user_token}`\n"
            f"🌐 **Base URL:** `http://api.nub-coder.tech`\n\n"
            "**Endpoints:**\n"
            f"• `/info?token={user_token}&q=URL` - Video info\n"
            "• `/search?q=QUERY&max_results=5` - Search (free)\n"
            f"• `/batch-info?token={user_token}` - Batch (POST)\n"
            f"• `/rate-limit-status?token={user_token}` - Quota\n"
            "• `/health` - Health check\n\n"
            "**Rate Limits:**\n"
            "• Data endpoints: 1000/day\n"
            "• Search: Unlimited\n"
            "• Batch: Max 5 URLs per request\n\n"
            "**Python Quick Start:**\n"
            "```python\n"
            "import requests\n"
            f"r = requests.get('http://api.nub-coder.tech/info?token={user_token}&q=VIDEO_URL')\n"
            "data = r.json()\n"
            "```",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Implementation", callback_data="api_implementation")]
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
            "**Auth:** Token required\n"
            "**Returns:** Video metadata + streamable URL\n\n"
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
            "🐍 **Python Examples**\n\n"
            "```python\n"
            "import requests\n\n"
            f"TOKEN = '{user_token}'\n"
            "BASE = 'http://api.nub-coder.tech'\n\n"
            "# Search (free)\n"
            "r = requests.get(f'{BASE}/search', \n"
            "    params={'q': 'python tutorial', 'max_results': 5})\n"
            "results = r.json()['results']\n\n"
            "# Get info\n" 
            "r = requests.get(f'{BASE}/info',\n"
            "    params={'token': TOKEN, 'q': 'VIDEO_URL'})\n"
            "data = r.json()\n\n"
            "# Batch processing\n"
            "urls = ['URL1', 'URL2']\n"
            "r = requests.post(f'{BASE}/batch-info?token={TOKEN}',\n"
            "    json=urls)\n"
            "batch_data = r.json()\n"
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
        user_token = await get_user_token(user_id) or "YOUR_TOKEN"
        await callback_query.answer()
        await callback_query.edit_message_text(
            "🐍 **Python Examples**\n\n"
            "```python\n"
            "import requests\n\n"
            f"TOKEN = '{user_token}'\n"
            "BASE = 'http://api.nub-coder.tech'\n\n"
            "# Search (free)\n"
            "r = requests.get(f'{BASE}/search', \n"
            "    params={'q': 'python tutorial', 'max_results': 5})\n"
            "results = r.json()['results']\n\n"
            "# Get info\n" 
            "r = requests.get(f'{BASE}/info',\n"
            "    params={'token': TOKEN, 'q': 'VIDEO_URL'})\n"
            "data = r.json()\n\n"
            "# Batch processing\n"
            "urls = ['URL1', 'URL2']\n"
            "r = requests.post(f'{BASE}/batch-info?token={TOKEN}',\n"
            "    json=urls)\n"
            "batch_data = r.json()\n"
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
            "**Auth:** Token required\n"
            "**Returns:** Video metadata + streamable URLs for each video\n\n"
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
            "  -d '[\"https://youtube.com/watch?v=dQw4w9WgXcQ\", \"https://youtube.com/watch?v=9bZkp7q19f0\"]'\n"
            "```\n\n"
            "**2. Multiple URLs (max 5):**\n"
            "```bash\n"
            f"curl -X POST \"http://api.nub-coder.tech/batch-info?token={user_token}\" \\\n"
            "  -H \"Content-Type: application/json\" \\\n"
            "  -d '[\"https://youtube.com/watch?v=VIDEO1\", \"https://youtube.com/watch?v=VIDEO2\", \"https://youtube.com/watch?v=VIDEO3\", \"https://youtube.com/watch?v=VIDEO4\", \"https://youtube.com/watch?v=VIDEO5\"]'\n"
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
            "🐍 **Python Examples**\n\n"
            "```python\n"
            "import requests\n\n"
            f"TOKEN = '{user_token}'\n"
            "BASE = 'http://api.nub-coder.tech'\n\n"
            "# Search (free)\n"
            "r = requests.get(f'{BASE}/search', \n"
            "    params={'q': 'python tutorial', 'max_results': 5})\n"
            "results = r.json()['results']\n\n"
            "# Get info\n" 
            "r = requests.get(f'{BASE}/info',\n"
            "    params={'token': TOKEN, 'q': 'VIDEO_URL'})\n"
            "data = r.json()\n\n"
            "# Batch processing\n"
            "urls = ['URL1', 'URL2']\n"
            "r = requests.post(f'{BASE}/batch-info?token={TOKEN}',\n"
            "    json=urls)\n"
            "batch_data = r.json()\n"
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
            "🐍 **Python Examples**\n\n"
            "```python\n"
            "import requests\n\n"
            f"TOKEN = '{user_token}'\n"
            "BASE = 'http://api.nub-coder.tech'\n\n"
            "# Search (free)\n"
            "r = requests.get(f'{BASE}/search', \n"
            "    params={'q': 'python tutorial', 'max_results': 5})\n"
            "results = r.json()['results']\n\n"
            "# Get info\n" 
            "r = requests.get(f'{BASE}/info',\n"
            "    params={'token': TOKEN, 'q': 'VIDEO_URL'})\n"
            "data = r.json()\n\n"
            "# Batch processing\n"
            "urls = ['URL1', 'URL2']\n"
            "r = requests.post(f'{BASE}/batch-info?token={TOKEN}',\n"
            "    json=urls)\n"
            "batch_data = r.json()\n"
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
        user_token = await get_user_token(user_id) or "YOUR_TOKEN"
        await callback_query.answer()
        await callback_query.edit_message_text(
            "🐍 **Python Examples**\n\n"
            "```python\n"
            "import requests\n\n"
            f"TOKEN = '{user_token}'\n"
            "BASE = 'http://api.nub-coder.tech'\n\n"
            "# Search (free)\n"
            "r = requests.get(f'{BASE}/search', \n"
            "    params={'q': 'python tutorial', 'max_results': 5})\n"
            "results = r.json()['results']\n\n"
            "# Get info\n" 
            "r = requests.get(f'{BASE}/info',\n"
            "    params={'token': TOKEN, 'q': 'VIDEO_URL'})\n"
            "data = r.json()\n\n"
            "# Batch processing\n"
            "urls = ['URL1', 'URL2']\n"
            "r = requests.post(f'{BASE}/batch-info?token={TOKEN}',\n"
            "    json=urls)\n"
            "batch_data = r.json()\n"
            "```",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to Health Check", callback_data="api_health")]
            ])
        )

    elif data == "back_menu":
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🔧 API Implementation", callback_data="api_implementation"),
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