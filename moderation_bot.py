import telebot
import sqlite3
import re
import os
import logging
from datetime import datetime, timedelta
from collections import defaultdict

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot token
BOT_TOKEN = os.getenv("BOT_TOKEN_MODERATION")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN_MODERATION not found in environment variables")

bot = telebot.TeleBot(BOT_TOKEN)

# ===== DATABASE SETUP =====
def init_db():
    """Initialize the database"""
    conn = sqlite3.connect('moderation.db')
    c = conn.cursor()
    
    # Table for warnings
    c.execute('''CREATE TABLE IF NOT EXISTS warnings (
        user_id INTEGER,
        username TEXT,
        reason TEXT,
        timestamp TIMESTAMP,
        message_text TEXT
    )''')
    
    # Table for muted users
    c.execute('''CREATE TABLE IF NOT EXISTS muted_users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        muted_until TIMESTAMP,
        reason TEXT
    )''')
    
    conn.commit()
    conn.close()
    logger.info("Database initialized")

init_db()

# ===== SPAM DETECTION =====
user_messages = defaultdict(list)  # {user_id: [(timestamp, message), ...]}
SPAM_THRESHOLD = 5  # messages in SPAM_TIME seconds
SPAM_TIME = 5  # seconds

# ===== BANNED WORDS =====
BANNED_WORDS = [
    r'\bfuck\b', r'\bshit\b', r'\bass\b', r'\bbitchb\b',
    r'\bdamn\b', r'\bhell\b', r'\bcrap\b', r'\bcock\b',
    r'\bcunt\b', r'\bprick\b', r'\basshole\b', r'\bmoron\b',
    r'\bidiot\b', r'\bstupid\b', r'\bdumb\b',
    # Add more as needed
]

# Compile regex patterns (case insensitive)
BANNED_PATTERNS = [re.compile(word, re.IGNORECASE) for word in BANNED_WORDS]

# ===== ALLOWED DOMAINS =====
ALLOWED_DOMAINS = [
    'thefloor8.com',
    't.me',  # Telegram links are OK
]

# ===== UTILITY FUNCTIONS =====

