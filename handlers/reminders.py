from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler
from datetime import datetime
import logging

from config import REMIND_STATES
from database import (
    is_user_verified, save_reminder, get_pending_reminders,
    get_reminder_by_id, delete_reminder, get_user_channels
)
from utils.notifications import send_email_reminder
from utils.nlp_parser import parse_natural_reminder

logger = logging.getLogger(__name__)

ASK_TEXT = REMIND_STATES["ASK_TEXT"]
ASK_DATE = REMIND_STATES["ASK_DATE"]
ASK_TIME = REMIND_STATES["ASK_TIME"]
CONFIRM = REMIND_STATES["CONFIRM"]

# ========== JOB CALLBACK ==========

async def send_reminder_job(context: ContextTypes.DEFAULT_TYPE):
    """Actual reminder bhejne ka function - JobQueue se call hota hai"""
    job = context.job
    chat_id = job.chat_id
    data = job.data
    text = data["text"]
    db_id = data["db_id"]
    
    logger.info(f"Sending reminder {db_id} for chat {chat_id}")
    
    # User ke verified channels nikalo
    channels = get_user_channels(chat_id)
    reminder_msg = f"⏰ Reminder:\n{text}"
    
    sent_count = 0
    
    if channels:
        for ctype, value in channels:
            try:
                if ctype == "telegram":
                    await context.bot.send_message(
                        chat_id=int(value),
                        text=reminder_msg,
                    )
                    sent_count += 1
                    logger.info(f"Telegram reminder sent to chat {value}")
                    
                elif ctype == "email":
                    send_email_reminder(value, text)
                    sent_count += 1
                    logger.info(f"Email reminder sent to {value}")
                    
            except Exception as e:
                logger.error(f"Failed to send reminder via {ctype}: {e}")
    else:
        # Fallback: sirf Telegram chat me bhejo
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=reminder_msg,
            )
            sent_count += 1
            logger.warning(f"No channels found, sent to Telegram fallback for {chat_id}")
        except Exception as e:
            logger.error(f"Fallback Telegram send failed: {e}")
    
    # DB se reminder delete karo (test reminders ke liye db_id = -1)
    if db_id != -1:
        delete_reminder(db_id)
        logger.info(f"Reminder {db_id} deleted from database")
    
    logger.info(f"✅ Reminder {db_id} sent successfully to {sent_count} channel(s)")

# ========== /testremind COMMAND ==========

