from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, CopyTextButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import db_mgr
import aiosqlite
from config import DB_PATH
from typing import Optional

panel_router = Router()

def ib(
    text: str,
    *,
    callback_data: Optional[str] = None,
    url: Optional[str] = None,
    style: Optional[str] = None,
    emoji_id: Optional[str] = None,
    copy_text: Optional[str] = None,
):
    kwargs = {"text": text}
    if callback_data is not None: kwargs["callback_data"] = callback_data
    if url is not None: kwargs["url"] = url
    if style is not None: kwargs["style"] = style
    if emoji_id is not None: kwargs["icon_custom_emoji_id"] = emoji_id
    if copy_text is not None: kwargs["copy_text"] = CopyTextButton(text=copy_text)
    return InlineKeyboardButton(**kwargs)

# ---------- general icons ----------
E_GEAR = "6138477872030947849"
E_LOCK = "5976409802262190486"
E_OK   = "6267115986541877538"

# ---------- action-specific icons (new) ----------
E_EDIT_URL   = "6204162490515855272"   # Edit URL button
E_TURN_OFF   = "5436167336639871203"   # Turn OFF action
E_TURN_ON    = "5798385735715261675"   # Turn ON action
E_DELETE     = "5445267414562389170"   # Delete Panel button
E_BACK       = "5458540078982773051"   # Back button (all)
E_SET_USER   = "5202216593966244027"   # Set Username button
E_SET_PASS   = "5807952667992920776"   # Set Password button
E_CLEAR      = "5904542823167824187"   # Clear Credentials button

# ---------- panel list active/inactive marker ----------
E_ACTIVE   = "4949926143370199866"     # panel is running
E_INACTIVE = "5318840353510408444"     # panel is not running

# ---------- STATUS custom emoji (SET / UNSET / OFF) ----------
ST_SET   = "6206479140040743133"   # sob set/active ache
ST_UNSET = "6305394740833558225"   # set nai
ST_OFF   = "6001162025206550903"   # set ache kintu monitor off

def se(kind: str) -> str:
    """status emoji tag banay. kind: 'set' | 'unset' | 'off'"""
    if kind == "set":
        return f'<tg-emoji emoji-id="{ST_SET}">✅</tg-emoji>'
    elif kind == "off":
        return f'<tg-emoji emoji-id="{ST_OFF}">🟡</tg-emoji>'
    else:
        return f'<tg-emoji emoji-id="{ST_UNSET}">❌</tg-emoji>'

# ==========================================
# 🗄️ STATES
# ==========================================
class ApiPanelFSM(StatesGroup):
    waiting_for_panel_name = State()
    waiting_for_panel_url = State()
    waiting_for_edit_url = State()

class SecurePanelFSM(StatesGroup):
    waiting_for_name = State()
    waiting_for_user = State()
    waiting_for_pass = State()
    waiting_for_edit_user = State()
    waiting_for_edit_pass = State()

