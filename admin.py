from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from database import Database
from config import ADMIN_IDS, CHANNEL_USERNAME, PROVIDER_USERNAME

db = Database()

async def admin_panel(query):
    """Show admin panel."""
    user_id = str(query.from_user.id)
    
    text = f"**⚙️ Admin Panel**\n\n"
    text += f"Welcome to the admin dashboard!\n"
    text += f"You can manage the bot from here.\n\n"
    text += f"**Bot for @{CHANNEL_USERNAME}**\n"
    text += f"**Provided by @{PROVIDER_USERNAME}**"
    
    keyboard = [
        [InlineKeyboardButton("📊 Edit Global Stats", callback_data="admin_edit_stats")],
        [InlineKeyboardButton("👥 Manage Co-Admins", callback_data="admin_co_admins")],
        [InlineKeyboardButton("📢 Broadcast Message", callback_data="admin_broadcast")],
        [InlineKeyboardButton("📋 View All Users", callback_data="admin_users")],
        [InlineKeyboardButton("🔙 Back to Dashboard", callback_data="back")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin callbacks."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = str(query.from_user.id)
    
    if not (user_id in ADMIN_IDS or db.is_co_admin(user_id)):
        await query.edit_message_text("❌ You are not authorized!")
        return
    
    if data == "admin_edit_stats":
        await edit_stats_menu(query, context)
    elif data == "admin_co_admins":
        await co_admin_menu(query, context)
    elif data == "admin_broadcast":
        context.user_data['waiting_for_broadcast'] = True
        await query.edit_message_text(
            "📢 **Send the message you want to broadcast to all users.**\n\n"
            "Type your message below. It will be sent to all registered users.\n"
            "Send /cancel to cancel.",
            parse_mode='Markdown'
        )
    elif data == "admin_users":
        await view_all_users(query)
    elif data.startswith("admin_remove_coadmin_"):
        await remove_co_admin(query, context)

async def edit_stats_menu(query, context):
    """Show edit stats menu."""
    stats = db.get_global_stats()
    
    text = f"**📊 Edit Global Statistics**\n\n"
    text += f"Current Stats:\n"
    text += f"• Total Deals: {stats['total_deals']}\n"
    text += f"• Total Volume TON: {stats['total_volume_ton']}\n"
    text += f"• Total Volume USDT: {stats['total_volume_usdt']}\n"
    text += f"• Total Volume INR: {stats['total_volume_inr']}\n\n"
    text += "Click a button below to edit:"
    
    keyboard = [
        [InlineKeyboardButton("📈 Total Deals", callback_data="edit_stats_deals")],
        [InlineKeyboardButton("💎 TON Volume", callback_data="edit_stats_ton")],
        [InlineKeyboardButton("💵 USDT Volume", callback_data="edit_stats_usdt")],
        [InlineKeyboardButton("🇮🇳 INR Volume", callback_data="edit_stats_inr")],
        [InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_panel")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def edit_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle stats editing."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    stat_type = data.replace("edit_stats_", "")
    
    context.user_data['waiting_for_stats_edit'] = True
    context.user_data['stats_type'] = stat_type
    
    stat_names = {
        'deals': 'Total Deals',
        'ton': 'TON Volume',
        'usdt': 'USDT Volume',
        'inr': 'INR Volume'
    }
    
    await query.edit_message_text(
        f"✏️ **Edit {stat_names.get(stat_type, stat_type)}**\n\n"
        f"Enter the new value for {stat_names.get(stat_type, stat_type)}:\n"
        f"Send /cancel to cancel.",
        parse_mode='Markdown'
    )

async def save_stats_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Save edited stats."""
    user_id = str(update.effective_user.id)
    message_text = update.message.text
    
    if message_text == "/cancel":
        context.user_data['waiting_for_stats_edit'] = False
        context.user_data['stats_type'] = None
        await update.message.reply_text("❌ Cancelled!")
        return
    
    try:
        new_value = float(message_text)
        stat_type = context.user_data.get('stats_type')
        
        stats = db.get_global_stats()
        
        if stat_type == 'deals':
            db.update_global_stats(deals=int(new_value))
        elif stat_type == 'ton':
            db.update_global_stats(volume_ton=new_value)
        elif stat_type == 'usdt':
            db.update_global_stats(volume_usdt=new_value)
        elif stat_type == 'inr':
            db.update_global_stats(volume_inr=new_value)
        
        context.user_data['waiting_for_stats_edit'] = False
        context.user_data['stats_type'] = None
        
        await update.message.reply_text(f"✅ Statistics updated successfully!\nNew value: {new_value}")
        
        # Return to admin panel
        keyboard = [[InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_panel")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Click below to return:", reply_markup=reply_markup)
        
    except ValueError:
        await update.message.reply_text("❌ Please enter a valid number!")

async def co_admin_menu(query, context):
    """Show co-admin management menu."""
    co_admins = db.get_all_co_admins()
    
    text = f"**👥 Co-Admin Management**\n\n"
    if co_admins:
        text += "Current Co-Admins:\n"
        for admin in co_admins:
            text += f"• User ID: `{admin['user_id']}`\n"
            text += f"  Added by: {admin['added_by']}\n"
            text += f"  Added at: {admin['added_at']}\n\n"
    else:
        text += "No co-admins added yet.\n\n"
    
    text += "To add a new co-admin, send their user ID."
    
    keyboard = []
    for admin in co_admins:
        keyboard.append([
            InlineKeyboardButton(
                f"❌ Remove {admin['user_id']}", 
                callback_data=f"admin_remove_coadmin_{admin['user_id']}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("➕ Add Co-Admin", callback_data="admin_add_coadmin")])
    keyboard.append([InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_panel")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def add_co_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add a new co-admin."""
    query = update.callback_query
    await query.answer()
    
    context.user_data['waiting_for_coadmin'] = True
    await query.edit_message_text(
        "👤 **Add Co-Admin**\n\n"
        "Please enter the Telegram User ID of the person you want to add as co-admin.\n"
        "Send /cancel to cancel.",
        parse_mode='Markdown'
    )

async def remove_co_admin(query, context):
    """Remove a co-admin."""
    user_id = query.data.replace("admin_remove_coadmin_", "")
    admin_id = str(query.from_user.id)
    
    if db.remove_co_admin(user_id):
        await query.edit_message_text(f"✅ Co-admin {user_id} removed successfully!")
    else:
        await query.edit_message_text(f"❌ Failed to remove co-admin {user_id}")
    
    # Show updated co-admin list
    await co_admin_menu(query, context)

async def broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle broadcast message."""
    query = update.callback_query
    await query.answer()
    
    context.user_data['waiting_for_broadcast'] = True
    await query.edit_message_text(
        "📢 **Broadcast Message**\n\n"
        "Type your message below. It will be sent to all registered users.\n"
        "Send /cancel to cancel.",
        parse_mode='Markdown'
    )

async def send_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send broadcast message to all users."""
    user_id = str(update.effective_user.id)
    message_text = update.message.text
    
    if message_text == "/cancel":
        context.user_data['waiting_for_broadcast'] = False
        await update.message.reply_text("❌ Broadcast cancelled!")
        return
    
    # Get all users
    users = db.get_all_users()
    
    if not users:
        await update.message.reply_text("❌ No users to broadcast to!")
        return
    
    sent = 0
    failed = 0
    
    for user in users:
        try:
            await context.bot.send_message(
                chat_id=user,
                text=f"📢 **Broadcast Message**\n\n{message_text}\n\n"
                     f"---\n"
                     f"Bot for @{CHANNEL_USERNAME}\n"
                     f"Provided by @{PROVIDER_USERNAME}",
                parse_mode='Markdown'
            )
            sent += 1
        except Exception as e:
            failed += 1
    
    context.user_data['waiting_for_broadcast'] = False
    
    await update.message.reply_text(
        f"✅ **Broadcast Complete!**\n\n"
        f"• Sent: {sent} users\n"
        f"• Failed: {failed} users\n"
        f"• Total: {len(users)} users"
    )

async def view_all_users(query):
    """View all registered users."""
    users = db.get_all_users()
    
    if not users:
        text = "No users registered yet!"
    else:
        text = f"**📋 Registered Users**\n\n"
        text += f"Total Users: {len(users)}\n\n"
        text += "User IDs:\n"
        for user in users[:20]:  # Show first 20
            text += f"• `{user}`\n"
        if len(users) > 20:
            text += f"\n...and {len(users) - 20} more users."
    
    keyboard = [
        [InlineKeyboardButton("🔄 Refresh", callback_data="admin_users")],
        [InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_panel")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
