import io
import re
import base64
import logging
from typing import Optional, Any
import datetime
import time  # 🔥 এই লাইনটা নতুন অ্যাড করা হলো
from aiogram.types import Message, CallbackQuery
from aiogram import F
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from panel_manager import panel_router, SecurePanelFSM, ApiPanelFSM
from aiogram.filters import StateFilter

# 🔥 বট স্টার্ট হওয়ার বর্তমান সময় রেকর্ড করে রাখা হলো (এর আগের কোনো ডেটা আর ধরবে না)
BOT_START_TIME = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
import aiosqlite

from aiogram import Router, F, types
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CopyTextButton,
)
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from config import (
    BOT_TOKEN,
    OTP_GROUP_LINK,
    UPDATE_CHANNEL_LINK,
    EXTRA_LINK_1,
    EXTRA_LINK_2, 
    BTN_EMOJIS,
    format_p_emo,
    DB_PATH,
    OTP_GROUP_ID,
    SYS_EMOJI,
)
from database import (
    db_mgr,
    GLOBAL_COUNTRY_MAP,
    resolve_universal_country,
)

# 🔥 অ্যাডমিন নোটিশের স্টেট ক্লাসটা ঠিক এইখানে বসে গেলো
class AdminNoticeState(StatesGroup):
    waiting_for_message = State()
    target_user_id = State()
# =========================================================
# LOGGER
# =========================================================

logger = logging.getLogger(__name__)

router = Router()
router.include_router(panel_router)  # 🔥 Ei line ta add korbe

# 🔥 ঠিক এইখানে গ্লোবাল ব্যান মিডলওয়্যার এবং নোটিশ হ্যান্ডলার বসিয়ে দিন:

from aiogram import BaseMiddleware

class GlobalBanMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user = event.from_user
        if not user:
            return await handler(event, data)
            
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM users WHERE user_id = ?", (user.id,))
            row = await cursor.fetchone()
            is_banned = 0
            if row:
                try:
                    is_banned = row["is_banned"]
                except Exception:
                    is_banned = 0
            
        if is_banned:
            # শুধু Support এবং Unban/Notice বাটন কাজ করবে
            if isinstance(event, types.CallbackQuery):
                if "support" in event.data.lower() or "sys_" in event.data:
                    return await handler(event, data)
                await event.answer("🚫 You are permanently BANNED! Only Support is allowed.", show_alert=True)
                return
            elif isinstance(event, types.Message):
                if event.text and "/start" in event.text:
                    pass # Start অ্যালাউ করা হলো যাতে সাপোর্ট বাটন দেখতে পায়
                else:
                    await event.answer("🚫 You are permanently BANNED from using this bot. Contact Support.")
                    return
                    
        return await handler(event, data)

# 🔥 গ্লোবাল লক চালু
router.message.middleware(GlobalBanMiddleware())
router.callback_query.middleware(GlobalBanMiddleware())

# 🔥 Notice Handler একদম ওপরে রাখা হলো যাতে অন্য কেউ ক্যাচ না করে
@router.message(AdminNoticeState.waiting_for_message)
async def process_sys_notice_send(message: types.Message, state: FSMContext):
    if message.text and message.text.lower() == "/cancel":
        await state.clear()
        return await message.reply("Action cancelled.")
        
    data = await state.get_data()
    target_id = data.get("target_user_id")
    
    notice_text = (
        f'<tg-emoji emoji-id="5420323339723881652">⚠️</tg-emoji> <b>Message from Admin:</b>\n\n'
        f'{message.html_text}'
    )
    
    try:
        await message.bot.send_message(chat_id=target_id, text=notice_text)
        await message.reply(f"✅ Notice sent successfully to user {target_id}.")
    except Exception:
        await message.reply("❌ Failed to send notice. User might have blocked the bot.")
        
    await state.clear()

# =========================================================
# CONSTANTS
# =========================================================

MENU_GET = "𝐆𝐄𝐓 𝐍𝐔𝐌𝐁𝐄𝐑"
MENU_STATUS = "𝐒𝐓𝐀𝐓𝐔𝐒"
MENU_ACTIVE = "𝐀𝐂𝐓𝐈𝐕𝐄 𝐍𝐔𝐌𝐁𝐄𝐑"
MENU_SUPPORT = "𝐒𝐔𝐏𝐏𝐎𝐑𝐓"
MENU_REFER = "𝐑𝐄𝐅𝐄𝐑"
MENU_WALLET = "𝐖𝐀𝐋𝐋𝐄𝐓"
MENU_ADMIN = "𝐀𝐃𝐌𝐈𝐍 𝐏𝐀𝐍𝐄𝐋"
MENU_LEADERBOARD = "𝐋𝐄𝐀𝐃𝐄𝐑𝐁𝐎𝐀𝐑𝐃"
#
=========================================================
# PREMIUM / CUSTOM EMOJI IDs
# =========================================================

