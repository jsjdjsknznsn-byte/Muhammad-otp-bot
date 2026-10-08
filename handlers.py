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
            cursor = await db.execute(
                "SELECT * FROM users WHERE user_id = ?",
                (user.id,)
            )
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

                await event.answer(
                    "🚫 You are permanently BANNED! Only Support is allowed.",
                    show_alert=True
                )
                return

            elif isinstance(event, types.Message):
                if event.text and "/start" in event.text:
                    pass # Start অ্যালাউ করা হলো যাতে সাপোর্ট বাটন দেখতে পায়
                else:
                    await event.answer(
                        "🚫 You are permanently BANNED from using this bot. Contact Support."
                    )
                    return
                    
        return await handler(event, data)


# 🔥 গ্লোবাল লক চালু
router.message.middleware(GlobalBanMiddleware())
router.callback_query.middleware(GlobalBanMiddleware())


# 🔥 Notice Handler একদম ওপরে রাখা হলো যাতে অন্য কেউ ক্যাচ না করে
@router.message(AdminNoticeState.waiting_for_message)
async def process_sys_notice_send(
    message: types.Message,
    state: FSMContext
):
    if message.text and message.text.lower() == "/cancel":
        await state.clear()
        return await message.reply("Action cancelled.")
        
    data = await state.get_data()
    target_id = data.get("target_user_id")
    
    notice_text = (
        f'<tg-emoji emoji-id="5420323339723881652">⚠️</tg-emoji> '
        f'<b>Message from Admin:</b>\n\n'
        f'{message.html_text}'
    )
    
    try:
        await message.bot.send_message(
            chat_id=target_id,
            text=notice_text
        )

        await message.reply(
            f"✅ Notice sent successfully to user {target_id}."
        )

    except Exception:
        await message.reply(
            "❌ Failed to send notice. User might have blocked the bot."
        )
        
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


# =========================================================
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
    service_data = SERVICE_EMOJIS.get(
        lower_s,
        SERVICE_EMOJIS["default"]
    )

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

    return text.translate(
        str.maketrans(normal, bold)
    )


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
 if not callback.from_user:
        return False

    user_id = callback.from_user.id

    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                """
                SELECT is_admin
                FROM users
                WHERE user_id = ?
                """,
                (user_id,)
            )

            row = await cursor.fetchone()

        if row and row[0]:
            return True

    except Exception:
        logger.exception("Admin check failed")

    await safe_answer(
        callback,
        "🚫 Admin access required.",
        show_alert=True,
    )

    return False


# =========================================================
# SERVICE / COUNTRY HELPERS
# =========================================================

async def get_available_services():
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row

            async with db.execute(
                """
                SELECT *
                FROM services
                ORDER BY id ASC
                """
            ) as cursor:
                rows = await cursor.fetchall()

        return rows

    except Exception:
        logger.exception(
            "Failed to load services"
        )
        return []


async def get_available_countries(
    service_name: str,
):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row

            async with db.execute(
                """
                SELECT DISTINCT country
                FROM numbers
                WHERE service = ?
                  AND status = 'available'
                ORDER BY country ASC
                """,
                (service_name,)
            ) as cursor:
                rows = await cursor.fetchall()

        return [
            row["country"]
            for row in rows
            if row["country"]
        ]

    except Exception:
        logger.exception(
            "Failed to load countries"
        )
        return []


# =========================================================
# SERVICE KEYBOARD
# =========================================================

def service_selection_keyboard(
    services,
) -> InlineKeyboardMarkup:

    rows = []
    current_row = []

    for service in services:
        try:
            service_name = (
                service["name"]
                if isinstance(service, dict)
                else service["service"]
            )
        except Exception:
            service_name = str(service)

        service_name = str(
            service_name
        ).strip()

        if not service_name:
            continue

        emoji_id = get_service_custom_emoji_id(
            service_name
        )

        current_row.append(
            ib(
                service_name.upper(),
                callback_data=pack_callback(
                    "svc",
                    service_name,
                ),
                style="primary",
                emoji_id=emoji_id,
            )
        )

        if len(current_row) == 2:
            rows.append(current_row)
            current_row = []

    if current_row:
        rows.append(current_row)

    rows.append(
        [
            ib(
                "↩️ BACK",
                callback_data="back_main",
                style="primary",
                emoji_id=E_BACK,
            )
        ]
    )

    return InlineKeyboardMarkup(
        inline_keyboard=rows
    )


