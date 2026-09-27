
import os
import sqlite3
import secrets
import time
import logging
from functools import wraps
from dotenv import load_dotenv

BOT_TOKEN="8636631305:AAFY9GGoK7ym5oBpq8XdFnDj2FVDMcHXwq0"
ADMIN_ID="8261066811"


from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# ---------------- CONFIG ----------------

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

DB = "bot.db"

SERVICES = [
    "Facebook",
    "WhatsApp",
    "Telegram",
    "Instagram",
    "TikTok",
]

# Demo price in internal credits (not real currency)
TEST_PRICE = 5

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
log = logging.getLogger(__name__)


# ---------------- DATABASE ----------------

def db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with db() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                balance REAL DEFAULT 0,
                created_at INTEGER
            )
        """)

        con.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount REAL,
                status TEXT DEFAULT 'pending',
                created_at INTEGER
            )
        """)

        con.execute("""
            CREATE TABLE IF NOT EXISTS test_otps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                service TEXT,
                otp_hash TEXT,
                expires_at INTEGER,
                used INTEGER DEFAULT 0
            )
        """)

        con.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount REAL,
                reason TEXT,
                created_at INTEGER
            )
        """)


def register_user(user):
    with db() as con:
        con.execute("""
            INSERT OR IGNORE INTO users
            (user_id, username, balance, created_at)
            VALUES (?, ?, 0, ?)
        """, (
            user.id,
            user.username or "",
            int(time.time()),
        ))

        con.execute("""
            UPDATE users SET username=?
            WHERE user_id=?
        """, (user.username or "", user.id))


def get_balance(user_id):
    with db() as con:
        row = con.execute(
            "SELECT balance FROM users WHERE user_id=?",
            (user_id,),
        ).fetchone()

    return float(row["balance"]) if row else 0.0


def add_balance(user_id, amount, reason):
    with db() as con:
        con.execute(
            "UPDATE users SET balance=balance+? WHERE user_id=?",
            (amount, user_id),
        )

        con.execute("""
            INSERT INTO transactions
            (user_id, amount, reason, created_at)
            VALUES (?, ?, ?, ?)
        """, (
            user_id,
            amount,
            reason,
            int(time.time()),
        ))


def deduct_balance(user_id, amount, reason):
    with db() as con:
        cur = con.execute("""
            UPDATE users
            SET balance=balance-?
            WHERE user_id=? AND balance>=?
        """, (amount, user_id, amount))

        if cur.rowcount == 0:
            return False

        con.execute("""
            INSERT INTO transactions
            (user_id, amount, reason, created_at)
            VALUES (?, ?, ?, ?)
        """, (
            user_id,
            -amount,
            reason,
            int(time.time()),
        ))

    return True


def is_admin(user_id):
    return user_id == ADMIN_ID


# ---------------- KEYBOARDS ----------------

def main_menu(user_id):
    rows = [
        [InlineKeyboardButton(
            "📱 Services",
            callback_data="services"
        )],
        [
            InlineKeyboardButton(
                "💰 My Balance",
                callback_data="balance"
            ),
            InlineKeyboardButton(
                "💳 Add Funds",
                callback_data="addfunds"
            ),
        ],
        [InlineKeyboardButton(
            "🧪 Test OTP",
            callback_data="testotp"
        )],
    ]

    if is_admin(user_id):
        rows.append([
            InlineKeyboardButton(
                "🛠 Admin Panel",
                callback_data="admin"
            )
        ])

    return InlineKeyboardMarkup(rows)


def services_menu():
    rows = []

    for service in SERVICES:
        rows.append([
            InlineKeyboardButton(
                service,
                callback_data=f"service:{service}"
            )
        ])

    rows.append([
        InlineKeyboardButton(
            "⬅️ Back",
            callback_data="home"
        )
    ])

    return InlineKeyboardMarkup(rows)


# ---------------- START ----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    register_user(user)

    await update.message.reply_text(
        f"Assalam-o-Alaikum {user.first_name}!\n\n"
        "Welcome to your service demo bot.\n\n"
        "Select an option below:",
        reply_markup=main_menu(user.id),
    )


async def balance_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    register_user(user)

    await update.message.reply_text(
        f"Your balance: {get_balance(user.id):.2f} credits"
    )


# ---------------- TEST OTP ----------------

async def issue_test_otp(user_id, service):
    """
    This is a local simulation only.
    It does not contact any social media platform.
    The demo OTP is never sent to a phone number.
    """
    code = str(secrets.randbelow(900000) + 100000)

    # Store only a hash of the demo code.
    import hashlib
    code_hash = hashlib.sha256(code.encode()).hexdigest()

    with db() as con:
        con.execute("""
            INSERT INTO test_otps
            (user_id, service, otp_hash, expires_at, used)
            VALUES (?, ?, ?, ?, 0)
        """, (
            user_id,
            service,
            code_hash,
            int(time.time()) + 300,
        ))

    # Return for display in this private demo session only.
    return code


async def testotp_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    register_user(user)

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                service,
                callback_data=f"demo:{service}"
            )
        ]
        for service in SERVICES
    ])

    await update.message.reply_text(
        "Choose a service for a simulated test OTP.\n"
        "No real account or phone number is contacted.",
        reply_markup=keyboard,
    )


# ---------------- PAYMENTS ----------------

async def addfunds_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    register_user(user)

    await update.message.reply_text(
        "To request a balance top-up, send:\n\n"
        "/pay 100\n\n"
        "Example: /pay 100\n"
        "This creates a pending request for admin review.\n"
        "It does not process a real payment."
    )


async def pay_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    register_user(user)

    if not context.args:
        await update.message.reply_text(
            "Usage: /pay 100"
        )
        return

    try:
        amount = float(context.args[0])
        if amount <= 0 or amount > 100000:
            raise ValueError
    except ValueError:
        await update.message.reply_text(
            "Enter a valid amount greater than 0."
        )
        return

    with db() as con:
        cur = con.execute("""
            INSERT INTO payments
            (user_id, amount, status, created_at)
            VALUES (?, ?, 'pending', ?)
        """, (user.id, amount, int(time.time())))

        payment_id = cur.lastrowid

    await update.message.reply_text(
        f"Payment request #{payment_id} created.\n"
        f"Amount: {amount:.2f}\n"
        "Status: Pending admin review."
    )

    if ADMIN_ID:
        try:
            await context.bot.send_message(
                ADMIN_ID,
                f"New top-up request #{payment_id}\n"
                f"User: {user.id}\n"
                f"Amount: {amount:.2f}\n\n"
                f"Approve: /approve {payment_id}\n"
                f"Reject: /reject {payment_id}"
            )
        except Exception:
            log.exception("Could not notify admin")


# ---------------- ADMIN ----------------

def admin_only(func):
    @wraps(func)
    async def wrapper(update, context):
        user = update.effective_user

        if not user or not is_admin(user.id):
            if update.callback_query:
                await update.callback_query.answer(
                    "Admin only.",
                    show_alert=True,
                )
            elif update.message:
                await update.message.reply_text(
                    "You are not authorized."
                )
            return

        return await func(update, context)

    return wrapper


@admin_only
async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Admin commands:\n\n"
        "/stats - Bot statistics\n"
        "/users - Recent users\n"
        "/credit USER_ID AMOUNT - Add credits\n"
        "/debit USER_ID AMOUNT - Remove credits\n"
        "/approve PAYMENT_ID - Approve top-up\n"
        "/reject PAYMENT_ID - Reject top-up"
    )


@admin_only
async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with db() as con:
        users = con.execute(
            "SELECT COUNT(*) AS n FROM users"
        ).fetchone()["n"]

        pending = con.execute(
            "SELECT COUNT(*) AS n FROM payments WHERE status='pending'"
        ).fetchone()["n"]

        total = con.execute(
            "SELECT COALESCE(SUM(balance),0) AS n FROM users"
        ).fetchone()["n"]

    await update.message.reply_text(
        f"Users: {users}\n"
        f"Pending payments: {pending}\n"
        f"Total user credits: {total:.2f}"
    )


@admin_only
async def users_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with db() as con:
        rows = con.execute("""
            SELECT user_id, username, balance
            FROM users ORDER BY created_at DESC LIMIT 30
        """).fetchall()

    if not rows:
        await update.message.reply_text("No users yet.")
        return

    lines = ["Recent users:"]

    for row in rows:
        lines.append(
            f"{row['user_id']} | @{row['username']} | "
            f"{row['balance']:.2f}"
        )

    await update.message.reply_text("\n".join(lines))


@admin_only
async def credit_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 2:
        await update.message.reply_text(
            "Usage: /credit USER_ID AMOUNT"
        )
        return

    try:
        uid = int(context.args[0])
        amount = float(context.args[1])

        if amount <= 0 or amount > 100000:
            raise ValueError
    except ValueError:
        await update.message.reply_text("Invalid user ID or amount.")
        return

    with db() as con:
        exists = con.execute(
            "SELECT user_id FROM users WHERE user_id=?",
            (uid,),
        ).fetchone()

    if not exists:
        await update.message.reply_text(
            "User not found. They must first send /start."
        )
        return

    add_balance(uid, amount, "Admin credit")

    await update.message.reply_text(
        f"Added {amount:.2f} credits to {uid}."
    )

    try:
        await context.bot.send_message(
            uid,
            f"Admin added {amount:.2f} credits to your balance."
        )
    except Exception:
        pass


@admin_only
async def debit_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 2:
        await update.message.reply_text(
            "Usage: /debit USER_ID AMOUNT"
        )
        return

    try:
        uid = int(context.args[0])
        amount = float(context.args[1])

        if amount <= 0 or amount > 100000:
            raise ValueError
    except ValueError:
        await update.message.reply_text("Invalid user ID or amount.")
        return

    if not deduct_balance(uid, amount, "Admin debit"):
        await update.message.reply_text(
            "User not found or insufficient balance."
        )
        return

    await update.message.reply_text(
        f"Removed {amount:.2f} credits from {uid}."
    )


@admin_only
async def approve_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.message.reply_text(
            "Usage: /approve PAYMENT_ID"
        )
        return

    try:
        payment_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Invalid payment ID.")
        return

    with db() as con:
        payment = con.execute("""
            SELECT * FROM payments
            WHERE id=? AND status='pending'
        """, (payment_id,)).fetchone()

        if not payment:
            await update.message.reply_text(
                "Payment not found or already processed."
            )
            return

        con.execute(
            "UPDATE payments SET status='approved' WHERE id=?",
            (payment_id,),
        )

    add_balance(
        payment["user_id"],
        payment["amount"],
        f"Approved payment #{payment_id}",
    )

    await update.message.reply_text(
        f"Payment #{payment_id} approved."
    )

    try:
        await context.bot.send_message(
            payment["user_id"],
            f"Your payment request #{payment_id} was approved.\n"
            f"Credits added: {payment['amount']:.2f}\n"
            f"Balance: {get_balance(payment['user_id']):.2f}"
        )
    except Exception:
        pass


@admin_only
async def reject_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.message.reply_text(
            "Usage: /reject PAYMENT_ID"
        )
        return

    try:
        payment_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Invalid payment ID.")
        return

    with db() as con:
        cur = con.execute("""
            UPDATE payments
            SET status='rejected'
            WHERE id=? AND status='pending'
        """, (payment_id,))

        if cur.rowcount == 0:
            await update.message.reply_text(
                "Payment not found or already processed."
            )
            return

        payment = con.execute(
            "SELECT user_id FROM payments WHERE id=?",
            (payment_id,),
        ).fetchone()

    await update.message.reply_text(
        f"Payment #{payment_id} rejected."
    )

    try:
        await context.bot.send_message(
            payment["user_id"],
            f"Your payment request #{payment_id} was rejected."
        )
    except Exception:
        pass


# ---------------- BUTTON HANDLER ----------------

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = query.from_user
    register_user(user)

    data = query.data

    if data == "home":
        await query.edit_message_text(
            "Main menu:",
            reply_markup=main_menu(user.id),
        )

    elif data == "services":
        await query.edit_message_text(
            "Select a service:",
            reply_markup=services_menu(),
        )

    elif data == "balance":
        await query.edit_message_text(
            f"Your balance: {get_balance(user.id):.2f} credits",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Back", callback_data="home")
            ]]),
        )

    elif data == "addfunds":
        await query.edit_message_text(
            "Request a demo top-up using:\n"
            "/pay 100\n\n"
            "Admin approval is required. No real payment is taken.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Back", callback_data="home")
            ]]),
        )

    elif data == "testotp":
        await query.edit_message_text(
            "Choose a service for a simulated OTP:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    s, callback_data=f"demo:{s}"
                )]
                for s in SERVICES
            ]),
        )

    elif data.startswith("service:"):
        service = data.split(":", 1)[1]

        await query.edit_message_text(
            f"Service: {service}\n\n"
            "This is a demo service menu. No real account "
            "activation or OTP delivery is available.\n\n"
            f"Test OTP price: {TEST_PRICE} credits",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    "🧪 Run test OTP",
                    callback_data=f"demo:{service}"
                )],
                [InlineKeyboardButton(
                    "⬅️ Services",
                    callback_data="services"
                )],
            ]),
        )

    elif data.startswith("demo:"):
        service = data.split(":", 1)[1]

        if service not in SERVICES:
            await query.edit_message_text("Unknown service.")
            return

        if not deduct_balance(
            user.id,
            TEST_PRICE,
            f"Demo OTP: {service}",
        ):
            await query.edit_message_text(
                f"Insufficient demo credits.\n"
                f"Required: {TEST_PRICE}\n"
                f"Balance: {get_balance(user.id):.2f}\n\n"
                "Use /pay to request a top-up."
            )
            return

        code = await issue_test_otp(user.id, service)

        await query.edit_message_text(
            f"🧪 DEMO OTP — {service}\n\n"
            f"Test code: {code}\n"
            "Expires in 5 minutes.\n\n"
            "This is a simulated code for testing only. "
            "It will not verify or log in to any real account.\n\n"
            f"Remaining credits: {get_balance(user.id):.2f}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Main Menu", callback_data="home")
            ]]),
        )

    elif data == "admin":
        if not is_admin(user.id):
            await query.edit_message_text("Admin only.")
            return

        await query.edit_message_text(
            "Admin panel\n\n"
            "/stats - Statistics\n"
            "/users - Recent users\n"
            "/credit USER_ID AMOUNT\n"
            "/debit USER_ID AMOUNT\n"
            "/approve PAYMENT_ID\n"
            "/reject PAYMENT_ID"
        )


# ---------------- ERROR HANDLER ----------------

async def error_handler(update, context):
    log.error("Unhandled exception: %s", context.error)


# ---------------- MAIN ----------------

def main():
    if not TOKEN or ADMIN_ID == 0:
        raise SystemExit(
            "Please set BOT_TOKEN and ADMIN_ID in your .env file."
        )

    init_db()

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("balance", balance_cmd))
    app.add_handler(CommandHandler("testotp", testotp_cmd))
    app.add_handler(CommandHandler("addfunds", addfunds_cmd))
    app.add_handler(CommandHandler("pay", pay_cmd))

    app.add_handler(C