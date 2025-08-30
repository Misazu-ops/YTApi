
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

# Initialize Pyrogram client
app = Client("ytdlp_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

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

@app.on_message(filters.command("start"))
async def start_command(client, message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    
    # Check if user already has a token
    existing_token = await get_user_token(user_id)
    
    if existing_token:
        await message.reply_text(
            f"Welcome back, {username}!\n\n"
            f"Your API token: `{existing_token}`\n\n"
            f"Use this token in the API header: `Authorization: Bearer {existing_token}`\n\n"
            "Commands:\n"
            "/token - View your current token\n"
            "/revoke - Revoke and generate new token\n"
            "/status - Check your usage"
        )
    else:
        # Generate new token
        new_token = generate_token()
        await set_user_token(user_id, new_token)
        
        await message.reply_text(
            f"Welcome to YT-DLP API, {username}!\n\n"
            f"Your API token: `{new_token}`\n\n"
            f"Use this token in the API header: `Authorization: Bearer {new_token}`\n\n"
            "Daily limit: 1000 requests\n"
            "Search is always free!\n\n"
            "Commands:\n"
            "/token - View your current token\n"
            "/revoke - Revoke and generate new token\n"
            "/status - Check your usage"
        )

@app.on_message(filters.command("token"))
async def token_command(client, message: Message):
    user_id = message.from_user.id
    token = await get_user_token(user_id)
    
    if token:
        await message.reply_text(f"Your current API token: `{token}`")
    else:
        await message.reply_text("You don't have a token. Use /start to get one.")

@app.on_message(filters.command("revoke"))
async def revoke_command(client, message: Message):
    user_id = message.from_user.id
    
    # Revoke old token
    await revoke_user_token(user_id)
    
    # Generate new token
    new_token = generate_token()
    await set_user_token(user_id, new_token)
    
    await message.reply_text(
        f"Token revoked successfully!\n\n"
        f"Your new API token: `{new_token}`\n\n"
        "Update your API calls with the new token."
    )

@app.on_message(filters.command("status"))
async def status_command(client, message: Message):
    user_id = message.from_user.id
    token = await get_user_token(user_id)
    
    if not token:
        await message.reply_text("You don't have a token. Use /start to get one.")
        return
    
    request_count = await get_user_request_count(user_id)
    limit = 10000 if is_admin(user_id) else 1000
    
    status_text = (
        f"📊 **Usage Status**\n\n"
        f"Token: `{token}`\n"
        f"Requests used today: {request_count}/{limit}\n"
        f"Remaining: {limit - request_count}\n"
    )
    
    if is_admin(user_id):
        status_text += "\n👑 Admin privileges active"
    
    await message.reply_text(status_text)

@app.on_message(filters.command("admin") & filters.private)
async def admin_command(client, message: Message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        await message.reply_text("❌ You don't have admin privileges.")
        return
    
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    
    if not args:
        await message.reply_text(
            "👑 **Admin Commands**\n\n"
            "/admin stats - View bot statistics\n"
            "/admin user <user_id> - View user info\n"
            "/admin grant <user_id> <amount> - Grant extra requests\n"
            "/admin revoke <user_id> - Revoke user token"
        )
        return
    
    if args[0] == "stats":
        # Get total users and tokens
        total_users = len([key for key in redis_client.keys("user_token:*")])
        await message.reply_text(f"📈 **Bot Statistics**\n\nTotal users: {total_users}")
    
    elif args[0] == "user" and len(args) > 1:
        target_user_id = args[1]
        token = await get_user_token(target_user_id)
        request_count = await get_user_request_count(target_user_id)
        
        if token:
            await message.reply_text(
                f"👤 **User Info**\n\n"
                f"User ID: {target_user_id}\n"
                f"Token: `{token}`\n"
                f"Requests today: {request_count}"
            )
        else:
            await message.reply_text(f"User {target_user_id} not found.")
    
    elif args[0] == "grant" and len(args) > 2:
        target_user_id = int(args[1])
        amount = int(args[2])
        current_count = await get_user_request_count(target_user_id)
        new_count = max(0, current_count - amount)  # Reduce count to grant more requests
        await set_user_request_count(target_user_id, new_count)
        
        await message.reply_text(f"✅ Granted {amount} extra requests to user {target_user_id}")
    
    elif args[0] == "revoke" and len(args) > 1:
        target_user_id = int(args[1])
        await revoke_user_token(target_user_id)
        await message.reply_text(f"✅ Revoked token for user {target_user_id}")

async def start_bot():
    """Start the Telegram bot"""
    await app.start()
    print("✅ Telegram bot started successfully!")
    
    # Send startup message to channel
    try:
        await app.send_message(
            CHANNEL, 
            "🤖 YT-DLP API Bot is now online!\n\nUse /start to get your API token."
        )
    except Exception as e:
        print(f"Could not send startup message: {e}")

async def stop_bot():
    """Stop the Telegram bot"""
    await app.stop()
    print("🛑 Telegram bot stopped")

# Export functions for use in main.py
__all__ = ['start_bot', 'stop_bot', 'get_user_by_token', 'is_admin', 'increment_user_requests', 'get_user_request_count']
