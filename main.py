import logging
from datetime import datetime

from telegram import BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from config import BOT_TOKEN, DB_PATH, SIGNUP_STATES, REMIND_STATES
from database import set_db_path, init_db, get_pending_reminders
from utils.logger import setup_logging

from handlers.start import start
from handlers.signup import (
    signup_start, choose_telegram, choose_email_enable,
    ask_email, ask_otp, signup_cancel
)
from handlers.reminders import (
    test_remind, remind_natural, remind_start, remind_ask_date, remind_ask_time,
    remind_confirm, remind_save, remind_cancel, list_reminders,
    cancel_reminder, send_reminder_job
)

logger = logging.getLogger(__name__)

async def set_bot_commands(application: Application):
    """Bot commands menu automatically set karo"""
    commands = [
        BotCommand("start", "Bot start karo aur status dekho"),
        BotCommand("signup", "Channels setup/update karo"),
        BotCommand("remind", "🤖 AI reminder (10 min baad, kal 5pm)"),
        BotCommand("remindstep", "Step-by-step reminder setup"),
        BotCommand("list", "Pending reminders dekho"),
        BotCommand("cancel", "Reminder cancel karo (ID se)"),
    ]
    
    await application.bot.set_my_commands(commands)
    logger.info("✅ Bot commands menu set successfully")

async def post_init(application: Application):
    """Bot start hone ke baad run hoga"""
    await set_bot_commands(application)
    logger.info("Post-initialization complete")

def restore_pending_reminders(application: Application):
    """Bot restart ke baad pending reminders ko JobQueue mein wapas load karo"""
    logger.info("Restoring pending reminders from database...")
    
    rows = get_pending_reminders()
    now = datetime.now()
    restored = 0
    skipped = 0
    
    for rid, chat_id, text, run_at_str, job_name in rows:
        try:
            run_at = datetime.fromisoformat(run_at_str)
            
            if run_at <= now:
                logger.warning(f"Reminder {rid} time already passed, skipping")
                skipped += 1
                continue
            
            delay_seconds = (run_at - now).total_seconds()
            
            application.job_queue.run_once(
                send_reminder_job,
                when=delay_seconds,
                chat_id=chat_id,
                data={"text": text, "db_id": rid},
                name=job_name,
            )
            
            restored += 1
            logger.info(f"Restored reminder {rid} for chat {chat_id}")
            
        except Exception as e:
            logger.error(f"Failed to restore reminder {rid}: {e}")
    
    logger.info(f"✅ Restore complete: {restored} restored, {skipped} skipped")

def main():
    setup_logging()
    logger.info("🚀 Starting AI-Powered Reminder Bot...")
    
    set_db_path(DB_PATH)
    init_db()
    
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )
    
    restore_pending_reminders(application)
    
    # SIGNUP conversation - Email only
    signup_conv = ConversationHandler(
        entry_points=[CommandHandler("signup", signup_start)],
        states={
            SIGNUP_STATES["CHOOSE_TELEGRAM"]: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, choose_telegram)
            ],
            SIGNUP_STATES["CHOOSE_EMAIL_ENABLE"]: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, choose_email_enable)
            ],
            SIGNUP_STATES["ASK_EMAIL"]: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, ask_email)
            ],
            SIGNUP_STATES["ASK_OTP"]: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, ask_otp)
            ],
        },
        fallbacks=[CommandHandler("signupcancel", signup_cancel)],
    )
    
    # REMIND STEP-BY-STEP conversation
    remindstep_conv = ConversationHandler(
        entry_points=[CommandHandler("remindstep", remind_start)],
        states={
            REMIND_STATES["ASK_TEXT"]: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, remind_ask_date)
            ],
            REMIND_STATES["ASK_DATE"]: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, remind_ask_time)
            ],
            REMIND_STATES["ASK_TIME"]: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, remind_confirm)
            ],
            REMIND_STATES["CONFIRM"]: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, remind_save)
            ],
        },
        fallbacks=[CommandHandler("remindcancel", remind_cancel)],
    )
    
    # Register all handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(signup_conv)
    
    # IMPORTANT: Natural language /remind should be BEFORE conversation handler
    application.add_handler(CommandHandler("remind", remind_natural))
    application.add_handler(remindstep_conv)
    
    application.add_handler(CommandHandler("testremind", test_remind))
    application.add_handler(CommandHandler("list", list_reminders))
    application.add_handler(CommandHandler("cancel", cancel_reminder))
    
    logger.info("✅ Bot is running... Press Ctrl+C to stop.")
    print("\n" + "="*60)
    print("🤖 AI-Powered Reminder Bot Successfully Started!")
    print("="*60)
    print("🚀 Features:")
    print("  • Natural Language Processing (dateparser + Gemini AI)")
    print("  • Multi-channel reminders (Telegram + Email)")
    print("  • OTP verification with expiry")
    print("  • Persistent reminders (survives bot restart)")
    print("="*60)
    print("📱 Available Commands:")
    print("  /start      - Check bot status")
    print("  /signup     - Setup channels (Telegram + Email)")
    print("  /remind     - 🤖 AI reminder (10 min baad, kal 5pm)")
    print("  /remindstep - Step-by-step reminder")
    print("  /testremind - Test 20-second reminder")
    print("  /list       - View pending reminders")
    print("  /cancel     - Cancel a reminder")
    print("="*60)
    print("🔥 Example AI commands:")
    print("  /remind 10 min baad meeting")
    print("  /remind kal shaam 5 baje gym")
    print("  /remind tomorrow morning exercise")
    print("  /remind 2 hours baad khaana banana")
    print("="*60 + "\n")
    
    application.run_polling()

if __name__ == "__main__":
    main()
