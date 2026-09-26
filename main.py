‎import re, asyncio, httpx, os
‎from flask import Flask
‎from threading import Thread
‎from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
‎from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
‎
‎# --- AAPKA BOT ---
‎BOT_TOKEN = os.environ.get("BOT_TOKEN", "8636631305:AAFY9GGoK7ym5oBpq8XdFnDj2FVDMcHXwq0")
‎PANEL = "https://unixsms.com"
‎API_KEY = os.environ.get("API_KEY", "simple_v2_9jjdFOVK2uqotCnKNmbKQ2R3buR_vQJFFy2IkVKb1r61Ufx7")
‎
‎HEADERS = {"Authorization": f"Bearer {API_KEY}", "X-API-KEY": API_KEY}
‎SEEN = set()
‎
‎app_flask = Flask('')
‎@app_flask.route('/')
‎def home(): return "Muhammad Shahroz Bot Live"
‎def run_flask(): app_flask.run(host='0.0.0.0', port=10000)
‎def keep_alive(): Thread(target=run_flask).start()
‎
‎def clean(n):
‎    n = re.sub(r'\D','',str(n))
‎    return n[1:] if n.startswith('7') and len(n)==11 else n
‎
‎def otp(t):
‎    m = re.search(r'(\d{4,8})', t)
‎    return m.group(1) if m else None
‎
‎async def get_inbox():
‎    async with httpx.AsyncClient() as c:
‎        for url in [f"{PANEL}/api/inbox", f"{PANEL}/api/sms/inbox", f"{PANEL}/api/sms/list"]:
‎            try:
‎                r = await c.get(url, headers=HEADERS, timeout=10)
‎                if r.status_code == 200:
‎                    j = r.json()
‎                    return j.get('data', j) if isinstance(j, dict) else j
‎            except: pass
‎    return []
‎
‎def board():
‎    return InlineKeyboardMarkup([
‎        [InlineKeyboardButton("👑 MUHAMMAD SHAHROZ BOT", callback_data="live")],
‎        [InlineKeyboardButton("🔴 LIVE ALL OTP", callback_data="live"), InlineKeyboardButton("📋 ALL NUMBERS", callback_data="nums")],
‎        [InlineKeyboardButton("📱 CHECK OTP", callback_data="check"), InlineKeyboardButton("💰 BALANCE", callback_data="bal")],
‎        [InlineKeyboardButton("📞 CONTACT OWNER", url="https://t.me/MuhammadShahrozbot")]
‎    ])
‎
‎async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
‎    await update.message.reply_text(
‎        "👑 **MUHAMMAD SHAHROZ ALL OTP BOT**\n\n"
‎        "⚡️ 24/7 Online - Mobile band bhi ho to chalega\n"
‎        "🔰 Bot: @MuhammadShahrozbot\n\n"
‎        "Neeche button pe click karo:", 
‎        reply_markup=board(), parse_mode="Markdown")
‎
‎async def cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
‎    q = update.callback_query
‎    await q.answer()
‎    if q.data == "live":
‎        inbox = await get_inbox()
‎        if not inbox:
‎            await q.edit_message_text("❌ Abhi koi OTP nahi aaya, 5 sec baad try karo.", reply_markup=board())
‎            return
‎        msg = "🔴 **MUHAMMAD SHAHROZ - LIVE OTPs**\n\n"
‎        for s in inbox[-10:][::-1]:
‎            num = s.get('number') or s.get('to') or ''
‎            txt = s.get('text') or s.get('message') or ''
‎            code = otp(txt) or "No Code"
‎            msg += f"📱 +{num} | Clean: {clean(num)}\n🔑 OTP: {code}\n\n"
‎        await q.edit_message_text(msg[:4000], reply_markup=board())
‎
‎async def poller(app): 
‎    while True:
‎        await asyncio.sleep(5)
‎
‎async def post_init(app): asyncio.create_task(poller(app))
‎
‎def main():
‎    keep_alive()
‎    application = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
‎    application.add_handler(CommandHandler("start", start))
‎    application.add_handler(CallbackQueryHandler(cb))
‎    application.run_polling()
‎
‎if __name__ == "__main__":
‎    main()
‎