# ==========================================
# 🔧 DB HELPERS
# ==========================================
async def get_secure_panel(name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM secure_panels WHERE name = ?", (name,))
        row = await cur.fetchone()
        return dict(row) if row else None

def _cut(data: str, prefix: str) -> str:
    return data[len(prefix):]

def _mask(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 2:
        return "•" * len(value)
    return value[0] + "•" * (len(value) - 2) + value[-1]

# ==========================================
# 1. CORE MENU BUILDER
# ==========================================
async def build_panels_menu():
    normal_panels = await db_mgr.get_all_panels()
    secure_panels = await db_mgr.get_all_secure_panels()

    kb = []

    for p in normal_panels:
        p = dict(p)
        style = "success" if p['status'] == "ON" else "primary"
        mark_emoji = E_ACTIVE if p['status'] == "ON" else E_INACTIVE
        kb.append([ib(f"{p['name']}", callback_data=f"panel_edit_{p['name']}", style=style, emoji_id=mark_emoji)])

    for p in secure_panels:
        p = dict(p)
        style = "success" if p['status'] == "ON" else "primary"
        mark_emoji = E_ACTIVE if p['status'] == "ON" else E_INACTIVE
        kb.append([ib(f"{p['name']} (Secure)", callback_data=f"secp_open_{p['name']}", style=style, emoji_id=mark_emoji)])

    kb.append([ib("Add New Panel", callback_data="add_panel_choose", style="primary", emoji_id=E_GEAR)])
    kb.append([ib("Back to Admin", callback_data="adm:panels", style="primary", emoji_id=E_BACK)])

    # legend + list with status marks (custom emoji e)
    lines = [f'<tg-emoji emoji-id="{E_GEAR}">⚙️</tg-emoji> <b>API Panels Management</b>', '']
    for p in normal_panels:
        p = dict(p)
        has_url = bool(p.get('url'))
        if p['status'] == "ON":
            mark = se("set")
        elif has_url:
            mark = se("off")
        else:
            mark = se("unset")
        lines.append(f'{mark} {p["name"]}')
    for p in secure_panels:
        p = dict(p)
        configured = bool(p.get('username') and p.get('password'))
        if p['status'] == "ON":
            mark = se("set")
        elif configured:
            mark = se("off")
        else:
            mark = se("unset")
        lines.append(f'{mark} {p["name"]} (Secure)')

    lines.append('')
    lines.append(f'{se("set")} Running · {se("off")} Configured (OFF) · {se("unset")} Not set')

    text = "\n".join(lines)
    return text, InlineKeyboardMarkup(inline_keyboard=kb)

# ==========================================
# 2. ENTRY HANDLERS
# ==========================================
@panel_router.message(F.text == "/panels")
async def cmd_panels(message: Message, state: FSMContext):
    await state.clear()
    text, kb = await build_panels_menu()
    await message.answer(text, reply_markup=kb)

@panel_router.callback_query(F.data.in_(["adm:panels", "manage_api_panels", "manage_panels", "api_panels", "admin_api_panels", "panel_management"]))
async def call_panels(call: CallbackQuery, state: FSMContext):
    await state.clear()
    text, kb = await build_panels_menu()
    try:
        await call.message.edit_text(text, reply_markup=kb)
    except Exception:
        await call.message.answer(text, reply_markup=kb)
    await call.answer()

# ==========================================
# 3. ADD NEW PANEL (type choose)
# ==========================================
@panel_router.callback_query(F.data == "add_panel_choose")
async def add_panel_choose(call: CallbackQuery, state: FSMContext):
    await state.clear()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [ib("API URL Panel", callback_data="add_api_panel", style="primary", emoji_id=E_GEAR)],
        [ib("Secure Panel (User/Pass)", callback_data="add_secure_panel", style="primary", emoji_id=E_LOCK)],
        [ib("Back", callback_data="adm:panels", style="primary", emoji_id=E_BACK)],
    ])
    text = f'<tg-emoji emoji-id="{E_GEAR}">⚙️</tg-emoji> <b>Add New Panel</b>\n\nKon type er panel add korbe?'
    try:
        await call.message.edit_text(text, reply_markup=kb)
    except Exception:
        await call.message.answer(text, reply_markup=kb)
    await call.answer()

# ---------- Normal API panel add ----------
@panel_router.callback_query(F.data == "add_api_panel")
async def add_api_panel_start(call: CallbackQuery, state: FSMContext):
    await call.message.answer(f'<tg-emoji emoji-id="{E_GEAR}">⚙️</tg-emoji> Send the <b>Name</b> for the new API Panel:')
    await state.set_state(ApiPanelFSM.waiting_for_panel_name)
    await call.answer()

