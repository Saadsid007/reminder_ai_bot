import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from config import GMAIL_EMAIL, GMAIL_APP_PASSWORD

logger = logging.getLogger(__name__)

def send_email_otp(email: str, otp: str):
    """Gmail SMTP se email OTP bhejo"""
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = "🔐 Tumhara Reminder Bot OTP"
        msg['From'] = GMAIL_EMAIL
        msg['To'] = email
        
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px; background-color: #f5f5f5;">
            <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                <h2 style="color: #4CAF50; text-align: center;">🔐 Email Verification</h2>
                <p style="font-size: 16px; color: #333;">Namaste!</p>
                <p style="font-size: 16px; color: #333;">Tumhara OTP yeh hai:</p>
                
                <div style="background-color: #4CAF50; color: white; padding: 20px; text-align: center; border-radius: 5px; margin: 20px 0;">
                    <h1 style="margin: 0; font-size: 36px; letter-spacing: 5px;">{otp}</h1>
                </div>
                
                <p style="font-size: 14px; color: #666;">⚠️ Ye OTP 10 minute mein expire ho jayega.</p>
                <p style="font-size: 14px; color: #666;">Agar tumne ye request nahi kiya, to is email ko ignore kar do.</p>
                
                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                <p style="font-size: 12px; color: #999; text-align: center;">Sent by Reminder Bot 🤖</p>
            </div>
        </body>
        </html>
        """
        
        html_part = MIMEText(html_body, 'html')
        msg.attach(html_part)
        
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(GMAIL_EMAIL, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_EMAIL, email, msg.as_string())
        
        logger.info(f"Email OTP sent to {email}")
        print(f"✅ Email OTP sent to {email}")
    except Exception as e:
        logger.error(f"Failed to send email to {email}: {e}")
        print(f"❌ Email failed: {e}")
        raise

def send_email_reminder(email: str, text: str):
    """Gmail SMTP se email reminder bhejo"""
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = "⏰ Reminder - Reminder Bot"
        msg['From'] = GMAIL_EMAIL
        msg['To'] = email
        
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px; background-color: #f5f5f5;">
            <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                <h2 style="color: #FF9800; text-align: center;">⏰ Reminder</h2>
                
                <div style="background-color: #fff3e0; padding: 20px; border-left: 4px solid #FF9800; border-radius: 5px; margin: 20px 0;">
                    <p style="font-size: 18px; color: #333; margin: 0; white-space: pre-wrap;">{text}</p>
                </div>
                
                <p style="font-size: 14px; color: #666; text-align: center;">Tumne yeh reminder pehle set kiya tha 📝</p>
                
                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                <p style="font-size: 12px; color: #999; text-align: center;">Sent by your Telegram Reminder Bot 🤖</p>
            </div>
        </body>
        </html>
        """
        
        html_part = MIMEText(html_body, 'html')
        msg.attach(html_part)
        
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(GMAIL_EMAIL, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_EMAIL, email, msg.as_string())
        
        logger.info(f"Email reminder sent to {email}")
        print(f"✅ Reminder email sent to {email}")
    except Exception as e:
        logger.error(f"Failed to send email reminder to {email}: {e}")
        print(f"❌ Email reminder failed: {e}")
