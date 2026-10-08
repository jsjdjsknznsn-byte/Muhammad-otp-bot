from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import to_bold_font

def main_permanent_keyboard(user_id: int, is_admin: bool = False) -> ReplyKeyboardMarkup:
    kb = [
        [
            KeyboardButton(text="🟩 GET NUMBER"),
            KeyboardButton(text="🟩 TRAFFIC")
        ],
        [
            KeyboardButton(text="🟦 WALLET"),
            KeyboardButton(text="🟦 STATISTICS")
        ],
        [
            KeyboardButton(text="🟥 TOP USERS"),
            KeyboardButton(text="🟥 SUPPORT")
        ]
    ]
    if is_admin:
        kb.append([KeyboardButton(text="🟪 ADMIN PANEL")])
        
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def admin_inline_panel() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="➕ Add Numbers", callback_data="adm_add_num"),
                InlineKeyboardButton(text="📂 Manage Numbers", callback_data="adm_mng_num"))
    builder.row(InlineKeyboardButton(text="📁 Manage Categories", callback_data="adm_mng_cat"),
                InlineKeyboardButton(text="💸 Withdraw Requests", callback_data="adm_with_req"))
    builder.row(InlineKeyboardButton(text="📣 Broadcast", callback_data="adm_broadcast"),
                InlineKeyboardButton(text="👤 Admin List", callback_data="adm_list"))
    builder.row(InlineKeyboardButton(text="⚙️ Settings", callback_data="adm_settings"),
                InlineKeyboardButton(text="📣 Req. Channels", callback_data="adm_req_chan"))
    builder.row(InlineKeyboardButton(text="👮 Add Admin", callback_data="adm_add_adm"),
                InlineKeyboardButton(text="🚫 Remove Admin", callback_data="adm_rem_adm"))
    return builder.as_markup()