@panel_router.message(ApiPanelFSM.waiting_for_panel_name)
async def process_new_panel_name(message: Message, state: FSMContext):
    await state.update_data(new_panel_name=message.text.strip())
    await message.answer(f'<tg-emoji emoji-id="{E_GEAR}">⚙️</tg-emoji> Now send the <b>API URL</b> for this panel:')
    await state.set_state(ApiPanelFSM.waiting_for_panel_url)

@panel_router.message(ApiPanelFSM.waiting_for_panel_url)
async def process_new_panel_url(message: Message, state: FSMContext):
    url = message.text.strip()
    data = await state.get_data()
    name = data['new_panel_name']

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR REPLACE INTO api_panels (name, url, status) VALUES (?, ?, 'ON')", (name, url))
        await db.commit()

    await state.clear()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [ib("Open Panel", callback_data=f"panel_edit_{name}", style="success", emoji_id=E_GEAR)],
        [ib("Back to Panels", callback_data="adm:panels", style="primary", emoji_id=E_BACK)],
    ])
    await message.answer(f'{se("set")} Panel <b>{name}</b> added successfully!', reply_markup=kb)

# ---------- Secure panel add ----------
@panel_router.callback_query(F.data == "add_secure_panel")
async def add_secure_panel_start(call: CallbackQuery, state: FSMContext):
    await call.message.answer(f'<tg-emoji emoji-id="{E_LOCK}">🔐</tg-emoji> Send the <b>Name</b> for the new Secure Panel:')
    await state.set_state(SecurePanelFSM.waiting_for_name)
    await call.answer()

@panel_router.message(SecurePanelFSM.waiting_for_name)
async def add_secure_name(message: Message, state: FSMContext):
    name = message.text.strip()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO secure_panels (name, username, password, status) VALUES (?, '', '', 'OFF')",
            (name,)
        )
        await db.commit()
    await state.update_data(current_panel=name)
    await message.answer(f'<tg-emoji emoji-id="{E_LOCK}">🔐</tg-emoji> Send the <b>Username</b> for <b>{name}</b>:')
    await state.set_state(SecurePanelFSM.waiting_for_user)

# ==========================================
# 4. NORMAL PANEL DETAIL
# ==========================================
async def adm_panel_detail_refresh(call: CallbackQuery, panel_name: str):
    panel = await db_mgr.get_panel(panel_name)
    if not panel:
        await call.answer("Panel not found!", show_alert=True)
        return
    panel = dict(panel)

    has_url = bool(panel.get('url'))
    if panel['status'] == "ON":
        status_mark = se("set")
    elif has_url:
        status_mark = se("off")
    else:
        status_mark = se("unset")
    url_mark = se("set") if has_url else se("unset")

    is_on = panel['status'] == "ON"
    status_btn = "Turn OFF" if is_on else "Turn ON"
    status_style = "danger" if is_on else "success"
    status_emoji = E_TURN_OFF if is_on else E_TURN_ON

    kb = [
        [ib("Edit URL", callback_data=f"panel_url_{panel_name}", style="primary", emoji_id=E_EDIT_URL)],
        [ib(status_btn, callback_data=f"panel_toggle_{panel_name}", style=status_style, emoji_id=status_emoji)],
        [ib("Delete Panel", callback_data=f"panel_delete_{panel_name}", style="danger", emoji_id=E_DELETE)],
        [ib("Back", callback_data="adm:panels", style="primary", emoji_id=E_BACK)]
    ]

    text = (
        f'<tg-emoji emoji-id="{E_GEAR}">⚙️</tg-emoji> <b>Panel:</b> {panel_name}\n'
        f'<b>Type:</b> API URL\n'
        f'<b>Status:</b> {status_mark} {panel["status"]}\n'
        f'<b>URL:</b> {url_mark} <code>{panel["url"] or "Not Set"}</code>'
    )
    try:
        await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    except Exception:
        await call.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@panel_router.callback_query(F.data.startswith("panel_edit_"))
async def edit_normal_panel(call: CallbackQuery):
    await adm_panel_detail_refresh(call, _cut(call.data, "panel_edit_"))
    await call.answer()