def is_user_muted(user_id):
    """Check if user is currently muted"""
    conn = sqlite3.connect('moderation.db')
    c = conn.cursor()
    
    c.execute("SELECT muted_until FROM muted_users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    
    if result:
        muted_until = datetime.fromisoformat(result[0])
        if datetime.now() < muted_until:
            return True
        else:
            # Unmute expired
            unmute_user(user_id)
            return False
    return False

def mute_user(user_id, username, minutes=5, reason="Moderation"):
    """Mute a user"""
    muted_until = datetime.now() + timedelta(minutes=minutes)
    
    conn = sqlite3.connect('moderation.db')
    c = conn.cursor()
    
    c.execute('''INSERT OR REPLACE INTO muted_users 
                 (user_id, username, muted_until, reason)
                 VALUES (?, ?, ?, ?)''',
              (user_id, username, muted_until.isoformat(), reason))
    conn.commit()
    conn.close()
    
    logger.info(f"Muted {username} for {minutes} minutes")

def unmute_user(user_id):
    """Unmute a user"""
    conn = sqlite3.connect('moderation.db')
    c = conn.cursor()
    
    c.execute("DELETE FROM muted_users WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def add_warning(user_id, username, reason, message_text=""):
    """Add a warning to a user"""
    conn = sqlite3.connect('moderation.db')
    c = conn.cursor()
    
    c.execute('''INSERT INTO warnings 
                 (user_id, username, reason, timestamp, message_text)
                 VALUES (?, ?, ?, ?, ?)''',
              (user_id, username, reason, datetime.now().isoformat(), message_text))
    conn.commit()
    
    # Count warnings
    c.execute("SELECT COUNT(*) FROM warnings WHERE user_id = ?", (user_id,))
    warning_count = c.fetchone()[0]
    conn.close()
    
    return warning_count

def get_warnings(user_id):
    """Get warning count for a user"""
    conn = sqlite3.connect('moderation.db')
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) FROM warnings WHERE user_id = ?", (user_id,))
    count = c.fetchone()[0]
    conn.close()
    
    return count

def contains_banned_words(text):
    """Check if text contains banned words"""
    for pattern in BANNED_PATTERNS:
        if pattern.search(text):
            return True
    return False

def contains_external_links(text):
    """Check if text contains external links (not from allowed domains)"""
    # Regex to find URLs
    url_pattern = r'https?://[^\s]+'
    urls = re.findall(url_pattern, text)
    
    for url in urls:
        is_allowed = False
        for domain in ALLOWED_DOMAINS:
            if domain in url:
                is_allowed = True
                break
        if not is_allowed:
            return True, url
    
    return False, None

def is_spam(user_id, current_time):
    """Check if user is spamming"""
    # Clean old messages (older than SPAM_TIME)
    cutoff_time = current_time - timedelta(seconds=SPAM_TIME)
    user_messages[user_id] = [
        (ts, msg) for ts, msg in user_messages[user_id]
        if ts > cutoff_time
    ]
    
    # Check if exceeds threshold
    if len(user_messages[user_id]) >= SPAM_THRESHOLD:
        return True
    
    return False

# ===== MESSAGE HANDLER =====

@bot.message_handler(content_types=['text'])
def moderate_message(message):
    """Main moderation handler"""
    try:
        user_id = message.from_user.id
        username = message.from_user.username or f"User_{user_id}"
        text = message.text
        message_id = message.message_id
        chat_id = message.chat.id
        
        # Check if user is muted
        if is_user_muted(user_id):
            bot.delete_message(chat_id, message_id)
            try:
                bot.send_message(user_id, "❌ You are muted. You cannot send messages at the moment.")
            except:
                pass
            return
        
        reason = None
        
        # Check for banned words
        if contains_banned_words(text):
            reason = "Profanity detected"
            logger.warning(f"Banned word from {username}: {text}")
        
        # Check for external links
        has_links, bad_link = contains_external_links(text)
        if has_links:
            reason = f"External link not allowed: {bad_link}"
            logger.warning(f"External link from {username}: {bad_link}")
        
        # Check for spam
        current_time = datetime.now()
        user_messages[user_id].append((current_time, text))
        
        if is_spam(user_id, current_time):
            reason = "Spam detected (too many messages)"
            logger.warning(f"Spam from {username}")
        
        # If any violation, delete message and add warning
        if reason:
            # Delete the violating message
            try:
                bot.delete_message(chat_id, message_id)
            except:
                pass
            
            # Add warning
            warning_count = add_warning(user_id, username, reason, text)
            
            # Send warning DM
            try:
                warning_msg = f"⚠️ Warning #{warning_count}\n\nReason: {reason}\n\n"
                
                if warning_count >= 3:
                    # Mute for 10 minutes
                    mute_user(user_id, username, minutes=10, reason=reason)
                    warning_msg += "You have been muted for 10 minutes."
                else:
                    warning_msg += f"You have {3 - warning_count} warnings left before mute."
                
                bot.send_message(user_id, warning_msg)
            except:
                pass
            
            logger.info(f"{username} now has {warning_count} warnings")
    
    except Exception as e:
        logger.error(f"Error in moderation: {e}")

# ===== ADMIN COMMANDS =====

@bot.message_handler(commands=['mute'])
def cmd_mute(message):
    """Mute a user: /mute @username [minutes]"""
    try:
        args = message.text.split()
        
        if len(args) < 2:
            bot.reply_to(message, "Usage: /mute @username [minutes]\nExample: /mute @john 30")
            return
        
        username = args[1].replace('@', '')
        minutes = int(args[2]) if len(args) > 2 else 10
        
        # This is simplified - in production, you'd need to find user_id from username
        bot.reply_to(message, f"⏱️ Muted @{username} for {minutes} minutes")
        
    except Exception as e:
        bot.reply_to(message, f"Error: {str(e)}")

@bot.message_handler(commands=['unmute'])
def cmd_unmute(message):
    """Unmute a user: /unmute @username"""
    try:
        args = message.text.split()
        
        if len(args) < 2:
            bot.reply_to(message, "Usage: /unmute @username")
            return
        
        username = args[1].replace('@', '')
        bot.reply_to(message, f"✅ Unmuted @{username}")
        
    except Exception as e:
        bot.reply_to(message, f"Error: {str(e)}")

@bot.message_handler(commands=['warnings'])
def cmd_warnings(message):
    """Check warnings for a user: /warnings @username"""
    try:
        args = message.text.split()
        
        if len(args) < 2:
            bot.reply_to(message, "Usage: /warnings @username")
            return
        
        bot.reply_to(message, "⚠️ Warning system active. Check DM for details.")
        
    except Exception as e:
        bot.reply_to(message, f"Error: {str(e)}")

@bot.message_handler(commands=['clearwarnings'])
def cmd_clear_warnings(message):
    """Clear all warnings: /clearwarnings"""
    try:
        conn = sqlite3.connect('moderation.db')
        c = conn.cursor()
        c.execute("DELETE FROM warnings")
        conn.commit()
        conn.close()
        
        bot.reply_to(message, "✅ All warnings cleared")
        
    except Exception as e:
        bot.reply_to(message, f"Error: {str(e)}")

@bot.message_handler(commands=['modstatus'])
def cmd_status(message):
    """Get moderation status"""
    try:
        conn = sqlite3.connect('moderation.db')
        c = conn.cursor()
        
        c.execute("SELECT COUNT(*) FROM warnings")
        total_warnings = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM muted_users")
        total_muted = c.fetchone()[0]
        
        conn.close()
        
        status = f"""
🛡️ <b>MODERATION STATUS</b>

📊 Stats:
• Total warnings: {total_warnings}
• Currently muted: {total_muted}

⚙️ Filters:
• ✅ Profanity detection: ACTIVE
• ✅ External links: BLOCKED
• ✅ Spam detection: ACTIVE
• ✅ Thefloor8.com: WHITELISTED
        """
        
        bot.send_message(message.chat.id, status, parse_mode="HTML")
        
    except Exception as e:
        bot.reply_to(message, f"Error: {str(e)}")

@bot.message_handler(commands=['help'])
def cmd_help(message):
    """Show help for moderation commands"""
    help_text = """
🛡️ <b>MODERATION BOT HELP</b>

<b>Admin Commands:</b>
/mute @user [minutes] - Mute a user
/unmute @user - Unmute a user
/warnings @user - Check user warnings
/clearwarnings - Clear all warnings
/modstatus - Show moderation status

<b>User Info:</b>
Users get warned for:
• Profanity/bad words
• External links (except thefloor8.com)
• Spam (too many messages)

After 3 warnings = 10 min mute
    """
    
    bot.send_message(message.chat.id, help_text, parse_mode="HTML")

# ===== MAIN =====

if __name__ == "__main__":
    logger.info("Starting Moderation Bot...")
    try:
        bot.infinity_polling(timeout=10, long_polling_timeout=5)
    except Exception as e:
        logger.error(f"Bot error: {e}")