SERVICE_EMOJIS = {
    "facebook": {"emoji_id": "5323261730283863478", "placeholder": ""},
    "tiktok": {"emoji_id": "5327982530702359565", "placeholder": ""},
    "whatsapp": {"emoji_id": "5334998226636390258", "placeholder": ""},
    "telegram": {"emoji_id": "5244763347454300958", "placeholder": ""},
    "instagram": {"emoji_id": "5319160079465857105", "placeholder": ""},
    "paypal": {"emoji_id": "5364111181415996352", "placeholder": ""},
    "discord": {"emoji_id": "5325612636467903082", "placeholder": ""},
    "amazon": {"emoji_id": "6161414526399948623", "placeholder": ""},
    "pariland": {"emoji_id": "6161016606269907350", "placeholder": ""},
    "uber": {"emoji_id": "5298715455316303708", "placeholder": ""},
    "shopee": {"emoji_id": "6161414526399948623", "placeholder": ""},
    "apple": {"emoji_id": "5334955749409834455", "placeholder": ""},
    "hsbc": {"emoji_id": "6249045530119249807", "placeholder": ""},
    "alfursan": {"emoji_id": "6156449849148448697", "placeholder": ""},
    "microsoft": {"emoji_id": "5370857634440170316", "placeholder": ""},
    "bolt": {"emoji_id": "6179401140765992368", "placeholder": ""},
    "binance": {"emoji_id": "5281029063459234079", "placeholder": ""},
    "infosms": {"emoji_id": "5796690095511703420", "placeholder": ""},
    "signal": {"emoji_id": "5328050550099427291", "placeholder": ""},
    "imo": {"emoji_id": "6219680125751926660", "placeholder": ""},
    "indrive": {"emoji_id": "6163492921204024370", "placeholder": ""},
    "fib": {"emoji_id": "5332455502917949981", "placeholder": ""},
    "default": {"emoji_id": "5346066456142429527", "placeholder": ""},
}

def format_p_emo(emoji_id: str, fallback: str) -> str:
    if emoji_id and emoji_id != "0": 
        return f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>'
    return fallback

def get_service_custom_emoji_id(service_name: str) -> str:
    lower_s = str(service_name).lower().strip()
    # 🔥 Since it's a dictionary now, we need to extract ["emoji_id"]
    service_data = SERVICE_EMOJIS.get(lower_s, SERVICE_EMOJIS["default"])
    return service_data["emoji_id"]