@panel_router.callback_query(F.data.startswith("panel_url_"))
async def edit_normal_panel_url(call: CallbackQuery, state: FSMContext):
    panel_name = _cut(call.data, "panel_url_")
    await state.update_data(edit_panel_name=panel_name)
    await call.message.answer(f'<tg-emoji emoji-id="{E_EDIT_URL}">⚙️</tg-emoji> Send the new URL for <b>{panel_name}</b>:')
    await state.set_state(ApiPanelFSM.waiting_for_edit_url)
    await call.answer()

@panel_router.message(ApiPanelFSM.waiting_for_edit_url)
async def save_normal_panel_url(message: Message, state: FSMContext):
    new_url = message.text.strip()
    data = await state.get_data()
    panel_name = data['edit_panel_name']

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE api_panels SET url = ? WHERE name = ?", (new_url, panel_name))
        await db.commit()

    await state.clear()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [ib("Open Panel", callback_data=f"panel_edit_{panel_name}", style="success", emoji_id=E_GEAR)],
        [ib("Back to Panels", callback_data="adm:panels", style="primary", emoji_id=E_BACK)],
    ])
    await message.answer(f'{se("set")} URL updated for <b>{panel_name}</b>!', reply_markup=kb)

@panel_router.callback_query(F.data.startswith("panel_toggle_"))
async def adm_panel_toggle(call: CallbackQuery):
    name = _cut(call.data, "panel_toggle_")
    p = await db_mgr.get_panel(name)
    if not p:
        await call.answer("Panel not found!", show_alert=True)
        return
    p = dict(p)

    current_status = p.get('status', 'OFF')
    has_url = bool(p['url'] and str(p['url']).startswith("http"))

    if current_status != 'ON' and not has_url:
        await call.answer("⚠️ Please Add API URL first before turning it ON!", show_alert=True)
        return

    new_status = 'OFF' if current_status == 'ON' else 'ON'

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE api_panels SET status = ? WHERE name = ?", (new_status, name))
        await db.commit()

    await call.answer(f"✅ {name} Panel is now {new_status}!")
    await adm_panel_detail_refresh(call, name)

@panel_router.callback_query(F.data.startswith("panel_delete_"))
async def delete_normal_panel(call: CallbackQuery, state: FSMContext):
    panel_name = _cut(call.data, "panel_delete_")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM api_panels WHERE name = ?", (panel_name,))
        await db.commit()
    await call.answer(f"{panel_name} deleted!")
    await call_panels(call, state)

# ==========================================
# 5. SECURE PANEL DETAIL
# ==========================================
async def secure_panel_detail(call: CallbackQuery, panel_name: str, force_new: bool = False):
    p = await get_secure_panel(panel_name)
    if not p:
        await call.answer("Panel not found!", show_alert=True)
        return

    username = p.get('username') or ""
    password = p.get('password') or ""
    status = p.get('status') or "OFF"
    configured = bool(username and password)

    username_mark = se("set") if username else se("unset")
    password_mark = se("set") if password else se("unset")
    config_mark = se("set") if configured else se("unset")

    if status == "ON":
        status_mark = se("set")
    elif configured:
        status_mark = se("off")
    else:
        status_mark = se("unset")

    is_on = status == "ON"
    status_btn = "Stop Monitoring" if is_on else "Start Monitoring"
    status_style = "danger" if is_on else "success"
    status_emoji = E_TURN_OFF if is_on else E_TURN_ON

    kb = [
        [ib("Set Username", callback_data=f"secp_user_{panel_name}", style="primary", emoji_id=E_SET_USER)],
        [ib("Set Password", callback_data=f"secp_pass_{panel_name}", style="primary", emoji_id=E_SET_PASS)],
        [ib(status_btn, callback_data=f"secp_toggle_{panel_name}", style=status_style, emoji_id=status_emoji)],
        [ib("Clear Credentials", callback_data=f"secp_clear_{panel_name}", style="danger", emoji_id=E_CLEAR)],
        [ib("Back", callback_data="adm:panels", style="primary", emoji_id=E_BACK)]
    ]

    text = (
        f'<tg-emoji emoji-id="{E_LOCK}">🔐</tg-emoji> <b>Panel:</b> {panel_name}\n'
        f'<b>Type:</b> Secure (Login)\n'
        f'<b>Status:</b> {status_mark} {"Monitoring ON" if status == "ON" else ("Configured (OFF)" if configured else "Not Configured")}\n'
        f'<b>Config:</b> {config_mark} {"Ready" if configured else "Incomplete"}\n\n'
        f'<b>Username:</b> {username_mark} <code>{username if username else "Not Set"}</code>\n'
        f'<b>Password:</b> {password_mark} <code>{_mask(password) if password else "Not Set"}</code>'
    )

    markup = InlineKeyboardMarkup(inline_keyboard=kb)
    if force_new:
        await call.message.answer(text, reply_markup=markup)
        return
    try:
        await call.message.edit_text(text, reply_markup=markup)
    except Exception:
        await call.message.answer(text, reply_markup=markup)

