import os, json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = 8261066811
DATA_FILE = "users_data.json"

SERVICE_PRICE = {
    "tiktok": 0.8, "facebook": 1.0, "whatsapp": 1.0,
    "telegram": 1.0, "bybit": 1.0, "apple": 1.5, "paypal": 1.0
}

def load_data():
    if not os.path.exists(DATA_FILE): return {}
    with open(DATA_FILE, "r") as f:
        try: return json.load(f)
        except: return {}

def save_data(data):
    with open(DATA_FILE, "w") as f: json.dump(data, f, indent=2)

def get_numbers(service):
    file_name = f"{service}.txt"
    if not os.path.exists(file_name): return []
    with open(file_name, "r", encoding="utf-8") as f:
        nums = []
        for line in f:
            n = line.strip().replace(",", "").replace(" ", "")
            if n and len(n) > 5:
                nums.append(n)
        return nums

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("📱 ALL NUMBERS", callback_data='all_services')]]
    await update.message.reply_text(f"🔥 Bot Ready {update.effective_user.first_name}\nALL NUMBERS دباؤ", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data

    if data == 'all_services':
        keyboard = [
            [InlineKeyboardButton("💚 WhatsApp", callback_data='service_whatsapp'), InlineKeyboardButton("🎵 TikTok", callback_data='service_tiktok')],
            [InlineKeyboardButton("📘 Facebook", callback_data='service_facebook'), InlineKeyboardButton("✈️ Telegram", callback_data='service_telegram')],
            [InlineKeyboardButton("💰 Bybit", callback_data='service_bybit'), InlineKeyboardButton("🍎 Apple", callback_data='service_apple')],
            [InlineKeyboardButton("💵 PayPal", callback_data='service_paypal')],
        ]
        await q.message.reply_text("👇 سروس منتخب کریں:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith('service_'):
        service = data.replace('service_', '', 1)
        numbers = get_numbers(service)
        if not numbers:
            await q.message.reply_text(f"❌ `{service}.txt` میں کوئی نمبر نہیں ملا یا فائل خالی ہے۔ ہر نمبر الگ لائن میں لکھو۔", parse_mode='Markdown')
            return
        buttons = []
        for num in numbers[:40]:
            buttons.append([InlineKeyboardButton(f"{num}", callback_data=f"getnum_{service}_{num}")])
        await q.message.reply_text(f"✅ *{service.upper()}* میں {len(numbers)} نمبر ملے، ایک پر کلک کرو:", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(buttons))

    elif data.startswith('getnum_'):
        _, service, number = data.split('_', 2)
        db = load_data()
        uid = str(q.from_user.id)
        if uid not in db:
            db[uid] = {"name": q.from_user.first_name, "username": f"@{q.from_user.username}" if q.from_user.username else "", "count": 0, "total_bill": 0.0}
        db[uid]["count"] += 1
        db[uid]["total_bill"] = round(db[uid]["total_bill"] + SERVICE_PRICE.get(service, 1.0), 2)
        save_data(db)
        await q.message.reply_text(f"✅ *نمبر:* `{number}`\nسروس: {service.upper()}\n\nآپ کا حساب /stats میں دیکھو", parse_mode='Markdown')

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!= ADMIN_ID: return
    db = load_data()
    if not db:
        await update.message.reply_text("کوئی ڈیٹا نہیں")
        return
    msg = "📊 حساب\n\n"
    for uid, info in db.items():
        msg += f"👤 {info['name']} {info['username']}\nOTP: {info['count']} | Rs {info['total_bill']}\nID: `{uid}`\n\n"
    await update.message.reply_text(msg, parse_mode='Markdown')

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CallbackQueryHandler(handle_buttons))
    print("BOT LIVE")
    app.run_polling()

if __name__ == "__main__":
    main()