COUNTRY_EMOJIS = {
    "AFGHANISTAN": "5294096544406976986",
    "ALBANIA": "5294250613473820536",
    "ALGERIA": "5294286064133879533",
    "ANDORRA": "5292244112127309992",
    "ANGOLA": "5292213828312905338",
    "ANTIGUA AND BARBUDA": "5292270732334611090",
    "ARGENTINA": "5294179501700298684",
    "ARMENIA": "5291774508993100789",
    "AUSTRALIA": "5293988654828502400",
    "AUSTRIA": "5292285751835244257",
    "AZERBAIJAN": "5292095441834359120",
    "BAHAMAS": "5294068987896806041",
    "BAHRAIN": "5294282555145598445",
    "BANGLADESH": "5294500851153385168",
    "BARBADOS": "5294290943216727979",
    "BELARUS": "5294128460308952497",
    "BELGIUM": "5294255703010064221",
    "BELIZE": "5294192678659969543",
    "BENIN": "5294279724762151165",
    "BERMUDA": "5292231854290647654",
    "BHUTAN": "5294257004385155104",
    "BOLIVIA": "5294033743395176282",
    "BOSNIA AND HERZEGOVINA": "5294316730200375501",
    "BOTSWANA": "5291869986116090404",
    "BRAZIL": "5294401014638590651",
    "BRUNEI": "5292093668012865550",
    "BULGARIA": "5294009549844398897",
    "BURKINA FASO": "5292036948674754260",
    "BURUNDI": "5292178265983695853",
    "CABO VERDE": "5294466272371686676",
    "CAMBODIA": "5294018354527353443",
    "CAMEROON": "5294089569380088333",
    "CANADA": "5292023956398684554",
    "CENTRAL AFRICAN REPUBLIC": "5294120372885536804",
    "CHAD": "5291961301415772318",
    "CHILE": "5291837722321762793",
    "CHINA": "5294528665361594977",
    "COLOMBIA": "5294323009442559993",
    "COMOROS": "5294064022914611434",
    "CONGO": "5292182775699355868",
    "COSTA RICA": "5294360221039211867",
    "CROATIA": "5294379818974983811",
    "CYPRUS": "5292256812345604723",
    "CZECH REPUBLIC": "5294420372056194185",
    "DENMARK": "5294524868610505865",
    "DJIBOUTI": "5291791985215026199",
    "DOMINICA": "5292080314959543164",
    "DOMINICAN REPUBLIC": "5291962040150145704",
    "DR CONGO": "5294524718286648684",
    "ECUADOR": "5294034005388180164",
    "EGYPT": "5292168898660021541",
    "EL SALVADOR": "5291933873754616525",
    "ENGLAND": "5294044768576225045",
    "EQUATORIAL GUINEA": "5294232686280325366",
    "ESTONIA": "5294406580916207129",
    "ESWATINI": "5292027955013238582",
    "ETHIOPIA": "5294512168392209285",
    "EUROPEAN UNION": "5292215219882326573",
    "FIJI": "5294307040754157008",
    "FINLAND": "5292088630016227941",
    "FRANCE": "5294324697364707139",
    "GABON": "5294404137079813976",
    "GAMBIA": "5292179193696630126",
    "GEORGIA": "5292010100834186995",
    "GERMANY": "5294470636058458270",
    "GHANA": "5294208810557126145",
    "GREECE": "5292126163735427226",
    "GRENADA": "5291955851102271781",
    "GUATEMALA": "5294371392249149894",
    "GUINEA": "5294318061640235074",
    "GUINEA-BISSAU": "5292022620663855264",
    "GUYANA": "5294398167075273417",
    "HAITI": "5294173759329025494",
    "HONDURAS": "5292122826545838570",
    "HUNGARY": "5291889682836109921",
    "ICELAND": "5291879185936037620",
    "INDIA": "5294510171232419362",
    "INDONESIA": "5294364674920301441",
    "IRAN": "5294418473680649993",
    "IRAQ": "5294084990944952018",
    "IRELAND": "5294046293289614882",
    "ISRAEL": "5291780457522806625",
    "ITALY": "5291783691633179315",
    "JAMAICA": "5294171766464198371",
    "JAPAN": "5292252637637394017",
    "JORDAN": "5294235112936847701",
    "KAZAKHSTAN": "5292132601891406351",
    "KENYA": "5293996922640546414",
    "KIRIBATI": "5294082864936140082",
    "KOSOVO": "5294020669514727367",
    "KUWAIT": "5294510665153657908",
    "KYRGYZSTAN": "5294072870547241138",
    "LAOS": "5294515754689902278",
    "LATVIA": "5294197897045228028",
    "LEBANON": "5291982140597091240",
    "LESOTHO": "5294143643018345113",
    "LIBERIA": "5292232056154109362",
    "LIBYA": "5294081679525165705",
    "LIECHTENSTEIN": "5291983553641331042",
    "LITHUANIA": "5294343436307020064",
    "LUXEMBOURG": "5294194808963743125",
    "MADAGASCAR": "5291743636768176974",
    "MALAYSIA": "5292109885809376609",
    "MALDIVES": "5292156288636041561",
    "MALI": "5292134435842439385",
    "MALTA": "5294538900268661088",
    "MARSHALL ISLANDS": "5292053029032311205",
    "MARTINIQUE": "5292100419701455839",
    "MAURITIUS": "5294442087410842048",
    "MEXICO": "5291875964710567607",
    "MICRONESIA": "5292212260649843267",
    "MOLDOVA": "5292243875904108185",
    "MONACO": "5291754241042429367",
    "MONGOLIA": "5294157674676500911",
    "MONTENEGRO": "5294007037288527822",
    "MOROCCO": "5294475854443723073",
    "MOZAMBIQUE": "5291747167231294255",
    "NAMIBIA": "5291794609440047824",
    "NEPAL": "5294374235517500613",
    "NETHERLANDS": "5294241847445566691",
    "NEW ZEALAND": "5292140092314367840",
    "NIGER": "5294512361665738891",
    "NIGERIA": "5294130362979465506",
    "NORTH MACEDONIA": "5294302797326465547",
    "NORWAY": "5291807953903434152",
    "OMAN": "5291911668773699198",
    "PAKISTAN": "5291913455480092451",
    "PALAU": "5294108389926780755",
    "PALESTINE": "5294319208396502996",
    "PANAMA": "5291750233837944755",
    "PAPUA NEW GUINEA": "5294033584481383769",
    "PARAGUAY": "5291897044410055523",
    "PERU": "5291960111709830256",
    "PHILIPPINES": "5294212306660507275",
    "PORTUGAL": "5292106978116516589",
    "PUERTO RICO": "5294287021911586554",
    "QATAR": "5294044214525442531",
    "ROMANIA": "5294080455459486227",
    "RUSSIA": "5291734595862018096",
    "RWANDA": "5294524765531291089",
    "SAINT KITTS AND NEVIS": "5291931442803126844",
    "SAINT LUCIA": "5294255234858630622",
    "SAINT VINCENT AND THE GRENADINES": "5294418671249142859",
    "SAMOA": "5294254500419221878",
    "SAN MARINO": "5292127714218622101",
    "SAO TOME AND PRINCIPE": "5294491312031021064",
    "SAUDI ARABIA": "5294345751294393183",
    "SCOTLAND": "5292267541173909411",
    "SENEGAL": "5292266553331433530",
    "SERBIA": "5291929449938302792",
    "SEYCHELLES": "5294299185258969386",
    "SIERRA LEONE": "5292063143680291937",
    "SINGAPORE": "5294406215843985891",
    "SLOVAKIA": "5292028285725719287",
    "SLOVENIA": "5294068021529164085",
    "SOLOMON ISLANDS": "5292246096402201145",
    "SOMALIA": "5294078355220478091",
    "SOUTH AFRICA": "5294100525841659817",
    "SOUTH KOREA": "5294103841556413525",
    "SOUTH SUDAN": "5292027637185658003",
    "SPAIN": "5294323318680206912",
    "SRI LANKA": "5291887612661872281",
    "SUDAN": "5294204670208653563",
    "SURINAME": "5294004254149721569",
    "SWEDEN": "5292195991313726356",
    "SWITZERLAND": "5291752789343485768",
    "TAJIKISTAN": "5292058496525679262",
    "TANZANIA": "5292124531647854609",
    "THAILAND": "5294308565467543746",
    "TIMOR-LESTE": "5292026151126970843",
    "TOGO": "5294043261042703048",
    "TRINIDAD AND TOBAGO": "5294412254568004481",
    "TUNISIA": "5294039313967757294",
    "TURKMENISTAN": "5292055356904585500",
    "TURKEY": "5292218402453075461",
    "UAE": "5294285256680029509",
    "UGANDA": "5294079660890535793",
    "UNITED KINDOM": "5294447773947543583",
    "UKRAINE": "5294210833486724321",
    "URUGUAY": "5291863865787694128",
    "USA": "5291747893080766866",
    "UZBEKISTAN": "5294289324014057127",
    "MAURITANIA": "5404566049607663230",
    "VATICAN CITY": "5294429004940458392",
    "VIETNAM": "5294317155402137202",
    "VIRGIN ISLANDS": "5294211696775150914",
    "SYRIA": "5291969728141625850",
    "YEMEN": "5291806802852198444",
    "ZAMBIA": "5294161127830205421",
    "ZIMBABWE": "5292167442666110763",
}