@panel_router.callback_query(F.data.startswith("secp_open_"))
async def open_secure_panel(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await secure_panel_detail(call, _cut(call.data, "secp_open_"))
    await call.answer()

# ---------- edit username ----------
@panel_router.callback_query(F.data.startswith("secp_user_"))
async def secure_set_user(call: CallbackQuery, state: FSMContext):
    panel_name = _cut(call.data, "secp_user_")
    await state.update_data(current_panel=panel_name)
    await call.message.answer(f'<tg-emoji emoji-id="{E_SET_USER}">👤</tg-emoji> Send the <b>Username</b> for <b>{panel_name}</b>:')
    await state.set_state(SecurePanelFSM.waiting_for_edit_user)
    await call.answer()

@panel_router.message(SecurePanelFSM.waiting_for_edit_user)
async def secure_save_user(message: Message, state: FSMContext):
    data = await state.get_data()
    panel_name = data.get('current_panel')
    username = message.text.strip()

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE secure_panels SET username=? WHERE name=?", (username, panel_name))
        await db.commit()

    await state.clear()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [ib("Open Panel", callback_data=f"secp_open_{panel_name}", style="success", emoji_id=E_LOCK)],
        [ib("Back to Panels", callback_data="adm:panels", style="primary", emoji_id=E_BACK)],
    ])
    await message.answer(f'{se("set")} Username saved for <b>{panel_name}</b>.', reply_markup=kb)

# ---------- edit password ----------
@panel_router.callback_query(F.data.startswith("secp_pass_"))
async def secure_set_pass(call: CallbackQuery, state: FSMContext):
    panel_name = _cut(call.data, "secp_pass_")
    await state.update_data(current_panel=panel_name)
    await call.message.answer(f'<tg-emoji emoji-id="{E_SET_PASS}">🔑</tg-emoji> Send the <b>Password</b> for <b>{panel_name}</b>:')
    await state.set_state(SecurePanelFSM.waiting_for_edit_pass)
    await call.answer()

@panel_router.message(SecurePanelFSM.waiting_for_edit_pass)
async def secure_save_pass(message: Message, state: FSMContext):
    data = await state.get_data()
    panel_name = data.get('current_panel')
    password = message.text.strip()

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE secure_panels SET password=? WHERE name=?", (password, panel_name))
        await db.commit()

    try:
        await message.delete()   # password message muche dewa
    except Exception:
        pass

    await state.clear()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [ib("Open Panel", callback_data=f"secp_open_{panel_name}", style="success", emoji_id=E_LOCK)],
        [ib("Back to Panels", callback_data="adm:panels", style="primary", emoji_id=E_BACK)],
    ])
    await message.answer(f'{se("set