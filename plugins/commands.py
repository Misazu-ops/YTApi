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
            "**Example Request:**\n"
            "```\n"
            f"GET http://api.nub-coder.tech/info?token={user_token}&q=https://youtube.com/watch?v=ID\n"
            "```\n\n"
            "**Python Example:**\n"
            "```python\n"
            "import requests\n"
            "url = 'http://api.nub-coder.tech/info'\n"
            "params = {\n"
            f"    'token': '{user_token}',\n"
            "    'q': 'https://youtube.com/watch?v=VIDEO_ID'\n"
            "}\n"
            "response = requests.get(url, params=params)\n"
            "data = response.json()\n"
            "print(data['title'])\n"
            "```\n\n"
            "**Example Response:**\n"
            "```json\n"
            "{\n"
            "  \"query_type\": \"url\",\n"
            "  \"title\": \"Video Title\",\n"
            "  \"duration\": 180,\n"
            "  \"youtube_link\": \"https://youtube.com/watch?v=ID\",\n"
            "  \"channel_name\": \"Channel Name\",\n"
            "  \"views\": 1000000,\n"
            "  \"video_id\": \"VIDEO_ID\",\n"
            "  \"url\": \"https://stream-url.com\",\n"
            "  \"time_taken\": \"1.2 sec\"\n"
            "}\n"
            "```",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to API Docs", callback_data="api_docs")]
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
            "**Example Request:**\n"
            "```\n"
            "GET http://api.nub-coder.tech/search?q=python%20tutorial&max_results=5\n"
            "```\n\n"
            "**Python Example:**\n"
            "```python\n"
            "import requests\n"
            "url = 'http://api.nub-coder.tech/search'\n"
            "params = {\n"
            "    'q': 'python tutorial',\n"
            "    'max_results': 5\n"
            "}\n"
            "response = requests.get(url, params=params)\n"
            "results = response.json()['results']\n"
            "for video in results:\n"
            "    print(video['title'])\n"
            "```\n\n"
            "**Example Response:**\n"
            "```json\n"
            "{\n"
            "  \"query\": \"python tutorial\",\n"
            "  \"results\": [{\n"
            "    \"title\": \"Video Title\",\n"
            "    \"video_id\": \"VIDEO_ID\",\n"
            "    \"channel_name\": \"Channel\",\n"
            "    \"duration\": 180,\n"
            "    \"views\": 1000000,\n"
            "    \"youtube_link\": \"https://youtube.com/watch?v=ID\",\n"
            "    \"thumbnail\": \"https://thumb.jpg\"\n"
            "  }],\n"
            "  \"total_results\": 1,\n"
            "  \"time_taken\": \"0.8 sec\"\n"
            "}\n"
            "```",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to API Docs", callback_data="api_docs")]
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
            "• Request body: JSON array of URLs\n\n"
            "**Example Request:**\n"
            "```\n"
            "POST http://api.nub-coder.tech/batch-info?token=TOKEN\n"
            "Content-Type: application/json\n\n"
            "[\"https://youtube.com/watch?v=ID1\",\n"
            " \"https://youtube.com/watch?v=ID2\"]\n"
            "```\n\n"
            "**Example Response:**\n"
            "```json\n"
            "{\n"
            "  \"results\": [{\n"
            "    \"url\": \"https://youtube.com/watch?v=ID1\",\n"
            "    \"title\": \"Video Title\",\n"
            "    \"duration\": 180,\n"
            "    \"stream_url\": \"https://stream.com\"\n"
            "  }],\n"
            "  \"total_time\": \"2.5 sec\"\n"
            "}\n"
            "```\n\n"
            "**Limit:** Max 5 URLs per request",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to API Docs", callback_data="api_docs")]
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
            "**Example Request:**\n"
            "```\n"
            "GET http://api.nub-coder.tech/rate-limit-status?token=TOKEN\n"
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
            "```\n\n"
            "**Usage:** Monitor your daily quota",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to API Docs", callback_data="api_docs")]
            ])
        )

    elif data == "api_health":
        await callback_query.answer()
        await callback_query.edit_message_text(
            "❤️ **Health Check Endpoint**\n\n"
            "**Endpoint:** `http://api.nub-coder.tech/health`\n"
            "**Method:** `GET`\n"
            "**Auth:** No token required\n\n"
            "**Parameters:** None\n\n"
            "**Example Request:**\n"
            "```\n"
            "GET http://api.nub-coder.tech/health\n"
            "```\n\n"
            "**Example Response:**\n"
            "```json\n"
            "{\n"
            "  \"status\": \"ok\"\n"
            "}\n"
            "```\n\n"
            "**Usage:** Check if API is running\n"
            "**Response Time:** < 100ms\n"
            "**Rate Limit:** None",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back to API Docs", callback_data="api_docs")]
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