# =========================================================
# COUNTRY KEYBOARD
# =========================================================

def country_selection_keyboard(
    countries,
    service_name: str,
) -> InlineKeyboardMarkup:

    rows = []
    current_row = []

    for country in countries:

        country_name = str(
            country
        ).strip()

        if not country_name:
            continue

        emoji_id = get_country_custom_emoji_id(
            country_name
        )

        current_row.append(
            ib(
                country_name.upper(),
                callback_data=pack_callback(
                    "country",
                    service_name,
                    country_name,
                ),
                style="primary",
                emoji_id=emoji_id,
            )
        )

        if len(current_row) == 2:
            rows.append(current_row)
            current_row = []

    if current_row:
        rows.append(current_row)

    rows.append(
        [
            ib(
                "↩️ BACK",
                callback_data="get_number",
                style="primary",
                emoji_id=E_BACK,
            )
        ]
    )

    return InlineKeyboardMarkup(
        inline_keyboard=rows
    )


# =========================================================
# NUMBER DISPLAY
# =========================================================

def format_number_for_user(
    phone: str,
    country: str,
    remove_cc: bool = True,
) -> str:

    if not phone:
        return ""

    if remove_cc:
        return extract_pure_number_without_cc(
            phone,
            country,
        )

    return str(phone)


def number_info_text(
    phone: str,
    country: str,
    service: str,
    rate: Any = None,
    remove_cc: bool = True,
) -> str:

    display_number = format_number_for_user(
        phone,
        country,
        remove_cc=remove_cc,
    )

    service_emoji = format_p_emo(
        get_service_custom_emoji_id(service),
        "📱",
    )

    country_emoji = format_p_emo(
        get_country_custom_emoji_id(country),
        "🌍",
    )

    text = (
        f"{service_emoji} <b>Service:</b> "
        f"{service}\n"
        f"{country_emoji} <b>Country:</b> "
        f"{country}\n\n"
        f"📱 <b>Number:</b> "
        f"<code>{display_number}</code>"
    )

    if rate is not None:
        text += (
            f"\n💰 <b>Rate:</b> "
            f"{rate}"
        )

    return text


# =========================================================
# REMOVE COUNTRY CODE BUTTON
# =========================================================

def cc_toggle_keyboard(
    enabled: bool = True,
):

    status = "ON ✅" if enabled else "OFF ❌"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                ib(
                    f"Remove CC: {status}",
                    callback_data="toggle_cc",
                    style="primary",
                    emoji_id=E_CC,
                )
            ],
            [
                ib(
                    "↩️ BACK",
                    callback_data="back_main",
                    style="primary",
                    emoji_id=E_BACK,
                )
            ],
        ]
    )


# =========================================================
# NUMBER REQUEST
# =========================================================

async def reserve_number(
    user_id: int,
    service_name: str,
    country_name: str,
):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row

            cursor = await db.execute(
                """
                SELECT *
                FROM numbers
                WHERE service = ?
                  AND country = ?
                  AND status = 'available'
                ORDER BY id ASC
                LIMIT 1
                """,
                (
                    service_name,
                    country_name,
                )
            )

            row = await cursor.fetchone()

            if not row:
                return None

            number_id = row["id"]

            await db.execute(
                """
                UPDATE numbers
                SET status = 'active',
                    user_id = ?,
                    assigned_at = CURRENT_TIMESTAMP
                WHERE id = ?
                  AND status = 'available'
                """,
                (
                    user_id,
                    number_id,
                )
            )

            await db.commit()

            return dict(row)

    except Exception:
        logger.exception(
            "Failed to reserve number"
        )
        return None


# =========================================================
# ACTIVE NUMBER CHECK
# =========================================================

async def get_user_active_numbers(
    user_id: int,
):

    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row

            async with db.execute(
                """
                SELECT *
                FROM numbers
                WHERE user_id = ?
                  AND status = 'active'
                ORDER BY id DESC
                """,
                (user_id,)
            ) as cursor:
                rows = await cursor.fetchall()

        return rows

    except Exception:
        logger.exception(
            "Failed to get active numbers"
        )
        return []