# =========================================================
# BUTTON EMOJI IDs
# =========================================================

E_GET = "5800835941543186089"
E_STATUS = "5258028182149286660"
E_ACTIVE = "5386367538735104399"
E_SUPPORT = "5366043289633962337"
E_REFER = "5332724926216428039"
E_WALLET = "5215420556089776398"
E_ADMIN = "5316832430529722441"
E_BACK = "6206505206197261313"
E_VERIFY = "5330194932781050507"
E_GROUP = "5841494459904168607"
E_CHANGE = "5370715282044100355"
E_CC = "5188540541922480562"


# =========================================================
# FSM
# =========================================================

class Form(StatesGroup):
    waiting_for_numbers = State()
    waiting_for_service = State()
    waiting_for_nums_per_user = State()
    waiting_for_rate = State()

    waiting_for_broadcast_decision = State()
    waiting_for_broadcast_msg = State()

    waiting_for_withdraw_amt = State()
    waiting_for_withdraw_number = State()

    waiting_for_set_wallet_number = State()

    waiting_for_new_admin = State()
    waiting_for_edit_support = State()
    waiting_for_edit_min_with = State()

    waiting_for_req_channel = State()
    waiting_for_new_service = State()

    waiting_for_edit_service_rate = State()
    # Eita notun add koro
    waiting_for_panel_url = State()
    editing_panel_name = State()

# =========================================================
# BOLD FONT
# =========================================================

def to_bold_font(text: str) -> str:
    normal = (
        "abcdefghijklmnopqrstuvwxyz"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        "0123456789"
    )

    bold = (
        "𝗮𝗯𝗰𝗱𝗲𝗳𝗴𝗵𝗶𝗷𝗸𝗹𝗺𝗻𝗼𝗽𝗾𝗿𝘀𝘁𝘂𝘃𝘄𝘅𝘆𝘇"
        "𝗔𝗕𝗖𝗗𝗘𝗙𝗚𝗛𝗜𝗝𝗞𝗟𝗠𝗡𝗢𝗣𝗤𝗥𝗦𝗧𝗨𝗩𝗪𝗫𝗬𝗭"
        "𝟬𝟭𝟮𝟯𝟰𝟱𝟲𝟳𝟴𝟵"
    )

    return text.translate(str.maketrans(normal, bold))


# =========================================================
# UNICODE BOLD -> NORMAL
# =========================================================

_BOLD_NORMAL = (
    "abcdefghijklmnopqrstuvwxyz"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "0123456789"
)

_BOLD_CHARS = (
    "𝗮𝗯𝗰𝗱𝗲𝗳𝗴𝗵𝗶𝗷𝗸𝗹𝗺𝗻𝗼𝗽𝗾𝗿𝘀𝘁𝘂𝘃𝘄𝘅𝘆𝘇"
    "𝗔𝗕𝗖𝗗𝗘𝗙𝗚𝗛𝗜𝗝𝗞𝗟𝗠𝗡𝗢𝗣𝗤𝗥𝗦𝗧𝗨𝗩𝗪𝗫𝗬𝗭"
    "𝟬𝟭𝟮𝟯𝟰𝟱𝟲𝟳𝟴𝟵"
)

BOLD_TO_NORMAL = str.maketrans(
    _BOLD_CHARS,
    _BOLD_NORMAL,
)


def normalize_button_text(text: str) -> str:
    if not text:
        return ""

    text = text.translate(BOLD_TO_NORMAL)

    text = (
        text.replace("\u200b", "")
        .replace("\u200c", "")
        .replace("\u200d", "")
        .replace("\ufeff", "")
    )

    text = re.sub(r"\s+", " ", text).strip()

    return text.upper()


# =========================================================
# CALLBACK DATA PACK / UNPACK
# =========================================================
def pack_callback(prefix: str, *values: Any) -> str:
    raw = "||".join(str(v) for v in values)

    encoded = base64.urlsafe_b64encode(
        raw.encode("utf-8")
    ).decode("ascii").rstrip("=")

    return f"{prefix}:{encoded}"


def unpack_callback(data: str, prefix: str) -> list[str]:
    marker = f"{prefix}:"

    if not data.startswith(marker):
        return []

    encoded = data[len(marker):]

    padding = "=" * (-len(encoded) % 4)

    try:
        raw = base64.urlsafe_b64decode(
            encoded + padding
        ).decode("utf-8")
    except Exception:
        return []

    return raw.split("||")


