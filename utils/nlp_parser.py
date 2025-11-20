import re
import logging
from datetime import datetime, timedelta
import dateparser

logger = logging.getLogger(__name__)

def parse_natural_reminder(text: str) -> dict:
    """
    Natural language se reminder parse karo
    Multi-step parsing: Regex → dateparser → Gemini AI
    """
    
    # Hinglish to English mapping
    hinglish_replacements = {
        r'\bbaad\b': 'after',
        r'\bpehle\b': 'before',
        r'\bkal\b': 'tomorrow',
        r'\bparso\b': 'day after tomorrow',
        r'\baaj\b': 'today',
        r'\bsubah\b': 'morning',
        r'\bshaam\b': 'evening',
        r'\braat\b': 'night',
        r'\bdopahar\b': 'afternoon',
        r'\bmin\b': 'minutes',
        r'\bghante\b': 'hours',
        r'\bdin\b': 'days',
        r'\bhafta\b': 'week',
        r'\bmahina\b': 'month',
    }
    
    processed_text = text.lower()
    
    # Hinglish ko English mein convert karo
    for hindi, english in hinglish_replacements.items():
        processed_text = re.sub(hindi, english, processed_text, flags=re.IGNORECASE)
    
    logger.info(f"Original: {text} | Processed: {processed_text}")
    
    # ========== STEP 1: IMPROVED REGEX PATTERNS (ORDER MATTERS!) ==========
    
    patterns = [
        # Relative time - highest priority
        (r'(\d+)\s*(min|minute|minutes)\s*(baad|after|later)\s+(.+)', 'minutes_after'),
        (r'(\d+)\s*(ghante|hours?|hrs?)\s*(baad|after|later)\s+(.+)', 'hours_after'),
        (r'(\d+)\s*(din|days?)\s*(baad|after|later)\s+(.+)', 'days_after'),
        
        # Tomorrow with exact time (HH:MM format) - before simple time
        (r'(kal|tomorrow)\s+(?:raat|night|ko)?\s*(\d{1,2}):(\d{2})\s*(?:pe|baje|pm|am)?\s+(.+)', 'tomorrow_exact_time'),
        
        # Tomorrow with hour only
        (r'(kal|tomorrow)\s+(?:raat|night|shaam|evening|subah|morning)?\s*(\d+)\s*(baje|pm|am)\s+(.+)', 'tomorrow_time'),
        
        # Today night time
        (r'(aaj|today)\s+(?:raat|night)\s+(\d+)\s*(baje|pm|am)?\s+(.+)', 'today_night_time'),
        
        # Today with time
        (r'(aaj|today)\s+(\d+)\s*(baje|pm|am)?\s+(.+)', 'today_time'),
        
        # Exact time format HH:MM (without day) - check if it's for today
        (r'^(\d{1,2}):(\d{2})\s+(.+)', 'exact_time_today'),
        
        # Simple time (5pm, 10am) - lowest priority
        (r'^(\d+)\s*(pm|am|baje)\s+(.+)', 'time_today'),
    ]
    
    for pattern, pattern_type in patterns:
        match = re.search(pattern, processed_text, re.IGNORECASE)
        if match:
            logger.info(f"✅ Regex matched: {pattern_type}")
            
            try:
                if pattern_type == 'minutes_after':
                    minutes = int(match.group(1))
                    reminder_text = match.group(4).strip()
                    target_dt = datetime.now() + timedelta(minutes=minutes)
                    
                    return {
                        "success": True,
                        "datetime": target_dt,
                        "reminder_text": reminder_text,
                        "parsed_as": f"⚡ Regex: {minutes} minutes baad"
                    }
                
                elif pattern_type == 'hours_after':
                    hours = int(match.group(1))
                    reminder_text = match.group(4).strip()
                    target_dt = datetime.now() + timedelta(hours=hours)
                    
                    return {
                        "success": True,
                        "datetime": target_dt,
                        "reminder_text": reminder_text,
                        "parsed_as": f"⚡ Regex: {hours} hours baad"
                    }
                
                elif pattern_type == 'days_after':
                    days = int(match.group(1))
                    reminder_text = match.group(4).strip()
                    target_dt = datetime.now() + timedelta(days=days)
                    
                    return {
                        "success": True,
                        "datetime": target_dt,
                        "reminder_text": reminder_text,
                        "parsed_as": f"⚡ Regex: {days} days baad"
                    }
                
                elif pattern_type == 'tomorrow_exact_time':
                    hour = int(match.group(2))
                    minute = int(match.group(3))
                    reminder_text = match.group(4).strip()
                    
                    # PM/AM detection from suffix
                    full_match = match.group(0)
                    if 'pm' in full_match.lower():
                        if hour < 12:
                            hour += 12
                    elif 'am' in full_match.lower():
                        if hour == 12:
                            hour = 0
                    
                    # Validate hour
                    if hour >= 24:
                        hour = hour % 24
                    
                    tomorrow = datetime.now() + timedelta(days=1)
                    target_dt = tomorrow.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    
                    return {
                        "success": True,
                        "datetime": target_dt,
                        "reminder_text": reminder_text,
                        "parsed_as": f"⚡ Regex: kal {hour}:{minute:02d}"
                    }
                
                elif pattern_type == 'tomorrow_time':
                    hour = int(match.group(2))
                    time_suffix = match.group(3)
                    reminder_text = match.group(4).strip()
                    
                    # PM/AM detection
                    if time_suffix and ('pm' in time_suffix.lower() or 'baje' in time_suffix.lower()):
                        if hour < 12:
                            hour += 12
                    elif time_suffix and 'am' in time_suffix.lower():
                        if hour == 12:
                            hour = 0
                    
                    # Validate
                    if hour >= 24:
                        hour = hour % 24
                    
                    tomorrow = datetime.now() + timedelta(days=1)
                    target_dt = tomorrow.replace(hour=hour, minute=0, second=0, microsecond=0)
                    
                    return {
                        "success": True,
                        "datetime": target_dt,
                        "reminder_text": reminder_text,
                        "parsed_as": f"⚡ Regex: kal {hour}:00"
                    }
                
                elif pattern_type == 'today_night_time':
                    hour = int(match.group(2))
                    time_suffix = match.group(3)
                    reminder_text = match.group(4).strip()
                    
                    # Night = PM
                    if hour < 12:
                        hour += 12
                    
                    if hour >= 24:
                        hour = 23
                    
                    target_dt = datetime.now().replace(hour=hour, minute=0, second=0, microsecond=0)
                    
                    if target_dt <= datetime.now():
                        return {
                            "success": False,
                            "error": "Ye time aaj already nikal gaya hai"
                        }
                    
                    return {
                        "success": True,
                        "datetime": target_dt,
                        "reminder_text": reminder_text,
                        "parsed_as": f"⚡ Regex: aaj raat {hour}:00"
                    }
                
                elif pattern_type == 'today_time':
                    hour = int(match.group(2))
                    time_suffix = match.group(3)
                    reminder_text = match.group(4).strip()
                    
                    if time_suffix and ('pm' in time_suffix.lower() or 'baje' in time_suffix.lower()):
                        if hour < 12:
                            hour += 12
                    
                    if hour >= 24:
                        hour = hour % 24
                    
                    target_dt = datetime.now().replace(hour=hour, minute=0, second=0, microsecond=0)
                    
                    if target_dt <= datetime.now():
                        return {
                            "success": False,
                            "error": "Ye time aaj already nikal gaya hai"
                        }
                    
                    return {
                        "success": True,
                        "datetime": target_dt,
                        "reminder_text": reminder_text,
                        "parsed_as": f"⚡ Regex: aaj {hour}:00"
                    }
                
                elif pattern_type == 'exact_time_today':
                    hour = int(match.group(1))
                    minute = int(match.group(2))
                    reminder_text = match.group(3).strip()
                    
                    # Validate
                    if hour >= 24:
                        hour = hour % 24
                    
                    target_dt = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
                    
                    if target_dt <= datetime.now():
                        return {
                            "success": False,
                            "error": "Ye time already nikal gaya hai"
                        }
                    
                    return {
                        "success": True,
                        "datetime": target_dt,
                        "reminder_text": reminder_text,
                        "parsed_as": f"⚡ Regex: aaj {hour}:{minute:02d}"
                    }
                
                elif pattern_type == 'time_today':
                    hour = int(match.group(1))
                    time_suffix = match.group(2).lower()
                    reminder_text = match.group(3).strip()
                    
                    if 'pm' in time_suffix:
                        if hour < 12:
                            hour += 12
                        elif hour >= 12:
                            hour = hour % 12 + 12
                    elif 'am' in time_suffix:
                        if hour == 12:
                            hour = 0
                    
                    # Validate
                    if hour >= 24:
                        hour = 23
                    
                    target_dt = datetime.now().replace(hour=hour, minute=0, second=0, microsecond=0)
                    
                    if target_dt <= datetime.now():
                        return {
                            "success": False,
                            "error": "Ye time already nikal gaya hai"
                        }
                    
                    return {
                        "success": True,
                        "datetime": target_dt,
                        "reminder_text": reminder_text,
                        "parsed_as": f"⚡ Regex: aaj {hour}:00"
                    }
            
            except (ValueError, IndexError) as e:
                logger.error(f"Regex parse error in {pattern_type}: {e}")
                continue  # Try next pattern
    
    # ========== STEP 2: Try dateparser library ==========
    
    logger.info("🔍 Trying dateparser library...")
    
    words = processed_text.split()
    
    for i in range(min(10, len(words)), 0, -1):
        date_part = ' '.join(words[:i])
        potential_text = ' '.join(words[i:]).strip()
        
        parsed_date = dateparser.parse(
            date_part,
            settings={
                'PREFER_DATES_FROM': 'future',
                'TIMEZONE': 'Asia/Kolkata',
                'RETURN_AS_TIMEZONE_AWARE': False,
            },
            languages=['en', 'hi']
        )
        
        if parsed_date and parsed_date > datetime.now():
            logger.info(f"✅ dateparser success: {date_part} -> {parsed_date}")
            
            if not potential_text or len(potential_text) < 3:
                potential_text = text
            
            return {
                "success": True,
                "datetime": parsed_date,
                "reminder_text": potential_text,
                "parsed_as": f"📚 dateparser: {parsed_date.strftime('%Y-%m-%d %H:%M')}"
            }
    
    # ========== STEP 3: Fallback to Gemini AI ==========
    
    logger.info("🤖 Trying Gemini AI as final fallback...")
    
    try:
        from utils.gemini_parser import parse_with_gemini, is_gemini_available
        
        if is_gemini_available():
            gemini_result = parse_with_gemini(text)
            if gemini_result["success"]:
                logger.info("✅ Gemini AI successfully parsed")
                return gemini_result
            else:
                logger.warning(f"Gemini failed: {gemini_result.get('error')}")
        else:
            logger.warning("Gemini not available")
    except ImportError:
        logger.warning("Gemini module not found")
    except Exception as e:
        logger.error(f"Gemini error: {e}")
    
    # ========== All methods failed ==========
    
    return {
        "success": False,
        "error": "Date/time samajh nahi aaya. 😕\n\n"
                 "Clear mention karo jaise:\n"
                 "• 10 min baad meeting\n"
                 "• kal shaam 5 baje gym\n"
                 "• tomorrow 11:50 pm call\n"
                 "• 2 hours baad khaana\n\n"
                 "Ya /remindstep se step-by-step set karo"
    }