# =========================================================
# NUMBER STATUS
# =========================================================

async def get_number_status(
    number_id: int,
):

    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row

            async with db.execute(
                """
                SELECT *
                FROM numbers
                WHERE id = ?
                LIMIT 1
                """,
                (number_id,)
            ) as cursor:

                row = await cursor.fetchone()

        return row

    except Exception:
        logger.exception(
            "Failed to get number status"
        )
        return None
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
    premium = "𝐀𝐁𝐂𝐃𝐄𝐅𝐆𝐇𝐈𝐉𝐊𝐋𝐌𝐍𝐎𝐏𝐐𝐑𝐒𝐓𝐔𝐕𝗪𝐗𝐘𝐙𝐚𝐛𝐜𝐝𝐞𝐟𝐠𝐡𝗶𝐣𝗸𝗹𝐦𝐧𝐨𝐩𝐪𝐫𝐬𝐭𝐮𝘃𝘄𝘅𝘆𝘇"
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
    premium = "𝐀𝐁𝐂𝐃𝐄𝐅𝐆𝐇𝐈𝐉𝐊𝐋𝐌𝐍𝐎𝐏𝐐𝐑𝐒𝐓𝐔𝐕𝗪𝐗𝐘𝐙𝐚𝐛𝐜𝐝𝐞𝐟𝐠𝐡𝗶𝐣𝗸𝐥𝐦𝐧𝐨𝐩𝐪𝐫𝐬𝐭𝐮𝘃𝘄𝘅𝘆𝘇"
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
        
        current_row.append(btn)

        if len(current_row) == 2:
            rows.append(current_row)
            current_row = []

    if current_row:
        rows.append(current_row)

    # 🔥 শুধুমাত্র মেইন মেনুতে যাওয়ার ব্যাক বাটন (রিফ্রেশ বাটন গায়েব)
    rows.append(
        [
            ib(
                " Back",
                callback_data="menu:main",
                style="primary",
                emoji_id=E_BACK,
            )
        ]
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=rows
    )

    try:
        s_emo_id = get_service_custom_emoji_id(service)
        s_emo = f'<tg-emoji emoji-id="{s_emo_id}">💬</tg-emoji>'
    except Exception:
        s_emo = '💬'

    await safe_edit(
        callback.message,
        (
            f'<tg-emoji emoji-id="5409048419211682843">💠</tg-emoji> <b>Service:</b> {s_emo} <b>{premium_service}</b>\n\n'
            f'<b>Select a country from available stock:</b>'
        ),
        keyboard,
    )

    await safe_answer(callback)