# =========================================================
# SERVICE EMOJI
# =========================================================

def get_service_custom_emoji_id(service_name: str) -> str:
    name = str(service_name).lower().strip()

    return SERVICE_EMOJIS.get(
        name,
        SERVICE_EMOJIS["default"],
    )["emoji_id"]


def get_service_placeholder(service_name: str) -> str:
    name = str(service_name).lower().strip()

    return SERVICE_EMOJIS.get(
        name,
        SERVICE_EMOJIS["default"],
    )["placeholder"]


# =========================================================
# COUNTRY EMOJI
# =========================================================

def get_country_custom_emoji_id(country_name: str) -> str:
    base_country = re.sub(r'\s*\d+$', '', str(country_name)).strip().upper()
    
    for key, emoji_id in COUNTRY_EMOJIS.items():
        if key != "default" and key in base_country:
            return emoji_id
    return COUNTRY_EMOJIS["default"]


# =========================================================
# PHONE NUMBER
# =========================================================

def extract_pure_number_without_cc(
    phone: str,
    country: str,
) -> str:

    clean = re.sub(r"\D", "", str(phone))
    base_country = re.sub(r'\s*\d+$', '', str(country)).strip().upper()

    for prefix in sorted(
        GLOBAL_COUNTRY_MAP.keys(),
        key=len,
        reverse=True,
    ):
        try:
            mapped_country = str(GLOBAL_COUNTRY_MAP[prefix]).strip().upper()

            if (
                mapped_country == base_country
                and clean.startswith(str(prefix))
            ):
                return clean[len(str(prefix)):]

        except Exception:
            continue

    return clean


# =========================================================
# SAFE BOT HELPERS
# =========================================================

async def send_msg(
    bot,
    chat_id: int | str,
    text: str,
    reply_markup=None,
):
    try:
        return await bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="HTML",
            reply_markup=reply_markup,
        )

    except TelegramForbiddenError:
        logger.warning(
            "Bot blocked by user/chat %s",
            chat_id,
        )
        return None

    except Exception:
        logger.exception(
            "send_message failed for %s",
            chat_id,
        )
        return None


async def safe_edit(
    message: types.Message,
    text: str,
    reply_markup=None,
):
    try:
        return await message.edit_text(
            text=text,
            parse_mode="HTML",
            reply_markup=reply_markup,
        )

    except TelegramBadRequest as exc:
        if "message is not modified" in str(exc).lower():
            return message

        logger.warning(
            "edit_text TelegramBadRequest: %s",
            exc,
        )

    except Exception:
        logger.exception("safe_edit failed")

    return None


async def safe_answer(
    callback: types.CallbackQuery,
    text: str = "",
    show_alert: bool = False,
):
    try:
await callback.answer(
            text=text,
            show_alert=show_alert,
        )
    except Exception:
        pass


# =========================================================
# MAIN REPLY KEYBOARD
# =========================================================

def main_permanent_keyboard(
    user_id: int,
    is_admin: bool = False,
) -> ReplyKeyboardMarkup:

    rows = [
        [
            KeyboardButton(text="𝐆𝐄𝐓 𝐍𝐔𝐌𝐁𝐄𝐑", style="success", icon_custom_emoji_id=E_GET),
            KeyboardButton(text="𝐒𝐓𝐀𝐓𝐔𝐒", style="primary", icon_custom_emoji_id=E_STATUS),
        ],
        [
            KeyboardButton(text="𝐀𝐂𝐓𝐈𝐕𝐄 𝐍𝐔𝐌𝐁𝐄𝐑", style="primary", icon_custom_emoji_id=E_ACTIVE),
            KeyboardButton(text="𝐒𝐔𝐏𝐏𝐎𝐑𝐓", style="primary", icon_custom_emoji_id=E_SUPPORT),
        ],
        [
            KeyboardButton(text="𝐑𝐄𝐅𝐄𝐑", style="primary", icon_custom_emoji_id=E_REFER),
            KeyboardButton(text="𝐖𝐀𝐋𝐋𝐄𝐓", style="success", icon_custom_emoji_id=E_WALLET),
        ],
        [
            KeyboardButton(text="𝐋𝐄𝐀𝐃𝐄𝐑𝐁𝐎𝐀𝐑𝐃", style="primary", icon_custom_emoji_id="6307633028680130361"),
        ]
    ]

    if is_admin:
        rows.append([KeyboardButton(text="𝐀𝐃𝐌𝐈𝐍 𝐏𝐀𝐍𝐄𝐋", style="danger", icon_custom_emoji_id=E_ADMIN)])

    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
        input_field_placeholder="Choose an option...",
    )


# =========================================================
# INLINE BUTTON HELPER
# =========================================================

def ib(
    text: str,
    *,
    callback_data: Optional[str] = None,
    url: Optional[str] = None,
    style: Optional[str] = None,
    emoji_id: Optional[str] = None,
    copy_text: Optional[str] = None,
):
    kwargs = {
        "text": text,
    }

    if callback_data is not None:
        kwargs["callback_data"] = callback_data

    if url is not None:
        kwargs["url"] = url

    if style is not None:
        kwargs["style"] = style

    if emoji_id is not None:
        kwargs["icon_custom_emoji_id"] = emoji_id

    if copy_text is not None:
        kwargs["copy_text"] = CopyTextButton(
            text=copy_text
        )

    return InlineKeyboardButton(**kwargs)


