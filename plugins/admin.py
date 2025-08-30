
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from telegram_bot import (
    redis_client, is_admin, get_user_token, revoke_user_token,
    get_user_request_count, set_user_request_count
)

@Client.on_message(filters.command("admin") & filters.private)
async def admin_command(client: Client, message: Message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        await message.reply_text("❌ You don't have admin privileges.")
        return
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📊 Bot Stats", callback_data="admin_stats"),
            InlineKeyboardButton("👥 User Management", callback_data="admin_users")
        ],
        [
            InlineKeyboardButton("🎁 Grant Requests", callback_data="admin_grant"),
            InlineKeyboardButton("🚫 Revoke Tokens", callback_data="admin_revoke")
        ]
    ])
    
    await message.reply_text(
        "👑 **Admin Panel**\n\n"
        "Welcome to the admin dashboard.\n"
        "Choose an option below:",
        reply_markup=keyboard
    )

@Client.on_callback_query(filters.regex(r"^admin_"))
async def handle_admin_callbacks(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    
    if not is_admin(user_id):
        await callback_query.answer("❌ Access denied!", show_alert=True)
        return
    
    data = callback_query.data
    
    if data == "admin_stats":
        # Get total users and active tokens
        user_keys = redis_client.keys("user_token:*")
        total_users = len(user_keys)
        
        # Get active users (users with requests today)
        request_keys = redis_client.keys("user_requests:*")
        active_users = len(request_keys)
        
        await callback_query.answer()
        await callback_query.edit_message_text(
            f"📊 **Bot Statistics**\n\n"
            f"👥 Total users: **{total_users}**\n"
            f"🔥 Active today: **{active_users}**\n"
            f"🗃️ Redis keys: **{len(redis_client.keys('*'))}**\n\n"
            f"📈 **Usage Distribution:**\n"
            f"• Regular users: 1000 req/day\n"
            f"• Admin users: 10000 req/day",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Refresh", callback_data="admin_stats")],
                [InlineKeyboardButton("🔙 Back", callback_data="admin_back")]
            ])
        )
    
    elif data == "admin_users":
        await callback_query.answer()
        await callback_query.edit_message_text(
            "👥 **User Management**\n\n"
            "Send a user ID to get user information:\n"
            "Format: `user 123456789`\n\n"
            "Or use the buttons below:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📋 List Recent Users", callback_data="admin_list_users")],
                [InlineKeyboardButton("🔙 Back", callback_data="admin_back")]
            ])
        )
    
    elif data == "admin_grant":
        await callback_query.answer()
        await callback_query.edit_message_text(
            "🎁 **Grant Extra Requests**\n\n"
            "Send the following format:\n"
            "`grant 123456789 500`\n\n"
            "This will grant 500 extra requests to user 123456789.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="admin_back")]
            ])
        )
    
    elif data == "admin_revoke":
        await callback_query.answer()
        await callback_query.edit_message_text(
            "🚫 **Revoke User Tokens**\n\n"
            "Send the following format:\n"
            "`revoke 123456789`\n\n"
            "This will revoke the token for user 123456789.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 Back", callback_data="admin_back")]
            ])
        )
    
    elif data == "admin_list_users":
        user_keys = redis_client.keys("user_token:*")
        recent_users = []
        
        for key in user_keys[:10]:  # Show last 10 users
            user_id = key.split(":")[1]
            token = redis_client.get(key)
            request_count = redis_client.get(f"user_requests:{user_id}") or "0"
            recent_users.append(f"👤 {user_id}: {request_count} requests")
        
        users_text = "\n".join(recent_users) if recent_users else "No users found"
        
        await callback_query.answer()
        await callback_query.edit_message_text(
            f"📋 **Recent Users**\n\n{users_text}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Refresh", callback_data="admin_list_users")],
                [InlineKeyboardButton("🔙 Back", callback_data="admin_back")]
            ])
        )
    
    elif data == "admin_back":
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📊 Bot Stats", callback_data="admin_stats"),
                InlineKeyboardButton("👥 User Management", callback_data="admin_users")
            ],
            [
                InlineKeyboardButton("🎁 Grant Requests", callback_data="admin_grant"),
                InlineKeyboardButton("🚫 Revoke Tokens", callback_data="admin_revoke")
            ]
        ])
        
        await callback_query.answer()
        await callback_query.edit_message_text(
            "👑 **Admin Panel**\n\n"
            "Welcome to the admin dashboard.\n"
            "Choose an option below:",
            reply_markup=keyboard
        )

@Client.on_message(filters.regex(r"^user \d+") & filters.private)
async def admin_user_info(client: Client, message: Message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        return
    
    try:
        target_user_id = message.text.split()[1]
        token = await get_user_token(target_user_id)
        request_count = await get_user_request_count(target_user_id)
        
        if token:
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🚫 Revoke Token", callback_data=f"admin_revoke_user_{target_user_id}"),
                    InlineKeyboardButton("🎁 Grant 500", callback_data=f"admin_grant_user_{target_user_id}_500")
                ]
            ])
            
            await message.reply_text(
                f"👤 **User Information**\n\n"
                f"🆔 User ID: `{target_user_id}`\n"
                f"🔑 Token: `{token}`\n"
                f"📊 Requests today: **{request_count}**\n"
                f"👑 Admin: {'Yes' if is_admin(int(target_user_id)) else 'No'}",
                reply_markup=keyboard
            )
        else:
            await message.reply_text(f"❌ User {target_user_id} not found.")
    except Exception as e:
        await message.reply_text(f"❌ Error: {str(e)}")

@Client.on_message(filters.regex(r"^grant \d+ \d+") & filters.private)
async def admin_grant_requests(client: Client, message: Message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
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

@Client.on_message(filters.regex(r"^revoke \d+") & filters.private)
async def admin_revoke_token(client: Client, message: Message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        return
    
    try:
        target_user_id = int(message.text.split()[1])
        await revoke_user_token(target_user_id)
        await message.reply_text(f"✅ Token revoked for user {target_user_id}")
    except Exception as e:
        await message.reply_text(f"❌ Error: {str(e)}")