@router.callback_query(
    F.data.startswith("country:")
)
async def process_allocation_final(
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

    values = unpack_callback(
        callback.data,
        "country",
    )

    if len(values) != 2:
        await safe_answer(
            callback,
            " Invalid country selection.",
 if len(values) != 2:
        await safe_answer(
            callback,
            " Invalid country selection.",
            show_alert=True,
        )
        return

    service = values[0].strip().upper()
    country = values[1].strip()

    categories = await db_mgr.get_categories()

    cat_spec = next(
        (
            c
            for c in categories
            if str(c["name"]).upper()
            == service
        ),
        None,
    )

    if not cat_spec:
        await safe_answer(
            callback,
            "❌ Service configuration unavailable.",
            show_alert=True,
        )
        return

    await safe_answer(
        callback,
        "⏳ Allocating number...",
    )

    allocated = (
        await db_mgr.allocate_numbers_to_user(
            callback.from_user.id,
            service,
            country,
            cat_spec["nums_per_user"],
        )
    )

    if not allocated:
        await safe_edit(
            callback.message,
            (
                f" <b>OUT OF STOCK</b>\n\n"
                f"No numbers left for "
                f"<b>{service}</b> "
                f"({country})."
            ),
        )
        return

    await show_allocated_numbers(
        callback.message,
        service,
        country,
        allocated,
    )


@router.callback_query(
    F.data.startswith("change:")
)
async def process_change_number(
    callback: types.CallbackQuery,
):
    if not await verify_dual_membership(
        callback.bot,
        callback.from_user.id,
    ):
        await deny_access(
            callback.bot,
            callback.from_user.id,
        )
        return await safe_answer(
            callback,
            " Access denied.",
            show_alert=True,
        )

    # 🔥 Database Columns Auto-Migration (Ultra Safe - Separate Blocks)
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute(
                "ALTER TABLE users ADD COLUMN is_banned INTEGER DEFAULT 0"
            )
        except Exception:
            pass

        try:
            # wasted_count কে এখন আমরা Spam Click Tracker হিসেবে ইউজ করবো
            await db.execute(
                "ALTER TABLE users ADD COLUMN wasted_count INTEGER DEFAULT 0"
            )
        except Exception:
            pass

        try:
            await db.execute(
                "ALTER TABLE users ADD COLUMN last_number_time REAL DEFAULT 0"
            )
        except Exception:
            pass
        
        await db.commit()
        
        db.row_factory = aiosqlite.Row

        cursor = await db.execute(
            "SELECT * FROM users WHERE user_id = ?",
            (callback.from_user.id,)
        )

        user_data = await cursor.fetchone()

    user_dict = dict(user_data) if user_data else {}

    # 🚫 Ban Check First
    if user_dict.get('is_banned', 0):
        return await safe_answer(
            callback,
            "🚫 You are permanently BANNED for abusing the system!",
            show_alert=True
        )

    # ⏱️ 15-Second Cooldown & 5-Click Spam Check
    current_time = time.time()
    last_time = user_dict.get(
        'last_number_time',
        0
    )

    if not last_time:
        last_time = 0
        
    time_diff = current_time - float(last_time)

    spam_count = user_dict.get(
        'wasted_count',
        0
    )

    if not spam_count:
        spam_count = 0

    if time_diff < 15.0:
        spam_count += 1
        
        if spam_count >= 5:
            # 🛑 5 বার স্প্যাম ক্লিক করলেই ডাইরেক্ট পার্মানেন্ট ব্যান
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute(
                    "UPDATE users SET is_banned = 1, wasted_count = ? WHERE user_id = ?",
                    (
                        spam_count,
                        callback.from_user.id
                    )
                )
                await db.commit()
                
            # Notify Admins
            normal_chars = (
                "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
                "abcdefghijklmnopqrstuvwxyz"
                "0123456789"
            )

            premium_chars = (
                "𝐀𝐁𝐂𝐃𝐄𝐅𝐆𝐇𝐈𝐉𝐊𝐋𝐌𝐍𝐎𝐏𝐐𝐑𝐒𝐓𝐔𝐕"
                "𝐖𝐗𝐘𝐙"
                "𝐚𝐛𝐜𝐝𝐞𝐟𝐠𝐡𝐢𝐣𝐤𝐥𝐦𝐧𝐨𝐩𝐪𝐫𝐬𝐭𝐮𝐯"
                "𝐰𝐱𝐲𝐳"
                "𝟎𝟏𝟐𝟑𝟒𝟓𝟔𝟕𝟖𝟗"
            )

            font_map = str.maketrans(
                normal_chars,
                premium_chars
            )
            
            username = (
                f"@{callback.from_user.username}"
                if callback.from_user.username
                else "No Username"
            )

            u_name = callback.from_user.first_name
            
            alert_text = (
                f'<tg-emoji emoji-id="5420323339723881652">⚠️</tg-emoji> '
                f'<b>{"SPAM ABUSE DETECTED".translate(font_map)}</b>\n\n'
                f'{"This user has been permanently banned for button spamming".translate(font_map)}.\n\n'
                f'<tg-emoji emoji-id="5453957997418004470">👤</tg-emoji> '
                f'{"Name".translate(font_map)}: '
                f'<b>{str(u_name).translate(font_map)}</b>\n'
                f'<tg-emoji emoji-id="5354972242629383937">🆔</tg-emoji> '
                f'{"UID".translate(font_map)}: '
                f'<code>{str(callback.from_user.id).translate(font_map)}</code>\n'
                f'<tg-emoji emoji-id="6275857834127134596">🔗</tg-emoji> '
                f'{"Username".translate(font_map)}: '
                f'{username.translate(font_map)}'
            )
            
            admin_kb = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        ib(
                            "Unban User".translate(font_map),
                            callback_data=f"sys_unban:{callback.from_user.id}",
                            style="success",
                            emoji_id="5472250091332993630"
                        ),
                        ib(
                            "Notice User".translate(font_map),
                            callback_data=f"sys_notice:{callback.from_user.id}",
                            style="primary",
                            emoji_id="6269532506941298061"
                        )
                    ]
                ]
            )
            
            admins = (
                await db_mgr.get_admins()
                if hasattr(db_mgr, 'get_admins')
                else []
            )

            for admin_id in admins:
                try:
                    await callback.bot.send_message(
                        chat_id=admin_id,
                        text=alert_text,
                        reply_markup=admin_kb
                    )
                except Exception:
                    pass

            return await safe_answer(
                callback,
                "🚫 BANNED: You spammed the button too many times!",
                show_alert=True
            )
            
        else:
            # স্প্যাম কাউন্ট আপডেট করে ওয়ার্নিং দেওয়া হচ্ছে
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute(
                    "UPDATE users SET wasted_count = ? WHERE user_id = ?",
                    (
                        spam_count,
                        callback.from_user.id
                    )
                )
                await db.commit()
                
            wait_time = int(
                15 - time_diff
            )

            return await safe_answer(
                callback,
                f"⚠️ Please wait {wait_time}s! "
                f"Spamming will get you banned "
                f"({spam_count}/5)",
                show_alert=True
            )

    # ⏳ ১৫ সেকেন্ড পার হয়ে গেলে নরমাল চেঞ্জ অ্যাকসেপ্ট হবে এবং স্প্যাম কাউন্ট জিরো হয়ে যাবে
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET last_number_time = ?, wasted_count = 0 WHERE user_id = ?",
            (
                current_time,
                callback.from_user.id
            )
        )
        await db.commit()

    # Original Allocation Logic
    values = unpack_callback(
        callback.data,
        "change",
    )

    if len(values) != 2:
        return await safe_answer(
            callback,
            " Invalid request.",
            show_alert=True
        )

    service = values[0].strip().upper()
    country = values[1].strip()

    await safe_answer(
        callback,
        " Changing number..."
    )

    try:
        await db_mgr.clear_user_numbers(
            callback.from_user.id,
            service,
        )
    except Exception:
        pass

    categories = await db_mgr.get_categories()

    cat_spec = next(
        (
            c
            for c in categories
            if str(c["name"]).upper()
            == service
        ),
        None
    )

    if not cat_spec:
        return await safe_edit(
            callback.message,
            " Selected service is unavailable."
        )

    allocated = await db_mgr.allocate_numbers_to_user(
        callback.from_user.id,
        service,
        country,
        cat_spec["nums_per_user"],
    )

    if not allocated:
        return await safe_edit(
            callback.message,
            f" <b>OUT OF STOCK</b>\n\n"
            f"No numbers left for "
            f"{service} ({country})."
        )

    await show_allocated_numbers(
        callback.message,
        service,
        country,
        allocated,
    )


