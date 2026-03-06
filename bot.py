from pyrogram import Client, idle
from tools import (
    redis_client, generate_token, is_admin, get_user_token, 
    set_user_token, revoke_user_token, get_user_by_token,
    get_user_request_count, set_user_request_count, increment_user_requests
)

API_ID = 21856699
API_HASH = '73f10cf0979637857170f03d4c86f251'
BOT_TOKEN = '8349109217:AAFtzhQVBYoWf-nQY4-YcFqfh77866zmLEk'
GROUP = "nub_coder_s"
CHANNEL = "nub_coders"

telegram_app = Client(
    "ytdlp_bot", 
    api_id=API_ID, 
    api_hash=API_HASH, 
    bot_token=BOT_TOKEN, in_memory=True,
    plugins=dict(root="plugins"),
    device_model="Desktop",
    system_version="Windows 10",
    app_version="3.4.3 x64",
    lang_code="en",
    lang_pack="tdesktop"
)

def setup_bot_commands():
    from pyrogram.types import BotCommand
    commands = [
        BotCommand("start", "🚀 Get your API token and welcome message"),
        BotCommand("menu", "📋 Show main menu with options"),
        BotCommand("status", "📊 Check your usage statistics"),
        BotCommand("token", "🔑 View your current API token"),
        BotCommand("revoke", "🔄 Revoke your current token"),
        BotCommand("help", "❓ Get help and API documentation"),
    ]
    try:
        telegram_app.set_bot_commands(commands)
        print("✅ Bot commands set successfully")
    except Exception as e:
        print(f"⚠️ Failed to set bot commands: {e}")

def run_bot():
    telegram_app.start()
    setup_bot_commands()
    telegram_app.run()
    telegram_app.stop()

if __name__ == "__main__":
    run_bot()
