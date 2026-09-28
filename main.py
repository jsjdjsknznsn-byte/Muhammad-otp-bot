import os
import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# ----------------------------------------------------
# 1. Configuration (اپنا ٹوکن اور API Keys یہاں درج کریں)
# ----------------------------------------------------
BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN_HERE"  # BotFather سے حاصل کردہ ٹوکن

PANELS = {
    "panel_1": {
        "url": "https://panel1-domain.com/api/v2",
        "api_key": "YOUR_PANEL_1_API_KEY"
    },
    "panel_2": {
        "url": "https://panel2-domain.com/api/v2",
        "api_key": "YOUR_PANEL_2_API_KEY"
    },
    "panel_3": {
        "url": "https://panel3-domain.com/api/v2",
        "api_key": "YOUR_PANEL_3_API_KEY"
    }
}

# ----------------------------------------------------
# 2. Text فائلز سے نمبر پڑھنے اور ہٹانے کا فنکشن
# ----------------------------------------------------
def get_and_remove_number(filename):
    if not os.path.exists(filename):
        return f"فائل `{filename}` موجود نہیں ہے۔"
    
    with open(filename, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]
    
    if not lines:
        return f"فائل `{filename}` میں فی الحال کوئی نمبر موجود نہیں ہے۔"
    
    # پہلا نمبر اٹھائیں
    selected_number = lines[0]
    
    # باقی تمام نمبرز واپس فائل میں لکھ دیں
    remaining_numbers = lines[1:]
    with open(filename, 'w', encoding='utf-8') as f:
        for num in remaining_numbers:
            f.write(num + "\n")
            
    return selected_number

# ----------------------------------------------------
# 3. Start Command Handler (بٹنز کا مینو)
# ----------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("WhatsApp 🟢", callback_data="get_whatsapp"),
            InlineKeyboardButton("Facebook 🔵", callback_data="get_facebook")
        ],
        [
            InlineKeyboardButton("TikTok 🎵", callback_data="get_tiktok"),
            InlineKeyboardButton("Bybit 🟡", callback_data="get_bybit")
        ],
        [
            InlineKeyboardButton("PayPal 💳", callback_data="get_paypal"),
            InlineKeyboardButton("Apple 🍏", callback_data="get_apple")
        ],
        [
            InlineKeyboardButton("Telegram ✈️", callback_data="get_telegram")
        ],
        [
            InlineKeyboardButton("پینل بیلنس (Panel Balance)", callback_data="check_balance")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "خوش آمدید! آپ کو جس سروس کا نمبر چاہیے، نیچے دیے گئے بٹن پر کلک کریں:",
        reply_markup=reply_markup
    )

# ----------------------------------------------------
# 4. Callback Query Handler (بٹن دبانے کا جواب)
# ----------------------------------------------------
async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    if data.startswith("get_"):
        service = data.replace("get_", "")
        # ٹیکسٹ فائل کا نام (مثلاً whatsapp.txt)
        file_name = f"{service}.txt"
        
        # فائل سے نمبر حاصل کریں
        number = get_and_remove_number(file_name)
        
        message_text = f"📱 **سروس:** {service.upper()}\n📞 **نمبر:** `{number}`\n\nکوڈ کا انتظار ہے..."
        
        # دوبارہ سروسز پر جانے کے لیے بٹن
        back_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("واپس مینو (Back)", callback_data="main_menu")]
        ])
        
        await query.edit_message_text(text=message_text, parse_mode="Markdown", reply_markup=back_keyboard)

    elif data == "check_balance":
        balance_info = "📊 **پینل بیلنس کی معلومات:**\n\n"
        for panel_name, panel_info in PANELS.items():
            try:
                response = requests.post(panel_info["url"], data={
                    "key": panel_info["api_key"],
                    "action": "balance"
                }, timeout=5)
                res_data = response.json()
                bal = res_data.get("balance", "N/A")
                currency = res_data.get("currency", "USD")
                balance_info += f"• {panel_name.upper()}: {bal} {currency}\n"
            except Exception:
                balance_info += f"• {panel_name.upper()}: API Connect Error\n"

        back_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("واپس مینو (Back)", callback_data="main_menu")]
        ])
        await query.edit_message_text(text=balance_info, parse_mode="Markdown", reply_markup=back_keyboard)

    elif data == "main_menu":
        # دوبارہ شروعاتی مینو دکھانے کے لیے
        keyboard = [
            [
                InlineKeyboardButton("WhatsApp 🟢", callback_data="get_whatsapp"),
                InlineKeyboardButton("Facebook 🔵", callback_data="get_facebook")
            ],
            [
                InlineKeyboardButton("TikTok 🎵", callback_data="get_tiktok"),
                InlineKeyboardButton("Bybit 🟡", callback_data="get_bybit")
            ],
            [
                InlineKeyboardButton("PayPal 💳", callback_data="get_paypal"),
                InlineKeyboardButton("Apple 🍏", callback_data="get_apple")
            ],
            [
                InlineKeyboardButton("Telegram ✈️", callback_data="get_telegram")
            ],
            [
                InlineKeyboardButton("پینل بیلنس (Panel Balance)", callback_data="check_balance")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("خوش آمدید! آپ کو جس سروس کا نمبر چاہیے، نیچے دیے گئے بٹن پر کلک کریں:", reply_markup=reply_markup)

# ----------------------------------------------------
# 5. Main Execution
# ----------------------------------------------------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_click))

    print("Bot is running successfully...")
    app.run_polling()

if __name__ == '__main__':
    main()