async def test_remind(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """20-second test reminder - quick testing ke liye"""
    chat_id = update.effective_chat.id
    logger.info(f"Test remind triggered by chat {chat_id}")
    
    reminder_text = "🧪 Yeh 20-second test reminder hai!"
    
    context.job_queue.run_once(
        send_reminder_job,
        when=20,
        chat_id=chat_id,
        data={"text": reminder_text, "db_id": -1},
        name=f"test_{chat_id}_{datetime.now().timestamp()}",
    )
    
    logger.info(f"Test reminder scheduled for chat {chat_id}")
    await update.message.reply_text(
        "✅ 20-second test reminder set ho gaya.\n\n"
        "⏰ 20 second ke andar ek test reminder message aayega.\n\n"
        "💡 Agar message aa gaya to sab kuch sahi hai!"
    )

# ========== NATURAL LANGUAGE /remind COMMAND ==========

async def remind_natural(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Natural language reminder parsing - AI powered one-line command
    Examples: /remind 10 min baad meeting, /remind kal 5pm gym
    """
    chat_id = update.effective_chat.id
    
    if not is_user_verified(chat_id):
        await update.message.reply_text(
            "❌ Pehle signup + OTP verify kar lo: /signup\n\n"
            "Channels setup karne ke baad hi reminder set kar sakte ho."
        )
        return
    
    # Get text after /remind
    if not context.args:
        await update.message.reply_text(
            "🤖 **AI-Powered Natural Language Reminder**\n\n"
            "📝 Examples:\n"
            "• `/remind 10 min baad meeting attend karna`\n"
            "• `/remind kal shaam 5 baje gym jana`\n"
            "• `/remind tomorrow 9am call karna`\n"
            "• `/remind 2 hours baad khaana banana`\n"
            "• `/remind next monday 10am presentation`\n\n"
            "💡 Ya step-by-step reminder ke liye /remindstep use karo"
        )
        return
    
    full_text = ' '.join(context.args)
    logger.info(f"🤖 Natural language reminder: {full_text}")
    
    # Show processing message
    processing_msg = await update.message.reply_text("🔄 Parsing reminder...")
    
    # Parse natural language
    result = parse_natural_reminder(full_text)
    
    if not result["success"]:
        await processing_msg.edit_text(
            f"❌ {result['error']}"
        )
        return
    
    reminder_dt = result["datetime"]
    text = result["reminder_text"]
    parsed_as = result.get("parsed_as", "")
    
    # Calculate delay
    delay_seconds = (reminder_dt - datetime.now()).total_seconds()
    
    if delay_seconds <= 0:
        await processing_msg.edit_text(
            "❌ Ye time already nikal gaya hai.\n"
            "Future time do."
        )
        return
    
    # Save to DB
    job_name = f"reminder_{chat_id}_{reminder_dt.timestamp()}"
    rid = save_reminder(chat_id, text, reminder_dt.isoformat(), job_name)
    
    # Schedule job
    context.job_queue.run_once(
        send_reminder_job,
        when=delay_seconds,
        chat_id=chat_id,
        data={"text": text, "db_id": rid},
        name=job_name,
    )
    
    logger.info(f"✅ Natural reminder {rid} scheduled: {parsed_as}")
    
    # Human readable time
    hours = int(delay_seconds // 3600)
    minutes = int((delay_seconds % 3600) // 60)
    if hours > 0:
        time_msg = f"{hours}h {minutes}m"
    else:
        time_msg = f"{minutes}m"
    
    await processing_msg.edit_text(
        f"✅ **Reminder set ho gaya!**\n\n"
        f"🆔 ID: {rid}\n"
        f"📝 Text: {text}\n"
        f"⏰ Time: {reminder_dt.strftime('%d %b %Y, %I:%M %p')}\n"
        f"🕐 {time_msg} mein reminder jayega\n"
        f"{parsed_as}\n\n"
        f"💡 Commands:\n"
        f"• /list - Pending reminders dekho\n"
        f"• /cancel {rid} - Ye reminder cancel karo"
    )

# ========== INTERACTIVE /remindstep FLOW ==========

async def remind_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Step 1: Reminder text pucho"""
    chat_id = update.effective_chat.id
    
    if not is_user_verified(chat_id):
        await update.message.reply_text(
            "❌ Pehle signup + OTP verify kar lo: /signup\n\n"
            "Channels setup karne ke baad hi reminder set kar sakte ho."
        )
        return ConversationHandler.END
    
    logger.info(f"Interactive remind started for chat {chat_id}")
    
    await update.message.reply_text(
        "📝 Reminder kya hai? Message likho:\n\n"
        "Example:\n"
        "• Pani peena\n"
        "• Meeting attend karna\n"
        "• Gym jana\n"
        "• Medicine lena",
        reply_markup=ReplyKeyboardRemove()
    )
    return ASK_TEXT

async def remind_ask_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Step 2: Text save karo aur date pucho"""
    text = update.message.text.strip()
    
    if len(text) < 3:
        await update.message.reply_text(
            "❌ Reminder text thoda bada likho (at least 3 characters).\n\n"
            "Dobara try karo:"
        )
        return ASK_TEXT
    
    context.user_data["reminder_text"] = text
    logger.info(f"Reminder text saved: {text}")
    
    await update.message.reply_text(
        f"✅ Text saved: {text}\n\n"
        f"📅 Reminder ki **date** kya hai?\n\n"
        f"Format: YYYY-MM-DD\n"
        f"Example: 2025-11-18"
    )
    return ASK_DATE

async def remind_ask_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Step 3: Date validate karo aur time pucho"""
    date_str = update.message.text.strip()
    
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        
        # Check if date is not in past
        if date_obj.date() < datetime.now().date():
            await update.message.reply_text(
                "❌ Ye date past mein hai.\n\n"
                "Future ki date do (today ya aage ki).\n"
                "Dobara try karo:"
            )
            return ASK_DATE
            
        context.user_data["reminder_date"] = date_str
        logger.info(f"Date saved: {date_str}")
        
    except ValueError:
        await update.message.reply_text(
            "❌ Date galat format mein hai.\n\n"
            "Sahi format: YYYY-MM-DD\n"
            "Example: 2025-11-22\n\n"
            "Dobara try karo:"
        )
        return ASK_DATE
    
    await update.message.reply_text(
        f"✅ Date saved: {date_str}\n\n"
        f"⏰ Reminder ka **time** kya hai?\n\n"
        f"Format: HH:MM (24-hour)\n"
        f"Example:\n"
        f"• 09:30 (subah 9:30)\n"
        f"• 14:00 (dopahar 2:00)\n"
        f"• 18:45 (shaam 6:45)"
    )
    return ASK_TIME

async def remind_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Step 4: Time validate karo aur confirmation pucho"""
    time_str = update.message.text.strip()
    date_str = context.user_data["reminder_date"]
    
    try:
        reminder_dt = datetime.strptime(
            f"{date_str} {time_str}", "%Y-%m-%d %H:%M"
        )
    except ValueError:
        await update.message.reply_text(
            "❌ Time galat format mein hai.\n\n"
            "Sahi format: HH:MM\n"
            "Example: 14:30\n\n"
            "Dobara try karo:"
        )
        return ASK_TIME
    
    now = datetime.now()
    if reminder_dt <= now:
        time_diff = (now - reminder_dt).total_seconds() / 60
        await update.message.reply_text(
            f"❌ Ye time already nikal chuka hai ({int(time_diff)} minutes pehle).\n\n"
            "Future time do (at least 1-2 minute aage).\n"
            "Dobara try karo:"
        )
        return ASK_TIME
    
    context.user_data["reminder_time"] = time_str
    context.user_data["reminder_dt"] = reminder_dt
    
    text = context.user_data["reminder_text"]
    time_diff = (reminder_dt - now).total_seconds() / 60
    
    logger.info(f"Confirmation pending: {text} at {reminder_dt}")
    
    keyboard = [["✅ Confirm", "❌ Cancel"]]
    await update.message.reply_text(
        f"📋 **Confirmation**\n\n"
        f"📝 Text: {text}\n"
        f"📅 Date: {date_str}\n"
        f"⏰ Time: {time_str}\n"
        f"🕐 Reminder {int(time_diff)} minutes mein jayega\n\n"
        f"✅ Confirm karo ya ❌ Cancel?",
        reply_markup=ReplyKeyboardMarkup(
            keyboard, one_time_keyboard=True, resize_keyboard=True
        )
    )
    return CONFIRM

async def remind_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Step 5: Final save karo aur job schedule karo"""
    chat_id = update.effective_chat.id
    choice = update.message.text.lower()
    
    if "cancel" in choice or "❌" in choice:
        logger.info(f"Reminder cancelled by user {chat_id}")
        await update.message.reply_text(
            "❌ Reminder cancel kar diya.\n\n"
            "Naya reminder set karne ke liye /remind ya /remindstep bhejo.",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END
    
    text = context.user_data["reminder_text"]
    reminder_dt = context.user_data["reminder_dt"]
    
    delay_seconds = (reminder_dt - datetime.now()).total_seconds()
    job_name = f"reminder_{chat_id}_{reminder_dt.timestamp()}"
    
    # DB mein save karo
    rid = save_reminder(chat_id, text, reminder_dt.isoformat(), job_name)
    
    # JobQueue mein schedule karo
    context.job_queue.run_once(
        send_reminder_job,
        when=delay_seconds,
        chat_id=chat_id,
        data={"text": text, "db_id": rid},
        name=job_name,
    )
    
    logger.info(f"✅ Reminder {rid} scheduled for chat {chat_id} at {reminder_dt}")
    
    # Calculate human-readable time
    hours = int(delay_seconds // 3600)
    minutes = int((delay_seconds % 3600) // 60)
    time_msg = ""
    if hours > 0:
        time_msg = f"{hours} hour(s) {minutes} minute(s)"
    else:
        time_msg = f"{minutes} minute(s)"
    
    await update.message.reply_text(
        f"✅ **Reminder set ho gaya!**\n\n"
        f"🆔 ID: {rid}\n"
        f"📝 Text: {text}\n"
        f"⏰ Time: {reminder_dt.strftime('%Y-%m-%d %H:%M')}\n"
        f"🕐 Reminder {time_msg} mein jayega\n\n"
        f"💡 Commands:\n"
        f"• /list - Pending reminders dekho\n"
        f"• /cancel {rid} - Ye reminder cancel karo",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

async def remind_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Conversation cancel karo"""
    chat_id = update.effective_chat.id
    logger.info(f"Remind conversation cancelled by chat {chat_id}")
    await update.message.reply_text(
        "❌ Reminder setup cancel kar diya.\n\n"
        "Dobara start karne ke liye /remind ya /remindstep bhejo.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

# ========== /list COMMAND ==========

async def list_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User ke saare pending reminders show karo"""
    chat_id = update.effective_chat.id
    
    if not is_user_verified(chat_id):
        await update.message.reply_text(
            "❌ Pehle signup + OTP verify kar lo: /signup"
        )
        return
    
    rows = get_pending_reminders(chat_id)
    
    if not rows:
        await update.message.reply_text(
            "📭 Abhi koi pending reminder nahi hai.\n\n"
            "💡 Naya reminder set karne ke liye:\n"
            "• /remind - Natural language AI reminder\n"
            "• /remindstep - Step-by-step reminder"
        )
        return
    
    logger.info(f"Listing {len(rows)} reminders for chat {chat_id}")
    
    lines = []
    for rid, text, run_at in rows:
        try:
            run_dt = datetime.fromisoformat(run_at)
            formatted_time = run_dt.strftime("%d %b %Y, %I:%M %p")
            
            # Calculate time remaining
            now = datetime.now()
            diff = (run_dt - now).total_seconds()
            if diff > 0:
                hours = int(diff // 3600)
                minutes = int((diff % 3600) // 60)
                if hours > 0:
                    time_left = f"{hours}h {minutes}m"
                else:
                    time_left = f"{minutes}m"
                time_status = f"🕐 {time_left} mein"
            else:
                time_status = "⚠️ Time passed"
            
            lines.append(
                f"🆔 ID: {rid}\n"
                f"📝 {text}\n"
                f"⏰ {formatted_time}\n"
                f"{time_status}\n"
            )
        except Exception as e:
            logger.error(f"Error formatting reminder {rid}: {e}")
            lines.append(f"🆔 ID: {rid}\n📝 {text}\n⏰ {run_at}\n")
    
    msg = f"📋 **Tumhare pending reminders ({len(rows)}):**\n\n" + "\n".join(lines)
    msg += "\n💡 Cancel karne ke liye: /cancel <id>"
    
    await update.message.reply_text(msg)

# ========== /cancel COMMAND ==========

async def cancel_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reminder cancel karo by ID"""
    chat_id = update.effective_chat.id
    
    # Fix: Handle both message and callback_query
    if update.message:
        message = update.message
    elif update.callback_query:
        message = update.callback_query.message
        await update.callback_query.answer()
    else:
        logger.error("No message or callback_query found in update")
        return
    
    if not is_user_verified(chat_id):
        await message.reply_text(
            "❌ Pehle signup + OTP verify kar lo: /signup"
        )
        return
    
    if not context.args:
        await message.reply_text(
            "❌ Reminder ID do.\n\n"
            "Usage: /cancel <reminder_id>\n"
            "Example: /cancel 5\n\n"
            "💡 IDs dekhne ke liye /list bhejo."
        )
        return
    
    try:
        rid = int(context.args[0])
    except ValueError:
        await message.reply_text(
            "❌ Reminder ID number hona chahiye.\n\n"
            "Example: /cancel 5"
        )
        return
    
    # DB se job_name nikalo
    row = get_reminder_by_id(rid, chat_id)
    
    if not row:
        await message.reply_text(
            f"❌ ID {rid} ka koi reminder nahi mila.\n\n"
            f"💡 /list se check karo konse reminders pending hain."
        )
        return
    
    job_name = row[0]
    
    # DB se delete
    delete_reminder(rid, chat_id)
    
    # JobQueue se job hatao
    current_jobs = context.job_queue.get_jobs_by_name(job_name)
    removed_count = 0
    for job in current_jobs:
        job.schedule_removal()
        removed_count += 1
    
    logger.info(f"Reminder {rid} cancelled by chat {chat_id} ({removed_count} job(s) removed)")
    
    await message.reply_text(
        f"✅ Reminder {rid} cancel kar diya gaya.\n\n"
        f"💡 Baaki reminders dekhne ke liye /list bhejo."
    )