@router.callback_query(
    F.data.startswith("cc:")
)
async def user_toggle_cc(
    callback: types.CallbackQuery,
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

    values = unpack_callback(
        callback.data,
        "cc",
    )

    if len(values) != 2:
        await safe_answer(
            callback,
            " Invalid request.",
            show_alert=True,
        )
        return

    service = values[0].strip().upper()
    country = values[1].strip()

    new_status = await db_mgr.toggle_config(
        "remove_cc"
    )

    categories = await db_mgr.get_categories()

    cat_spec = next(
        (
            c
            for c in categories
            if str(c["name"]).upper()
            == service
        ),
        None
    )

    quota = (
        cat_spec["nums_per_user"]
        if cat_spec
        else None
    )

    async with aiosqlite.connect(DB_PATH) as db:

        db.row_factory = aiosqlite.Row

        query = """
            SELECT phone_number
            FROM numbers_pool
            WHERE assigned_to = ?
              AND service = ?
              AND UPPER(country) = UPPER(?)
            ORDER BY assigned_at DESC
        """

        params = [
            callback.from_user.id,
            service,
            country,
        ]

        if quota:
            query += " LIMIT ?"
            params.append(quota)

        async with db.execute(
            query,
            params,
        ) as cursor:

            rows = await cursor.fetchall()

    allocated = [
        row["phone_number"]
        for row in rows
    ]

    if not allocated:
        await safe_answer(
            callback,
            "No active number session found.",
            show_alert=True,
        )
        return

    await safe_edit(
        callback.message,
        number_result_text(
            service,
            country,
        ),
        number_result_keyboard(
            service,
            country,
            allocated,
            new_status,
        ),
    )

    await safe_answer(
        callback,
        f"Remove CC is now {new_status}.",
    )


# 🔥 নতুন ক্লোজ/হোম হ্যান্ডলার (ব্যাক দিলে এই মেসেজটা আসবে)
@router.callback_query(
    F.data == "menu:close"
)
async def callback_menu_close(
    callback: types.CallbackQuery,
    state: FSMContext
):
    await state.clear()

    await safe_edit(
        callback.message,
        (
            f"{SYS_EMOJI} "
            f"<b>Action cancelled.</b>\n\n"
            f"Please use the menu buttons below."
        )
    )

    await safe_answer(callback)


# 🔥 আপনার আপডেট করা ওয়ালেট সেট ফাংশন
@router.callback_query(
    F.data == "wallet:set"
)
async def user_req_set_wallet(
    callback: types.CallbackQuery,
    state: FSMContext
):

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                ib(
                    " Bkash",
                    callback_data="wallet:bkash",
                    style="primary",
                    emoji_id="5348469219761626211",
                ),
                ib(
                    " Nagad",
                    callback_data="wallet:nagad",
                    style="primary",
                    emoji_id="6147706485439730700",
                ),
            ],
            [
                ib(
                    " Rocket",
                    callback_data="wallet:rocket",
                    style="primary",
                    emoji_id="5346042941196507141",
                ),
                ib(
                    " Binance",
                    callback_data="wallet:binance",
                    style="primary",
                    emoji_id="5348212415077064131",
                ),
            ],
            [
                # 🔥 ম্যাজিক! ব্যাক বাটন এখন "menu:close" এ যাবে
                ib(
                    " Back",
                    callback_data="menu:close",
                    style="primary",
                    emoji_id=E_BACK,
                )
            ],
        ]
    )

    await safe_edit(
        callback.message,
        (
            f"{SYS_EMOJI}  "
            f"<b>Choose Wallet Provider</b>"
        ),
        keyboard,
    )

    await safe_answer(callback)


