
from pyrogram import Client, filters
from pyrogram.types import Message
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools import (
    redis_client, is_admin, get_user_token, revoke_user_token,
    get_user_request_count, set_user_request_count
)

@Client.on_message(filters.command("stats") & filters.private)
async def bot_stats(client: Client, message: Message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        await message.reply_text("❌ You don't have admin privileges.")
        return
    
    try:
        # Get total users and active tokens
        user_keys = redis_client.keys("user_token:*")
        total_users = len(user_keys)
        
        # Get active users (users with requests today)
        request_keys = redis_client.keys("user_requests:*")
        active_users = len(request_keys)
        
        # Calculate total requests today
        total_requests_today = 0
        user_request_data = []
        
        for key in request_keys:
            try:
                count = int(redis_client.get(key) or 0)
                total_requests_today += count
                user_id_from_key = key.split(":")[1]
                user_request_data.append((user_id_from_key, count))
            except:
                continue
        
        # Sort users by request count (top users)
        user_request_data.sort(key=lambda x: x[1], reverse=True)
        top_users = user_request_data[:5]
        
        # Calculate admin users count
        admin_count = 0
        admin_requests = 0
        regular_requests = 0
        
        for user_id_str, count in user_request_data:
            if is_admin(int(user_id_str)):
                admin_count += 1
                admin_requests += count
            else:
                regular_requests += count
        
        # Get Redis info
        redis_info = redis_client.info()
        redis_memory = redis_info.get('used_memory_human', 'N/A')
        redis_uptime = redis_info.get('uptime_in_seconds', 0)
        redis_uptime_hours = round(redis_uptime / 3600, 1)
        
        # Usage statistics
        avg_requests_per_active_user = round(total_requests_today / max(active_users, 1), 2)
        
        # Build top users text
        top_users_text = ""
        for i, (uid, count) in enumerate(top_users, 1):
            admin_badge = "👑" if is_admin(int(uid)) else "👤"
            top_users_text += f"{admin_badge} User {uid}: {count} requests\n"
        
        if not top_users_text:
            top_users_text = "No active users today"
        
        # Calculate usage percentages
        user_utilization = round((active_users / max(total_users, 1)) * 100, 1)
        
        stats_message = (
            f"📊 **Comprehensive Bot Statistics**\n\n"
            f"👥 **User Metrics:**\n"
            f"• Total registered: **{total_users}**\n"
            f"• Active today: **{active_users}** ({user_utilization}%)\n"
            f"• Admin users: **{admin_count}**\n"
            f"• Regular users: **{total_users - admin_count}**\n\n"
            
            f"📈 **Request Analytics:**\n"
            f"• Total requests today: **{total_requests_today:,}**\n"
            f"• Admin requests: **{admin_requests:,}**\n"
            f"• Regular requests: **{regular_requests:,}**\n"
            f"• Avg per active user: **{avg_requests_per_active_user}**\n\n"
            
            f"🔥 **Top Users Today:**\n{top_users_text}\n"
            
            f"🗃️ **System Status:**\n"
            f"• Redis memory usage: **{redis_memory}**\n"
            f"• Redis uptime: **{redis_uptime_hours}h**\n"
            f"• Total Redis keys: **{len(redis_client.keys('*'))}**\n\n"
            
            f"📋 **Rate Limits:**\n"
            f"• Regular users: **1,000** req/day\n"
            f"• Admin users: **10,000** req/day\n"
            f"• Search endpoint: **Unlimited** (free)\n\n"
            
            f"⚡ **Performance:**\n"
            f"• Active user ratio: **{user_utilization}%**\n"
            f"• System load: {'🟢 Low' if total_requests_today < 50000 else '🟡 Medium' if total_requests_today < 100000 else '🔴 High'}\n"
            f"• Cache efficiency: **Active**"
        )
        
        await message.reply_text(stats_message)
        
    except Exception as e:
        await message.reply_text(f"❌ Error retrieving stats: {str(e)}")

@Client.on_message(filters.regex(r"^/user \d+") & filters.private)
async def user_info(client: Client, message: Message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        await message.reply_text("❌ You don't have admin privileges.")
        return
    
    try:
        target_user_id = message.text.split()[1]
        token = await get_user_token(target_user_id)
        request_count = await get_user_request_count(target_user_id)
        
        if token:
            await message.reply_text(
                f"👤 **User Information**\n\n"
                f"🆔 User ID: `{target_user_id}`\n"
                f"🔑 Token: `{token}`\n"
                f"📊 Requests today: **{request_count}**\n"
                f"👑 Admin: {'Yes' if is_admin(int(target_user_id)) else 'No'}"
            )
        else:
            await message.reply_text(f"❌ User {target_user_id} not found.")
    except Exception as e:
        await message.reply_text(f"❌ Error: {str(e)}")

@Client.on_message(filters.regex(r"^/grant \d+ \d+") & filters.private)
async def grant_requests(client: Client, message: Message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        await message.reply_text("❌ You don't have admin privileges.")
        return
    
    try:
        _, target_user_id, amount = message.text.split()
        target_user_id = int(target_user_id)
        amount = int(amount)
        
        current_count = await get_user_request_count(target_user_id)
        new_count = max(0, current_count - amount)  # Reduce count to grant more requests
        await set_user_request_count(target_user_id, new_count)
        
        await message.reply_text(
            f"✅ **Request Granted!**\n\n"
            f"👤 User: {target_user_id}\n"
            f"🎁 Amount: {amount} extra requests\n"
            f"📊 Previous: {current_count}\n"
            f"📈 New: {new_count}"
        )
    except Exception as e:
        await message.reply_text(f"❌ Error: {str(e)}")

@Client.on_message(filters.regex(r"^/revoke \d+") & filters.private)
async def revoke_token(client: Client, message: Message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        await message.reply_text("❌ You don't have admin privileges.")
        return
    
    try:
        target_user_id = int(message.text.split()[1])
        await revoke_user_token(target_user_id)
        await message.reply_text(f"✅ Token revoked for user {target_user_id}")
    except Exception as e:
        await message.reply_text(f"❌ Error: {str(e)}")

@Client.on_message(filters.command("listusers") & filters.private)
async def list_users(client: Client, message: Message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        await message.reply_text("❌ You don't have admin privileges.")
        return
    
    user_keys = redis_client.keys("user_token:*")
    recent_users = []
    
    for key in user_keys[:20]:  # Show last 20 users
        user_id_key = key.split(":")[1]
        token = redis_client.get(key)
        request_count = redis_client.get(f"user_requests:{user_id_key}") or "0"
        recent_users.append(f"👤 {user_id_key}: {request_count} requests")
    
    users_text = "\n".join(recent_users) if recent_users else "No users found"
    
    await message.reply_text(f"📋 **Recent Users**\n\n{users_text}")

@Client.on_message(filters.command("adminhelp") & filters.private)
async def admin_help(client: Client, message: Message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        await message.reply_text("❌ You don't have admin privileges.")
        return
    
    await message.reply_text(
        "👑 **Admin Commands**\n\n"
        "📊 `/stats` - View bot statistics\n"
        "👤 `/user <user_id>` - Get user information\n"
        "🎁 `/grant <user_id> <amount>` - Grant extra requests\n"
        "🚫 `/revoke <user_id>` - Revoke user token\n"
        "📋 `/listusers` - List recent users\n"
        "❓ `/adminhelp` - Show this help message\n\n"
        "**Examples:**\n"
        "• `/user 123456789`\n"
        "• `/grant 123456789 500`\n"
        "• `/revoke 123456789`"
    )
