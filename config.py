import os

# 🤖 Main Bot Token (Single Source of Truth)
BOT_TOKEN = "main bot token here "

# 🤖 Group Forwarding Bots (Load Balancers)
BOT_TOKEN_2 = "forward bot token here"
BOT_TOKEN_3 = "otp frowardbot token here "

# 👑 Admin & Control Credentials 
PRIMARY_ADMIN_ID = your admin id

# 📊 Channels & Groups (Force Join System)
OTP_GROUP_ID = -1003886680181
UPDATE_CHANNEL_LINK = "https://t.me/botxupdat"
OTP_GROUP_LINK = "https://t.me/ivasmsrangev3"
EXTRA_LINK_1 = "https://t.me/+xz0sqMIvL95kMGJl"  
EXTRA_LINK_2 = "https://t.me/+_MQpQfQQnNJmZmU1"  
BOT_LINK = "https://www.youtube.com/@NAGITMV"

# 💾 Absolute Database Engine Storage Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")

# 🎭 Premium Custom Interface Core Layout Matrix Configurations
BTN_EMOJIS = {
    "default_btn": "🟩",
    "wallet_btn": "🟦",
    "stats_btn": "🟦",
    "top_btn": "🟥",
    "support_btn": "🟥",
    "admin_btn": "🟪"
}

TEXT_EMOJIS = {
    "sms_number": "5465239105404559569",
    "language": "5465220456673329434"
}

def format_p_emo(custom_id: str, fallback: str) -> str:
    return f"<tg-emoji emoji-id='{custom_id}'>{fallback}</tg-emoji>"

def to_bold_font(text: str) -> str:
    return f"<b>{text}</b>"

# Global System Animated Prefix
SYS_EMOJI = "<tg-emoji emoji-id='5346066456142429527'>🚀</tg-emoji>"