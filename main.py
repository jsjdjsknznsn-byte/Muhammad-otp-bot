import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN")

def get_numbers_from_file():
    try:
        if not os.path.exists("numbers.txt"):
            return []
        with open("numbers.txt", "r") as f:
            numbers = [line.strip() for line in f if line.strip() != ""]
        return numbers
    except:
        return []

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📱 سارے نمبر دیکھو", callback_data='show_numbers')],
        [
            InlineKeyboardButton("📘 Facebook OTP", callback_data='fb'),
            InlineKeyboardButton("💚 WhatsApp OTP", callback_data='wa')
        ],
        [InlineKeyboardButton("🎵 TikTok OTP", callback_data='tiktok')],
    ]
    await update.message.reply_text(
        "🔥 **MUHAMMAD SHAHROZ ALL OTP BOT** 🔥\n\nنیچے اپنی سروس سلیکٹ کریں 👇",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    numbers = get_numbers_from_file()
    
    if not numbers:
        await query.message.reply_text("❌ `numbers.txt` فائل خالی ہے۔ پہلے نمبر ایڈ کریں۔", parse_mode='Markdown')
        return

    msg_header = ""
    if query.data == 'show_numbers':
        msg_header = f"📱 **کل {len(numbers)} نمبر دستیاب ہیں:**\n\n"
    elif query.data == 'fb':
        msg_header = f"📘 **Facebook OTP کے لیے {len(numbers)} نمبر:**\n\n"
    elif query.data == 'wa':
        msg_header = f"💚 **WhatsApp OTP کے لیے {len(numbers)} نمبر:**\n\n"
    elif query.data == 'tiktok':
        msg_header = f"🎵 **TikTok OTP کے لیے {len(numbers)} نمبر:**\n\n"

    msg = msg_header
    for i, num in enumerate(numbers, 1):
        msg += f"{i}. `{num}`\n"
    
    await query.message.reply_text(msg, parse_mode='Markdown')

app = Application.builder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button))
print("BOT IS LIVE WITH FB WA TIKTOK BUTTONS")
app.run_polling()