# =========================================================
# ADMIN PANEL
# =========================================================

def admin_inline_panel() -> InlineKeyboardMarkup:

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                ib(
                    "🔌 API Panels",
                    callback_data="adm:panels",
                    style="primary",
                    emoji_id="5316832430529722441",
                ),
                ib(
                    " Inventory Dashboard",
                    callback_data="adm:inventory",
                    style="primary",
                    emoji_id=E_STATUS,
                ),
            ],
            [
                ib(
                    " Add Numbers Pool",
                    callback_data="adm:addnum",
                    style="success",
                    emoji_id=E_GET,
                ),
                ib(
                    " Add Service",
                    callback_data="adm:addservice",
                    style="success",
                    emoji_id=E_GET,
                ),
            ],
            [
                ib(
                    " Manage Services",
                    callback_data="adm:services",
                    style="primary",
                    emoji_id=E_STATUS,
                ),
                ib(
                    " Withdrawal Nodes",
                    callback_data="adm:withdrawals",
                    style="primary",
                    emoji_id=E_ACTIVE,
                ),
            ],
            [
                ib(
                    "📢 PUSH Broadcast",
                    callback_data="adm:broadcast",
                    style="primary",
                    emoji_id=E_STATUS,
                ),
                ib(
                    " Admins Configuration",
                    callback_data="adm:admins",
                    style="primary",
                    emoji_id=E_ADMIN,
                ),
            ],
            [
                ib(
                    " Add System Admin",
                    callback_data="adm:addadmin",
                    style="success",
                    emoji_id=E_GET,
                ),
                ib(
                    " Decouple Admin Node",
                    callback_data="adm:removeadmin",
                    style="danger",
                    emoji_id=E_ADMIN,
                ),
            ],
            [
                ib(
                    " Requirements Channel",
                    callback_data="adm:reqchannel",
                    style="primary",
                    emoji_id=E_SUPPORT,
                ),
                ib(
                    " Global Configurations",
                    callback_data="adm:settings",
                    style="primary",
                    emoji_id=E_STATUS,
                ),
            ],
        ]
    )

# =========================================================
# MEMBERSHIP
# =========================================================