@router.callback_query(
    F.data.startswith("wallet:")
)
async def user_select_wallet_provider(
    callback: types.CallbackQuery,
    state: FSMContext
):

    method = callback.data.split(
        ":",
        1,
    )[1]

    if method == "view":
        await safe_answer(callback)
        return

    method = method.title()

    await state.update_data(
        wallet_type=method
    )

    await state.set_state(
        Form.waiting_for_set_wallet_number
    )

    if method in {
        "Bkash",
        "Nagad",
        "Rocket",
    }:
        prompt = (
            f" Send your "
            f"<b>{method}</b> number:"
        )
    else:
        prompt = (
            f" Send your "
            f"<b>{method}</b> Pay ID "
        )

    await send_msg(
        callback.bot,
        callback.from_user.id,
        (
            f"{SYS_EMOJI}  {prompt}\n\n"
            f"Send <b>/cancel</b> to stop."
        ),
    )

    await safe_answer(callback)


@router.callback_query(
    F.data == "withdraw:start"
)
async def user_start_withdraw_flow(
    callback: types.CallbackQuery,
    state: FSMContext
):

    await state.clear()

    withdraw_status = await db_mgr.get_config(
        "withdraw_enabled"
    )

    if str(withdraw_status).upper() == "OFF":
        await safe_answer(
            callback,
            " Withdraw is disabled by admin.",
            show_alert=True,
        )
        return

    user = await db_mgr.get_user(
        callback.from_user.id
    )

    if not user:
        await safe_answer(
            callback,
            " User account not found.",
            show_alert=True,
        )
        return