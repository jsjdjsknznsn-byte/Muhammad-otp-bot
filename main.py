import os, json, httpx
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = 8261066811
CHANNEL_ID = "-1003910116001"
DATA_FILE = "users_data.json"

TELEROUTEX_KEY = "1fxJ2pBqJ8NaFVwREgHLfK6URJ1BT0DUevqc2BDhIm8="
UNIX_KEY = "simple_v2_9jjdFOVK2uqotCnKNmbKQ2R3buR_vQJFFy2IkVKb1r61Ufx7"
LAMIX_KEY = "OqQS-cGgcrHAEzfx3Iihn6nZ0SMu9XOS6EXXOANgSoc"

SERVICE_PRICE = {
    "tiktok": 0.8, "facebook": 1.0, "whatsapp": 1.0,
    "telegram": 1.0, "bybit": 1.0, "apple": 1.5,
    "payper": 1.0 # پیپر کی پرائس آپ یہاں سے بدل سکتے ہیں
}

def load_data():
    if not os.path.exists(DATA_FILE): return {}
    with open(DATA_FILE, "r") as f:
        try: return json.load(f)
        except: return {}
def save_data(data):
    with open(DATA_FILE, "w") as f: json.dump(data, f, indent=2)
def get_numbers(service):
    try:
        with open(f"{service}.txt", "r") as f:
            return [l.strip() for l in f if l.strip()]
    except: return []

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("📱 All Numbers", callback_data='all_services')], [InlineKeyboardButton("📥 OTP Check", callback_data='check_otp')]]
    await update.message.reply_text("🔥 بوٹ تیار ہے - پیپر بھی ایڈ ہے", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data

    if data == 'all_services':
        keyboard = [
            [InlineKeyboardButton(f"🎵 TikTok - Rs {SERVICE_PRICE['tiktok']}", callback_data='service_tiktok')],
            [InlineKeyboardButton(f"📘 Facebook - Rs {SERVICE_PRICE['facebook']}", callback_data='service_facebook')],
            [InlineKeyboardButton(f"💚 WhatsApp - Rs {SERVICE_PRICE['whatsapp']}", callback_data='service_whatsapp')],
            [InlineKeyboardButton(f"✈️ Telegram - Rs {SERVICE_PRICE['telegram']}", callback_data='service_telegram')],
            [InlineKeyboardButton(f"💰 Bybit - Rs {SERVICE_PRICE['bybit']}", callback_data='service_bybit')],
            [InlineKeyboardButton(f"🍎 Apple - Rs {SERVICE_PRICE['apple']}", callback_data='service_apple')],
            [InlineKeyboardButton(f"💳 Payper - Rs {SERVICE_PRICE['payper']}", callback_data='service_payper')],
        ]
        await q.message.reply_text("سروس منتخب کریں:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith('service_'):
        service = data.replace('service_', '')
        numbers = get_numbers(service)
        price = SERVICE_PRICE.get(service, 1.0)
        if not numbers:
            await q.message.reply_text(f"❌ {service}.txt خالی ہے")
            return
        buttons = [[InlineKeyboardButton(f"{num} | Rs {price}", callback_data=f"num_{service}_{num}")] for num in numbers]
        await q.message.reply_text(f"✅ {service.upper()} کے {len(numbers)} نمبر:", reply_markup=InlineKeyboardMarkup(buttons))

    elif data.startswith('num_'):
        _, service, number = data.split('_', 2)
        price = SERVICE_PRICE.get(service, 1.0)
        db = load_data()
        uid = str(q.from_user.id)
        if uid not in db:
            db[uid] = {"name": q.from_user.first_name, "username": f"@{q.from_user.username}" if q.from_user.username else "", "count": 0, "total_bill": 0.0}
        db[uid]["count"] += 1
        db[uid]["total_bill"] = round(db[uid]["total_bill"] + price, 2)
        save_data(db)
        await q.message.reply_text(f"✅ نمبر:\n\n`{number}`\n\n📌 سروس: {service.upper()}\n💰 پرائس: Rs {price}", parse_mode='Markdown')

    elif data == 'check_otp':
        try:
            async with httpx.AsyncClient() as client:
                r = await client.get(f"https://api.unixsms.com/api/otp?api_key={UNIX_KEY}", timeout=20)
                otps = r.json()
                msg = "📩 LIVE OTPs:\n\n" + "\n".join([str(x) for x in otps[:10]])
                await q.message.reply_text(msg)
                for item in otps[:3]:
                    await q.message._bot.send_message(chat_id=CHANNEL_ID, text=f"🔥 NEW OTP\n\n{item}")
        except Exception as e:
            await q.message.reply_text(f"Error: {e}")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!= ADMIN_ID: return
    db = load_data()
    msg = "📊 حساب\n\n"
    for uid, info in db.items():
        msg += f"👤 {info['name']} {info['username']}\nOTP: {info['count']} | Bill: Rs {info['total_bill']}\nID: `{uid}`\n\n"
    await update.message.reply_text(msg, parse_mode='Markdown')

app = Application.builder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("stats", stats))
app.add_handler(CallbackQueryHandler(handle_buttons))
print("BOT LIVE WITH PAYPER")
app.run_polling()