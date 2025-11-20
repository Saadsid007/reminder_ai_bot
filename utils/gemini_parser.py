import os
import json
import logging
from datetime import datetime, timedelta
import google.generativeai as genai

from config import GEMINI_API_KEY

logger = logging.getLogger(__name__)

# Initialize Gemini
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        logger.info("✅ Gemini AI initialized successfully")
    except Exception as e:
        model = None
        logger.error(f"❌ Gemini initialization failed: {e}")
else:
    model = None
    logger.warning("⚠️ Gemini API key not found, AI parsing disabled")

def parse_with_gemini(text: str) -> dict:
    """
    Advanced AI parsing using Google Gemini
    Handles complex Hindi-English mixed queries
    """
    if not model:
        return {
            "success": False, 
            "error": "Gemini AI not configured. Add GEMINI_API_KEY to .env file"
        }
    
    try:
        current_datetime = datetime.now()
        current_time_str = current_datetime.strftime("%Y-%m-%d %H:%M")
        tomorrow = (current_datetime + timedelta(days=1)).strftime("%Y-%m-%d")
        
        prompt = f"""
You are a smart reminder parser. Current date and time is: {current_time_str} (IST - Indian Standard Time)

Parse this reminder request and extract the exact datetime and reminder text:
"{text}"

IMPORTANT RULES:
1. Parse both Hindi and English words
2. Common Hindi time words:
   - "baad" = after/later
   - "kal" = tomorrow ({tomorrow})
   - "aaj" = today
   - "parso" = day after tomorrow
   - "subah" = morning (9:00 AM)
   - "dopahar" = afternoon (2:00 PM)
   - "shaam" = evening (6:00 PM)
   - "raat" = night (9:00 PM)
   - "min/minute" = minutes
   - "ghante/hour" = hours
   - "baje" = o'clock

3. Time calculations:
   - "10 min baad" = add 10 minutes to current time
   - "2 ghante baad" = add 2 hours to current time
   - "kal 5 baje" = tomorrow at 5:00 PM (17:00)
   - "tomorrow 9am" = tomorrow at 09:00

4. Default assumptions:
   - If only hour given (like "5 baje"), assume PM if hour < 12, else keep as is
   - If "subah/morning" mentioned, use 9:00 AM
   - If "shaam/evening" mentioned, use 6:00 PM

5. Return ONLY a valid JSON object (no markdown, no extra text):
{{
  "datetime": "YYYY-MM-DD HH:MM",
  "reminder_text": "the actual reminder message without time info"
}}

6. If you cannot parse, return:
{{
  "datetime": null,
  "reminder_text": null
}}

Examples:
Input: "10 min baad meeting attend karna"
Output: {{"datetime": "{(current_datetime + timedelta(minutes=10)).strftime('%Y-%m-%d %H:%M')}", "reminder_text": "meeting attend karna"}}

Input: "kal shaam 5 baje gym jana"
Output: {{"datetime": "{tomorrow} 17:00", "reminder_text": "gym jana"}}

Input: "tomorrow morning call karna"
Output: {{"datetime": "{tomorrow} 09:00", "reminder_text": "call karna"}}

Input: "2 hours baad khaana banana"
Output: {{"datetime": "{(current_datetime + timedelta(hours=2)).strftime('%Y-%m-%d %H:%M')}", "reminder_text": "khaana banana"}}

Now parse: "{text}"
"""
        
        logger.info(f"Sending to Gemini: {text}")
        
        response = model.generate_content(prompt)
        result_text = response.text.strip()
        
        logger.info(f"Gemini response: {result_text}")
        
        # Clean markdown code blocks if present
        result_text = result_text.replace('``````', '').strip()
        
        # Parse JSON response
        parsed = json.loads(result_text)
        
        if not parsed.get("datetime") or not parsed.get("reminder_text"):
            logger.warning("Gemini returned null values")
            return {
                "success": False, 
                "error": "Date/time samajh nahi aaya. Clear mention karo jaise: '10 min baad', 'kal 5pm'"
            }
        
        # Convert to datetime object
        reminder_dt = datetime.strptime(parsed["datetime"], "%Y-%m-%d %H:%M")
        
        # Validate future time
        if reminder_dt <= datetime.now():
            logger.warning(f"Gemini returned past time: {reminder_dt}")
            return {
                "success": False, 
                "error": "Ye time already nikal gaya hai. Future time do."
            }
        
        logger.info(f"✅ Gemini successfully parsed: {reminder_dt}")
        
        return {
            "success": True,
            "datetime": reminder_dt,
            "reminder_text": parsed["reminder_text"].strip(),
            "parsed_as": "🤖 Gemini AI"
        }
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {e}, Response: {result_text}")
        return {
            "success": False,
            "error": "AI response parse nahi hua, dobara try karo"
        }
    except Exception as e:
        logger.error(f"Gemini parsing error: {e}")
        return {
            "success": False,
            "error": f"AI error: {str(e)}"
        }

def is_gemini_available() -> bool:
    """Check if Gemini is configured and available"""
    return model is not None
