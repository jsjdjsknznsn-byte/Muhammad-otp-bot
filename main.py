import os, json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# --- سیٹنگ ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = 8261066811

DATA_FILE = "users_data.json"

# --- ہر سروس کی قیمت ---
SERVICE_PRICE = {
    "tiktok": 0.8,
    "facebook": 1.0,
    "whatsapp": 1.0,
    "telegram": 1.0,
    "bybit": 1.0,
    "apple": 1.5
}

# --- ڈیٹا محفوظ کرنے کے فنکشن ---
def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r") as f:
        try:
            return json.load(f)
        except:
            return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def get_numbers(service):
    try:
        with open(f"{service}.txt", "r") as f:
            nums = [l.strip() for l in f if l.strip()]
            return nums
    except:
        return []

# --- /start کمانڈ ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📱 ALL NUMBERS", callback_data='all_services')],
        [InlineKeyboardButton("📥 OTP CHECK", callback_data='check_otp')]
    ]
    await update.message.reply_text(
        f"🔥 *Welcome {update.effective_user.first_name}*\n\nبوٹ تیار ہے، نیچے سے سروس منتخب کریں۔",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# --- سارے بٹنوں کا کنٹرول ---
async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data

    # 1. جب ALL NUMBERS پر کلک کرے
    if data == 'all_services':
        keyboard = [
            [InlineKeyboardButton(f"🎵 TikTok - Rs {SERVICE_PRICE['tiktok']}", callback_data='service_tiktok')],
            [InlineKeyboardButton(f"📘 Facebook - Rs {SERVICE_PRICE['facebook']}", callback_data='service_facebook')],
            [InlineKeyboardButton(f"💚 WhatsApp - Rs {SERVICE_PRICE['whatsapp']}", callback_data='service_whatsapp')],
            [InlineKeyboardButton(f"✈️ Telegram - Rs {SERVICE_PRICE['telegram']}", callback_data='service_telegram')],
            [InlineKeyboardButton(f"💰 Bybit - Rs {SERVICE_PRICE['bybit']}", callback_data='service_bybit')],
            [InlineKeyboardButton(f"🍎 Apple - Rs {SERVICE_PRICE['apple']}", callback_data='service_apple')],
        ]
        await q.message.reply_text("👇 سروس منتخب کریں:", reply_markup=InlineKeyboardMarkup(keyboard))

    # 2. جب کسی سروس پر کلک کرے تو اس کے نمبر دکھاؤ
    elif data.startswith('service_'):
        service = data.replace('service_', '', 1)
        numbers = get_numbers(service)
        price = SERVICE_PRICE.get(service, 1.0)

        if not numbers:
            await q.message.reply_text(f"❌ `{service}.txt` فائل خالی ہے، اس میں نمبر ڈالو۔", parse_mode='Markdown')
            return

        buttons = []
        for num in numbers[:30]: # پہلے 30 نمبر دکھائے گا
            buttons.append([InlineKeyboardButton(f"{num} | Rs {price}", callback_data=f"getnum_{service}_{num}")])

        await q.message.reply_text(
            f"✅ *{service.upper()}* کے {len(numbers)} نمبر موجود ہیں، کوئی ایک منتخب کرو:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    # 3. جب نمبر پر کلک کرے - یہ سب سے اہم حصہ ہے
    elif data.startswith('getnum_'):
        _, service, number = data.split('_', 2)
        price = SERVICE_PRICE.get(service, 1.0)

        # یوزر کا حساب سیو کرو
        db = load_data()
        uid = str(q.from_user.id)
        if uid not in db:
            db[uid] = {
                "name": q.from_user.first_name,
                "username": f"@{q.from_user.username}" if q.from_user.username else "No username",
                "count": 0,
                "total_bill": 0.0
            }

        db[uid]["count"] += 1
        db[uid]["total_bill"] = round(db[uid]["total_bill"] + price, 2)
        save_data(db)

        await q.message.reply_text(
            f"✅ *نمبر مل گیا:*\n\n`{number}`\n\nسروس: {service.upper()}\nقیمت: Rs {price}\n\nآپ کا کل حساب: {db[uid]['count']} OTP | Rs {db[uid]['total_bill']}",
            parse_mode='Markdown'
        )

    elif data == 'check_otp':
        await q.message.reply_text("📥 جس نمبر کا OTP چاہیے وہ نمبر بھیجیں، میں چیک کر لوں گا۔")

# --- /stats صرف آپ کے لیے ---
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!= ADMIN_ID:
        await update.message.reply_text("❌ آپ ایڈمن نہیں ہو۔")
        return

    db = load_data()
    if not db:
        await update.message.reply_text("ابھی کسی نے کوئی نمبر نہیں لیا۔")
        return

    msg = "📊 *کلائنٹس کا حساب*\n\n"
    for uid, info in db.items():
        msg += f"👤 {info['name']} {info['username']}\nOTP: {info['count']} | Bill: Rs {info['total_bill']}\nID: `{uid}`\n\n"

    await update.message.reply_text(msg, parse_mode='Markdown')

# --- بوٹ چلانا ---
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CallbackQueryHandler(handle_buttons))
    print("BOT IS LIVE...")
    app.run_polling()

if __name__ == "__main__":
    main()