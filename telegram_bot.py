
import asyncio
import string
import random
import redis
from pyrogram import Client, filters
from pyrogram.types import Message
import logging

# Telegram Bot Configuration
API_ID = 21869707
API_HASH = '31ec80a4adad7aaad9262e894e3654e6'
BOT_TOKEN = '8246299769:AAHD8gd49wwlMuq9lBXmKtCNOxWDFjKR694'
GROUP = "nub_coder_s"
CHANNEL = "nub_coders"

# Redis Configuration
redis_client = redis.Redis(
    host='redis-15440.c93.us-east-1-3.ec2.redns.redis-cloud.com',
    port=15440,
    decode_responses=True,
    username="default",
    password="Af1Y9RyLA2mSlpuEfoR99YfvBx0YmRvS"
)

# Initialize Pyrogram client with plugins
app = Client(
    "ytdlp_bot", 
    api_id=API_ID, 
    api_hash=API_HASH, 
    bot_token=BOT_TOKEN,
    plugins=dict(root="plugins")
)

# Load admin user IDs
def load_admin_ids():
    try:
        with open('admin.txt', 'r') as f:
            return [int(line.strip()) for line in f if line.strip().isdigit()]
    except FileNotFoundError:
        return []

def generate_token():
    """Generate a 10-character alphanumeric token"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=10))

def is_admin(user_id):
    """Check if user is admin"""
    admin_ids = load_admin_ids()
    return user_id in admin_ids

async def get_user_token(user_id):
    """Get user's current token from Redis"""
    return redis_client.get(f"user_token:{user_id}")

async def set_user_token(user_id, token):
    """Set user token in Redis"""
    redis_client.set(f"user_token:{user_id}", token)
    redis_client.set(f"token_user:{token}", user_id)

async def revoke_user_token(user_id):
    """Revoke user's current token"""
    current_token = await get_user_token(user_id)
    if current_token:
        redis_client.delete(f"user_token:{user_id}")
        redis_client.delete(f"token_user:{current_token}")

def get_user_by_token(token):
    """Get user ID by token"""
    user_id = redis_client.get(f"token_user:{token}")
    return int(user_id) if user_id else None

async def get_user_request_count(user_id):
    """Get user's daily request count"""
    return int(redis_client.get(f"user_requests:{user_id}") or 0)

async def set_user_request_count(user_id, count):
    """Set user's daily request count"""
    redis_client.setex(f"user_requests:{user_id}", 86400, count)  # 24 hours TTL

async def increment_user_requests(user_id):
    """Increment user's daily request count"""
    key = f"user_requests:{user_id}"
    current = int(redis_client.get(key) or 0)
    redis_client.setex(key, 86400, current + 1)
    return current + 1

# Commands are now handled by plugins

async def start_bot():
    """Start the Telegram bot"""
    await app.start()
    print("✅ Telegram bot started successfully!")
    print("🔌 Plugins loaded from plugins/ directory")
    
    # Send startup message to channel
    try:
        await app.send_message(
            CHANNEL, 
            "🤖 YT-DLP API Bot is now online!\n\n"
            "✨ Features:\n"
            "• Interactive buttons\n"
            "• Token management\n"
            "• Usage tracking\n"
            "• Admin panel\n\n"
            "Use /start to get your API token!"
        )
    except Exception as e:
        print(f"Could not send startup message: {e}")

async def stop_bot():
    """Stop the Telegram bot"""
    await app.stop()
    print("🛑 Telegram bot stopped")

# Export functions for use in main.py
__all__ = ['start_bot', 'stop_bot', 'get_user_by_token', 'is_admin', 'increment_user_requests', 'get_user_request_count']