async def verify_dual_membership(
    bot,
    user_id: int,
) -> bool:

    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row

            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS global_config (
                    config_key TEXT PRIMARY KEY,
                    config_value TEXT
                )
                """
            )

            await db.commit()

            async with db.execute(
                """
                SELECT config_value
                FROM global_config
                WHERE config_key = 'req_channel'
                """
            ) as cursor:

                row = await cursor.fetchone()

        db_channel = (
            row["config_value"]
            if row
            else UPDATE_CHANNEL_LINK
        )

        channel_value = str(
            db_channel or ""
        ).strip()

        if channel_value.startswith("-100"):
            target_channel = int(channel_value)

        elif "t.me/" in channel_value:
            clean = channel_value.split(
                "t.me/",
                1,
            )[-1].strip("/")

            if clean.startswith("+"):
                return False

            if "joinchat/" in clean:
                return False

            target_channel = (
                clean
                if clean.startswith("@")
                else f"@{clean}"
            )

        else:
            target_channel = (
                channel_value
                if channel_value.startswith("@")
                else f"@{channel_value}"
            )

        channel_member = await bot.get_chat_member(
            chat_id=target_channel,
            user_id=user_id,
        )

        if channel_member.status in {
            "left",
            "kicked",
        }:
            return False

        group_member = await bot.get_chat_member(
            chat_id=OTP_GROUP_ID,
            user_id=user_id,
        )

        if group_member.status in {
            "left",
            "kicked",
        }:
            return False

        return True

    except Exception:
        logger.exception(
            "Membership verification failed for %s",
            user_id,
        )
        return False


# =========================================================
# JOIN KEYBOARD
# =========================================================

def generate_join_inline_keyboard():

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                ib(
                    " Join Official Channel",
                    url=UPDATE_CHANNEL_LINK,
                    style="primary",
                    emoji_id=E_SUPPORT,
                )
            ],
            [
                ib(
                    " Join Method Channel",
                    url=EXTRA_LINK_1,
                    style="primary",
                    emoji_id=E_SUPPORT,
                )
            ],
            [
                ib(
                    " Join Payment Proofs",
                    url=EXTRA_LINK_2,
                    style="primary",
                    emoji_id=E_SUPPORT,
                )
            ],
            [
                ib(
                    " Join Official OTP Group",
                    url=OTP_GROUP_LINK,
                    style="primary",
                    emoji_id=E_GROUP,
                )
            ],
            [
                ib(
                    " Try Again / VERIFY",
                    callback_data="membership:retry",
                    style="success",
                    emoji_id=E_VERIFY,
                )
            ],
        ]
    )


async def deny_access(
    bot,
    user_id: int,
):
    await send_msg(
        bot,
        user_id,
        (
            f"{SYS_EMOJI}  "
            f"<b>Access Denied!</b>\n\n"
            f"Please join both the official channel "
            f"and OTP group first."
        ),
        generate_join_inline_keyboard(),
    )


async def require_admin(
    callback: types.CallbackQuery,
) -> bool:

    try:
        return await db_mgr.is_admin(
            callback.from_user.id
        )
    except Exception:
        return False


async def service_selection_keyboard():

    categories = await db_mgr.get_categories()

    keyboard = []

    for category in categories:
        name = str(category["name"]).strip()

        keyboard.append(
            [
                ib(
                    f"{get_service_placeholder(name)} "
                    f"{name.upper()}",
                    callback_data=pack_callback(
                        "buy",
                        name,
                    ),
                    style="success",
                    emoji_id=get_service_custom_emoji_id(name),
                )
            ]
        )

    keyboard.append(
        [
            ib(
                " Main Menu",
                callback_data="menu:main",
                style="primary",
                emoji_id=E_BACK,
            )
        ]
    )

    return (
        categories,
        InlineKeyboardMarkup(
            inline_keyboard=keyboard
        ),
    )


def number_result_keyboard(
    service: str,
    country: str,
    allocated: list[str],
    cc_mode: str,
):

    rows = []

    country_emoji = get_country_custom_emoji_id(
        country
    )

    for number in allocated:

        display_number = (
            extract_pure_number_without_cc(
                number,
                country,
            )
            if cc_mode == "ON"
            else number
        )

        copied = (
            display_number
            if cc_mode == "ON"
            else f"+{display_number}"
        )

        rows.append(
            [
                ib(
                    f"{display_number}",
                    copy_text=copied,
                    style="primary",
                    emoji_id=country_emoji,
                )
            ]
        )

    cc_text = (
        "Remove CC: ON"
        if cc_mode == "ON"
        else "Remove CC: OFF"
    )

    rows.extend(
        [
            [
                ib(
                    "Change Number",
                    callback_data=pack_callback(
                        "change",
                        service,
                        country,
                    ),
                    style="primary",
                    emoji_id=E_CHANGE,
                )
            ],
            [
                ib(
                    cc_text,
                    callback_data=pack_callback(
                        "cc",
                        service,
                        country,
                    ),
                    style="success",
                    emoji_id=E_CC,
                )
            ],
            [
                ib(
                    "Main Menu",
                    callback_data="menu:main",
                    style="primary",
                    emoji_id=E_BACK,
                )
            ],
            [
                ib(
                    "OTP Group",
                    url=OTP_GROUP_LINK,
                    style="danger",
                    emoji_id=E_GROUP,
                )
            ],
        ]
    )

    return InlineKeyboardMarkup(
        inline_keyboard=rows
    )


def number_result_text(
    service: str,
    country: str,
):
    try:
        s_emoji_id = get_service_custom_emoji_id(service)
        s_emoji = f'<tg-emoji emoji-id="{s_emoji_id}">✅</tg-emoji>'
    except Exception:
        s_emoji = '✅'

    try:
        c_emoji_id = get_country_custom_emoji_id(country)
        c_emoji = f'<tg-emoji emoji-id="{c_emoji_id}">🌍</tg-emoji>'
    except Exception:
        c_emoji = '🌍'

    normal = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    premium = "𝐀𝐁𝐂𝐃𝐄𝐅𝐆𝐇𝐈𝐉𝐊𝐋𝐌𝐍𝐎𝐏𝐐𝐑𝐒𝐓𝐔𝐕𝗪𝐗𝐘𝐙𝐚𝐛𝐜𝐝𝐞𝐟𝐠𝐡𝗶𝐣𝗸𝗹𝗺𝗻𝐨𝐩𝐪𝐫𝐬𝐭𝐮𝘃𝘄𝘅𝘆𝘇"
    premium_service = service.upper().translate(str.maketrans(normal, premium))

    return (
        f'<tg-emoji emoji-id="6206236607532504295">💼</tg-emoji> <i><b>Service:</b></i> {s_emoji} <b>{premium_service}</b>\n'
        f'<tg-emoji emoji-id="6114021507908767611">🌎</tg-emoji> <i><b>Country:</b></i> {c_emoji} <b>{country.capitalize()}</b>\n\n'
        f'<tg-emoji emoji-id="5386367538735104399">⌛</tg-emoji> <b>Waiting for OTP</b>'
    )


async def show_allocated_numbers(
    message: types.Message,
    service: str,
    country: str,
    allocated: list[str],
):

    cc_mode = await db_mgr.get_config(
        "remove_cc"
    )

    text = number_result_text(
        service,
        country,
    )

    keyboard = number_result_keyboard(
        service,
        country,
        allocated,
        cc_mode,
    )

    await safe_edit(
        message,
        text,
        keyboard,
    )


@router.callback_query(
    F.data == "membership:retry"
)
async def process_membership_retry(
    callback: types.CallbackQuery,
    state: FSMContext,
):

    if not await verify_dual_membership(
        callback.bot,
        callback.from_user.id,
    ):
        await safe_answer(
            callback,
            " You have not joined both yet.",
            show_alert=True,
        )
        return

    await state.clear()

    is_admin = await db_mgr.is_admin(
        callback.from_user.id
    )

    await send_msg(
        callback.bot,
        callback.from_user.id,
        (
            f"{SYS_EMOJI}  "
            f"<b>Verification Successful!</b>\n\n"
            f"Welcome to the Elite 24/7 OTP Engine."
        ),
        main_permanent_keyboard(
            callback.from_user.id,
            is_admin,
        ),
    )

    try:
        await callback.message.delete()
    except Exception:
        pass

    await safe_answer(
        callback,
        "✅ Verified!",
    )


@router.callback_query(
    F.data == "menu:main"
)
async def callback_menu_main(
    callback: types.CallbackQuery,
    state: FSMContext,
):

    if not await verify_dual_membership(
        callback.bot,
        callback.from_user.id,
    ):
        await deny_access(
            callback.bot,
            callback.from_user.id,
        )
        await safe_answer(
            callback,
            "⚠️ Access denied.",
            show_alert=True,
        )
        return

    await state.clear()

    categories, keyboard = (
        await service_selection_keyboard()
    )

    if not categories:
        await safe_edit(
            callback.message,
            (
                f"{SYS_EMOJI}  "
                f"<b>No active services.</b>\n\n"
                f"Please try again later."
            ),
        )
        await safe_answer(callback)
        return

    await safe_edit(
        callback.message,
        (
            '<tg-emoji emoji-id="6206236607532504295">💼</tg-emoji> <b>Select service</b> <tg-emoji emoji-id="5197474438970363734">⤵️</tg-emoji>\n\n'
            'Choose a service to get a number:'
        ),
        keyboard,
    )

    await safe_answer(callback)


@router.callback_query(
    F.data.startswith("buy:")
)
async def process_allocation_service(
    callback: types.CallbackQuery,
    state: FSMContext,
):

    if not await verify_dual_membership(
        callback.bot,
        callback.from_user.id,
    ):
        await deny_access(
            callback.bot,
            callback.from_user.id,
        )
        await safe_answer(
            callback,
            " Access denied.",
            show_alert=True,
        )
        return

    await state.clear()

    values = unpack_callback(
        callback.data,
        "buy",
    )

    if not values:
        await safe_answer(
            callback,
            "❌ Invalid service.",
            show_alert=True,
        )
        return

    service = values[0].strip().upper()

    # 🔥 ডাটাবেস থেকে স্টক এবং গত ১০ মিনিটের লাইভ ট্রাফিক চেক
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        # ১. শুধুমাত্র 0 এর থেকে বেশি স্টক আছে এমন কান্ট্রিগুলো বের করা
        cursor = await db.execute("""
            SELECT country, COUNT(phone_number) as stock_count 
            FROM numbers_pool 
            WHERE UPPER(service) = ? 
            AND (assigned_to = 0 OR assigned_to IS NULL)
            GROUP BY UPPER(country)
            HAVING stock_count > 0
            ORDER BY country ASC
        """, (service,))
        country_rows = await cursor.fetchall()

        # ২. 🕒 গত ১০ মিনিটে কোন কান্ট্রিগুলোতে নতুন OTP এসেছে সেটা চেক করা হচ্ছে
        cursor_traffic = await db.execute("""
            SELECT DISTINCT UPPER(n.country) 
            FROM otp_history o
            JOIN numbers_pool n ON o.phone_number = n.phone_number
            WHERE UPPER(o.service) = ? AND datetime(o.timestamp) >= datetime('now', '-10 minute')
        """, (service,))
        traffic_rows = await cursor_traffic.fetchall()
        
        # ট্রাফিক থাকা কান্ট্রিগুলোর লিস্ট
        active_traffic_countries = {str(row[0]).strip() for row in traffic_rows}

    normal = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    premium = "𝐀𝐁𝐂𝐃𝐄𝐅𝐆𝐇𝐈𝐉𝐊𝐋𝐌𝐍𝐎𝐏𝐐𝐑𝐒𝐓𝐔𝐕𝗪𝐗𝐘𝐙𝐚𝐛𝐜𝐝𝐞𝐟𝐠𝐡𝗶𝐣𝗸𝗹𝗺𝗻𝐨𝐩𝐪𝐫𝐬𝐭𝐮𝘃𝘄𝘅𝘆𝘇"
    premium_service = service.translate(str.maketrans(normal, premium))

    if not country_rows:
        await safe_edit(
            callback.message,
            (
                f'<tg-emoji emoji-id="5420323339723881652">⚠️</tg-emoji> <b>OUT OF STOCK</b>\n\n'
                f"No stock available for "
                f"<b>{premium_service}</b>."
            ),
        )

        await safe_answer(
            callback,
            "No stock available.",
            show_alert=True,
        )
        return

    rows = []
    current_row = []

    for row in country_rows:
        country_name = str(row["country"]).strip()
        stock = int(row["stock_count"])
        
        c_upper = country_name.upper()
        premium_country = c_upper.translate(str.maketrans(normal, premium))

        # 🔥 আল্টিমেট ডিসিশন মেকার: গত ১০ মিনিটে ট্রাফিক থাকলে সবুজ (success), না থাকলে নীল (primary)
        if c_upper in active_traffic_countries:
            btn_style = "success"
        else:
            btn_style = "primary"

        btn = ib(
            f" {premium_country} ({stock})",
            callback_data=pack_callback(
                "country",
                service,
                country_name,
            ),
            style=btn_style,
            emoji_id=get_country_custom_emoji_id(country_name),
        )
        
        current_r

