from telegram import Update
from telegram.ext import ContextTypes
import logging
from database import is_user_verified, get_channels_summary

logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    logger.info(f"Start command from chat {chat_id}")
    
    if is_user_verified(chat_id):
        summary = get_channels_summary(chat_id)
        await update.message.reply_text(
            "Hello! 👋\n\n"
            "Tum already signup + verified ho.\n\n"
            f"Tumhare channels:\n{summary}\n\n"
            "Commands:\n"
            "• /remind - Naya reminder set karo\n"
            "• /testremind - 20-second test reminder\n"
            "• /list - Pending reminders dekho\n"
            "• /cancel <id> - Reminder cancel karo\n"
            "• /signup - Channels change karo"
        )
    else:
        await update.message.reply_text(
            "Hello! 👋\n\n"
            "Pehle signup complete karo, taaki pata ho reminder kahan bhejna hai.\n\n"
            "Start karne ke liye /signup bhejo."
        )
