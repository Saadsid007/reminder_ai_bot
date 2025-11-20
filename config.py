from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DB_PATH = Path("reminders.db")

# Gmail config
GMAIL_EMAIL = os.getenv("GMAIL_EMAIL")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")

# Gemini AI config
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

SIGNUP_STATES = {
    "CHOOSE_TELEGRAM": 0,
    "CHOOSE_EMAIL_ENABLE": 1,
    "ASK_EMAIL": 2,
    "ASK_OTP": 3,
}

REMIND_STATES = {
    "ASK_TEXT": 10,
    "ASK_DATE": 11,
    "ASK_TIME": 12,
    "CONFIRM": 13,
}

OTP_EXPIRY_MINUTES = 10
MAX_OTP_ATTEMPTS = 3
