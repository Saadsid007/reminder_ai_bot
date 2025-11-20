from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler
import logging

from config import SIGNUP_STATES, OTP_EXPIRY_MINUTES
from database import save_channel, delete_channel, get_channels_summary, get_db
from utils.otp import create_otp, verify_otp, clear_otp
from utils.notifications import send_email_otp

logger = logging.getLogger(__name__)

CHOOSE_TELEGRAM = SIGNUP_STATES["CHOOSE_TELEGRAM"]
CHOOSE_EMAIL_ENABLE = SIGNUP_STATES["CHOOSE_EMAIL_ENABLE"]
ASK_EMAIL = SIGNUP_STATES["ASK_EMAIL"]
ASK_OTP = SIGNUP_STATES["ASK_OTP"]

async def signup_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    logger.info(f"Signup started for chat {chat_id}")
    
    clear_otp(chat_id)
    
    # Check existing channels
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT channel_type, is_verified FROM user_channels WHERE chat_id = ?",
            (chat_id,)
        )
        existing = {row[0]: bool(row[1]) for row in cur.fetchall()}
    
    if existing:
        msg = "📋 Tumhare current channels:\n\n"
        for ctype, verified in existing.items():
            status = "✅ verified" if verified else "⏳ pending"
            emoji = "📱" if ctype == "telegram" else "📧"
            msg += f"{emoji} {ctype.title()}: {status}\n"
        msg += "\n💡 Kya tum channels update karna chahte ho?"
        
        keyboard = [["Haan, update karo", "Nahi, rehne do"]]
        await update.message.reply_text(
            msg,
            reply_markup=ReplyKeyboardMarkup(
                keyboard, one_time_keyboard=True, resize_keyboard=True
            ),
        )
        context.user_data["updating"] = True
        return CHOOSE_TELEGRAM
    
    keyboard = [["Haan", "Nahi"]]
    await update.message.reply_text(
        "👋 Signup start kar rahe hain.\n\n"
        "📱 Kya tumhe **Telegram** pe (is chat pe) bhi reminder chahiye?",
        reply_markup=ReplyKeyboardMarkup(
            keyboard, one_time_keyboard=True, resize_keyboard=True
        ),
    )
    return CHOOSE_TELEGRAM

async def choose_telegram(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    choice = update.message.text.lower()
    
    # Handle "Nahi, rehne do" case
    if "rehne" in choice or "nahi" in choice.split(",")[0]:
        if context.user_data.get("updating"):
            await update.message.reply_text(
                "👍 Theek hai, channels same rahenge.",
                reply_markup=ReplyKeyboardRemove()
            )
            return ConversationHandler.END
        # Else continue normal flow for "Nahi"
    
    if "haa" in choice or "update" in choice:
        save_channel(chat_id, "telegram", str(chat_id), True)
        await update.message.reply_text("✅ Telegram channel add ho gaya.")
    elif not context.user_data.get("updating"):
        delete_channel(chat_id, "telegram")
        await update.message.reply_text("❌ Telegram skip kar diya.")
    
    keyboard = [["Haan", "Nahi"]]
    await update.message.reply_text(
        "📧 Kya tumhe **Email** pe bhi reminder chahiye?",
        reply_markup=ReplyKeyboardMarkup(
            keyboard, one_time_keyboard=True, resize_keyboard=True
        ),
    )
    return CHOOSE_EMAIL_ENABLE

async def choose_email_enable(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = update.message.text.lower()
    chat_id = update.effective_chat.id
    
    if choice.startswith("haa"):
        await update.message.reply_text(
            "✉️ Theek hai, apna **email address** bhejo.\n\n"
            "Example: example@gmail.com",
            reply_markup=ReplyKeyboardRemove(),
        )
        return ASK_EMAIL
    else:
        summary = get_channels_summary(chat_id)
        await update.message.reply_text(
            "✅ Signup complete ho gaya!\n\n"
            "📋 Tumhare selected channels:\n"
            f"{summary}\n\n"
            "💡 Ab /remind use karke reminder set kar sakte ho.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return ConversationHandler.END

async def ask_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    email = update.message.text.strip()
    
    # Basic email validation
    if "@" not in email or "." not in email.split("@")[-1]:
        await update.message.reply_text(
            "❌ Valid email address do.\n\n"
            "Example: example@gmail.com"
        )
        return ASK_EMAIL
    
    otp = create_otp(chat_id, "email", email, OTP_EXPIRY_MINUTES)
    
    try:
        send_email_otp(email, otp)
        await update.message.reply_text(
            f"✅ OTP tumhare email par bhej diya gaya hai.\n\n"
            f"⏰ OTP **{OTP_EXPIRY_MINUTES} minute** mein expire ho jayega.\n"
            f"🔐 Please yahan wahi OTP type karo.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return ASK_OTP
    except Exception as e:
        logger.error(f"Email send failed: {e}")
        await update.message.reply_text(
            "❌ Email bhejne mein error aaya.\n\n"
            "Please check karo:\n"
            "1. Email address sahi hai?\n"
            "2. Bot ka Gmail setup sahi hai?\n\n"
            "Dobara try karne ke liye /signup bhejo."
        )
        return ConversationHandler.END

async def ask_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_otp = update.message.text.strip()
    
    result = verify_otp(chat_id, user_otp)
    
    if not result["success"]:
        await update.message.reply_text(result["message"])
        if "Dobara" in result["message"]:
            return ConversationHandler.END
        return ASK_OTP
    
    data = result["data"]
    value = data["value"]
    
    save_channel(chat_id, "email", value, True)
    clear_otp(chat_id)
    
    summary = get_channels_summary(chat_id)
    await update.message.reply_text(
        "✅ Email verify ho gaya!\n\n"
        "🎉 Signup complete!\n\n"
        "📋 Tumhare channels:\n"
        f"{summary}\n\n"
        "💡 Ab /remind use karke reminder set kar sakte ho.",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END

async def signup_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    clear_otp(chat_id)
    logger.info(f"Signup cancelled for chat {chat_id}")
    await update.message.reply_text(
        "❌ Signup cancel kar diya gaya.\n\n"
        "Kabhi bhi /signup se dobara start kar sakte ho.",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END
