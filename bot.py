import os
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from database import Database
from admin import admin_panel, admin_callback, add_co_admin, broadcast_message, edit_stats
from config import BOT_TOKEN, ADMIN_IDS, CHANNEL_USERNAME, PROVIDER_USERNAME

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize database
db = Database()

# User states
WAITING_FOR_BROADCAST = 1
WAITING_FOR_STATS_EDIT = 2

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when /start is issued."""
    user = update.effective_user
    user_id = str(user.id)
    username = user.username or user.first_name
    
    # Register user in database
    db.register_user(user_id, username)
    
    # Check if user is admin
    is_admin = user_id in ADMIN_IDS or db.is_co_admin(user_id)
    
    # Welcome message
    welcome_text = f"Welcome **{username.upper()}!**\n\n"
    welcome_text += f"• Escrow Bot for @{CHANNEL_USERNAME}\n"
    welcome_text += f"• Provided by @{PROVIDER_USERNAME}\n\n"
    welcome_text += "• This is Your Personal Dashboard:\n\n"
    welcome_text += "Select the option below"
    
    # Main keyboard
    keyboard = [
        [InlineKeyboardButton("📊 My Stats", callback_data="my_stats")],
        [InlineKeyboardButton("📋 My Deals Info", callback_data="my_deals")],
        [InlineKeyboardButton("⏳ My Pending Deals", callback_data="pending_deals")],
        [InlineKeyboardButton("🌍 Escrow Global Stats", callback_data="global_stats")]
    ]
    
    # Add admin button if user is admin
    if is_admin:
        keyboard.append([InlineKeyboardButton("⚙️ Admin Panel", callback_data="admin_panel")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks."""
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    data = query.data
    
    if data == "my_stats":
        await show_stats(query, user_id)
    elif data == "my_deals":
        await show_deals(query, user_id)
    elif data == "pending_deals":
        await show_pending_deals(query, user_id)
    elif data == "global_stats":
        await show_global_stats(query)
    elif data == "admin_panel":
        if user_id in ADMIN_IDS or db.is_co_admin(user_id):
            await admin_panel(query)
        else:
            await query.edit_message_text("❌ You are not authorized to access admin panel!")
    elif data == "refresh_stats":
        await show_stats(query, user_id)
    elif data == "back":
        await start_from_callback(query)
    elif data.startswith("admin_"):
        await admin_callback(update, context)
    elif data.startswith("edit_stats_"):
        await edit_stats(update, context)
    elif data.startswith("add_admin_"):
        await add_co_admin(update, context)
    elif data.startswith("broadcast_"):
        await broadcast_message(update, context)

async def show_stats(query, user_id):
    """Show user stats."""
    user_data = db.get_user_stats(user_id)
    
    if not user_data:
        text = "No data found for you!"
    else:
        username = user_data.get('username', 'User')
        rank = user_data.get('rank', '#N/A')
        active_deals = user_data.get('active_deals', 0)
        total_escrows = user_data.get('total_escrows', 0)
        volume_ton = user_data.get('volume_ton', 0)
        volume_usdt = user_data.get('volume_usdt', 0)
        volume_inr = user_data.get('volume_inr', 0)
        
        text = f"**{username} Deal stats !**\n\n"
        text += f"- **Rank** ➤ {rank}\n"
        text += f"- **Active deals** ➤ {active_deals}\n"
        text += f"- **Total Escrow's** ➤ {total_escrows}\n"
        text += f"- **Total Volume** :\n"
        text += f"  - **TON** ➤ {volume_ton}\n"
        text += f"  - **USDT** ➤ {volume_usdt}\n"
        text += f"  - **₮** ➤ {volume_inr}\n\n"
        text += f"**Escrow Bot for @{CHANNEL_USERNAME}**\n"
        text += f"Provided by @{PROVIDER_USERNAME} !"
    
    keyboard = [
        [InlineKeyboardButton("🔄 Refresh", callback_data="refresh_stats")],
        [InlineKeyboardButton("🔙 Back", callback_data="back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def show_deals(query, user_id):
    """Show user deals."""
    deals = db.get_user_deals(user_id)
    
    if not deals:
        text = "No deals found for you!"
    else:
        text = f"**Your Deals**\n\n"
        for deal in deals:
            text += f"• Deal #{deal['id']}: {deal['status']} - {deal['amount']} {deal['currency']}\n"
        text += f"\n**Escrow Bot for @{CHANNEL_USERNAME}**\n"
        text += f"Provided by @{PROVIDER_USERNAME} !"
    
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def show_pending_deals(query, user_id):
    """Show pending deals."""
    pending = db.get_pending_deals(user_id)
    
    if not pending:
        text = "You have no Pending deals!"
    else:
        text = f"**Pending Deals**\n\n"
        for deal in pending:
            text += f"• Deal #{deal['id']}: {deal['amount']} {deal['currency']} - {deal['status']}\n"
    
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def show_global_stats(query):
    """Show global statistics."""
    stats = db.get_global_stats()
    
    total_deals = stats.get('total_deals', 0)
    total_volume_ton = stats.get('total_volume_ton', 0)
    total_volume_usdt = stats.get('total_volume_usdt', 0)
    total_volume_inr = stats.get('total_volume_inr', 0)
    
    text = f"**Escrow Global Statistics**\n\n"
    text += f"- **Total Deals:** {total_deals}\n\n"
    text += f"- **Total Volume:**\n"
    text += f"  - {total_volume_ton} TON\n"
    text += f"  - {total_volume_usdt} USDT\n"
    text += f"  - {total_volume_inr} INR\n\n"
    text += f"- **Escrow Bot for @{CHANNEL_USERNAME}**\n"
    text += f"- **Provided by @{PROVIDER_USERNAME}**"
    
    keyboard = [
        [InlineKeyboardButton("🔄 Refresh", callback_data="refresh_stats")],
        [InlineKeyboardButton("🔙 Back", callback_data="back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def start_from_callback(query):
    """Start from callback."""
    user_id = str(query.from_user.id)
    username = query.from_user.username or query.from_user.first_name
    is_admin = user_id in ADMIN_IDS or db.is_co_admin(user_id)
    
    welcome_text = f"Welcome **{username.upper()}!**\n\n"
    welcome_text += f"• Escrow Bot for @{CHANNEL_USERNAME}\n"
    welcome_text += f"• Provided by @{PROVIDER_USERNAME}\n\n"
    welcome_text += "• This is Your Personal Dashboard:\n\n"
    welcome_text += "Select the option below"
    
    keyboard = [
        [InlineKeyboardButton("📊 My Stats", callback_data="my_stats")],
        [InlineKeyboardButton("📋 My Deals Info", callback_data="my_deals")],
        [InlineKeyboardButton("⏳ My Pending Deals", callback_data="pending_deals")],
        [InlineKeyboardButton("🌍 Escrow Global Stats", callback_data="global_stats")]
    ]
    
    if is_admin:
        keyboard.append([InlineKeyboardButton("⚙️ Admin Panel", callback_data="admin_panel")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        welcome_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

def main():
    """Start the bot."""
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    
    # Add callback query handler
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Add message handler for admin operations
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_messages))
    
    # Start the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

async def handle_admin_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin messages for broadcast and stats edit."""
    user_id = str(update.effective_user.id)
    
    if user_id in ADMIN_IDS or db.is_co_admin(user_id):
        if context.user_data.get('waiting_for_broadcast'):
            await send_broadcast(update, context)
        elif context.user_data.get('waiting_for_stats_edit'):
            await save_stats_edit(update, context)

if __name__ == '__main__':
    main()
