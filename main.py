import asyncio
import logging
import aiosqlite
import re
import time
import html
from handlers import SERVICE_EMOJIS, format_p_emo, get_service_custom_emoji_id
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from langdetect import detect, LangDetectException

from config import BOT_TOKEN, BOT_TOKEN_2, BOT_TOKEN_3, OTP_GROUP_ID, DB_PATH, UPDATE_CHANNEL_LINK, SYS_EMOJI
import handlers
from database import db_mgr, GLOBAL_COUNTRY_MAP

logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s")
logger = logging.getLogger("CombinedBotEngine")

# Master Singular Bot System Instance
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
bot2 = Bot(token=BOT_TOKEN_2, default=DefaultBotProperties(parse_mode="HTML"))
bot3 = Bot(token=BOT_TOKEN_3, default=DefaultBotProperties(parse_mode="HTML"))

dp = Dispatcher()
dp.include_router(handlers.router)

# 🔥 Load Balancer Array & Index Tracker
group_bots = [bot2, bot3]
current_bot_idx = 0


def extract_pure_number_without_cc(phone: str, country: str) -> str:
    try:
        clean = re.sub(r'\D', '', phone)
        for prefix in sorted(GLOBAL_COUNTRY_MAP.keys(), key=lambda x: len(str(x)), reverse=True):
            if GLOBAL_COUNTRY_MAP[prefix].upper() == country.upper() and clean.startswith(str(prefix)):
                return clean[len(str(prefix)):]
        return clean
    except Exception:
        return phone


# ==========================================
# COUNTRY SHORT CODES
# ==========================================
COUNTRY_SHORT_CODES ={
  "AFGHANISTAN": "AF", "ALBANIA": "AL", "ALGERIA": "DZ", "ANDORRA": "AD", "ANGOLA": "AO",
  "ANTIGUA_BARBUDA": "AG", "ARGENTINA": "AR", "ARMENIA": "AM", "AUSTRALIA": "AU", "AUSTRIA": "AT",
  "AZERBAIJAN": "AZ", "BAHAMAS": "BS", "BAHRAIN": "BH", "BANGLADESH": "BD", "BARBADOS": "BB",
  "BELARUS": "BY", "BELGIUM": "BE", "BELIZE": "BZ", "BENIN": "BJ", "BHUTAN": "BT",
  "BOLIVIA": "BO", "BOSNIA_HERZEGOVINA": "BA", "BOTSWANA": "BW", "BRAZIL": "BR", "BRUNEI": "BN",
  "BULGARIA": "BG", "BURKINA_FASO": "BF", "BURUNDI": "BI", "CAMBODIA": "KH", "CAMEROON": "CM",
  "CANADA": "CA", "CAPE_VERDE": "CV", "CENTRAL_AFRICAN_REPUBLIC": "CF", "CHAD": "TD", "CHILE": "CL",
  "CHINA": "CN", "COLOMBIA": "CO", "COMOROS": "KM", "CONGO": "CG", "CONGO_DR": "CD",
  "COSTA_RICA": "CR", "CROATIA": "HR", "CUBA": "CU", "CYPRUS": "CY", "CZECH_REPUBLIC": "CZ",
  "DENMARK": "DK", "DJIBOUTI": "DJ", "DOMINICA": "DM", "DOMINICAN_REPUBLIC": "DO", "ECUADOR": "EC",
  "EGYPT": "EG", "EL_SALVADOR": "SV", "EQUATORIAL_GUINEA": "GQ", "ERITREA": "ER", "ESTONIA": "EE",
  "ESWATINI": "SZ", "ETHIOPIA": "ET", "FIJI": "FJ", "FINLAND": "FI", "FRANCE": "FR",
  "GABON": "GA", "GAMBIA": "GM", "GEORGIA": "GE", "GERMANY": "DE", "GHANA": "GH",
  "GREECE": "GR", "GRENADA": "GD", "GUATEMALA": "GT", "GUINEA": "GN", "GUINEA_BISSAU": "GW",
  "GUYANA": "GY", "HAITI": "HT", "HONDURAS": "HN", "HUNGARY": "HU", "ICELAND": "IS",
  "INDIA": "IN", "INDONESIA": "ID", "IRAN": "IR", "IRAQ": "IQ", "IRELAND": "IE",
  "ISRAEL": "IL", "ITALY": "IT", "IVORY_COAST": "CI", "JAMAICA": "JM", "JAPAN": "JP",
  "JORDAN": "JO", "KAZAKHSTAN": "KZ", "KENYA": "KE", "KIRIBATI": "KI", "KOSOVO": "XK",
  "KUWAIT": "KW", "KYRGYZSTAN": "KG", "LAOS": "LA", "LATVIA": "LV", "LEBANON": "LB",
  "LESOTHO": "LS", "LIBERIA": "LR", "LIBYA": "LY", "LIECHTENSTEIN": "LI", "LITHUANIA": "LT",
  "LUXEMBOURG": "LU", "MADAGASCAR": "MG", "MALAWI": "MW", "MALAYSIA": "MY", "MALDIVES": "MV",
  "MALI": "ML", "MALTA": "MT", "MARSHALL_ISLANDS": "MH", "MAURITANIA": "MR", "MAURITIUS": "MU",
  "MEXICO": "MX", "MICRONESIA": "FM", "MOLDOVA": "MD", "MONACO": "MC", "MONGOLIA": "MN",
  "MONTENEGRO": "ME", "MOROCCO": "MA", "MOZAMBIQUE": "MZ", "MYANMAR": "MM", "NAMIBIA": "NA",
  "NAURU": "NR", "NEPAL": "NP", "NETHERLANDS_1": "NL", "NEW_ZEALAND": "NZ", "NICARAGUA": "NI",
  "NIGER": "NE", "NIGERIA": "NG", "NORTH_KOREA": "KP", "NORTH_MACEDONIA": "MK", "NORWAY": "NO",
  "OMAN": "OM", "PAKISTAN": "PK", "PALAU": "PW", "PALESTINE": "PS", "PANAMA": "PA",
  "PAPUA_NEW_GUINEA": "PG", "PARAGUAY": "PY", "PERU": "PE", "PHILIPPINES": "PH", "POLAND": "PL",
  "PORTUGAL": "PT", "QATAR": "QA", "ROMANIA": "RO", "RUSSIA": "RU", "RWANDA": "RW",
  "SAINT_KITTS_NEVIS": "KN", "SAINT_LUCIA": "LC", "SAINT_VINCENT_GRENADINES": "VC", "SAMOA": "WS",
  "SAN_MARINO": "SM", "SAO_TOME_PRINCIPE": "ST", "SAUDI_ARABIA": "SA", "SENEGAL": "SN",
  "SERBIA": "RS", "SEYCHELLES": "SC", "SIERRA_LEONE": "SL", "SINGAPORE": "SG", "SLOVAKIA": "SK",
  "SLOVENIA": "SI", "SOLOMON_ISLANDS": "SB", "SOMALIA": "SO", "SOUTH_AFRICA": "ZA", "SOUTH_KOREA": "KR",
  "SOUTH_SUDAN": "SS", "SPAIN": "ES", "SRI LANKA": "LK", "SUDAN": "SD", "SURINAME": "SR",
  "SWEDEN": "SE", "SWITZERLAND": "CH", "SYRIA": "SY", "TAIWAN": "TW", "TAJIKISTAN": "TJ",
  "TANZANIA": "TZ", "THAILAND": "TH", "TIMOR LESTE": "TL", "TOGO": "TG", "TONGA": "TO",
  "TRINIDAD_TOBAGO": "TT", "TUNISIA": "TN", "TURKEY": "TR", "TURKMENISTAN": "TM", "TUVALU": "TV",
  "UAE": "AE", "UGANDA": "UG", "UKRAINE": "UA", "USA": "US", "URUGUAY": "UY",
  "UZBEKISTAN": "UZ", "VANUATU": "VU", "VATICAN": "VA", "VENEZUELA": "VE", "VIETNAM": "VN",
  "WESTERN SAHARA": "EH", "YEMEN": "YE", "ZAMBIA": "ZM", "ZIMBABWE": "ZW"
}

def get_short_country(country_name):
    # 🔥 FIX: 'SUDAN 1' বা 'SUDAN 2' থেকে পেছনের নাম্বার কেটে শুধু মেইন নামটা বের করে শর্ট কোড মেলাবে
    base_name = re.sub(r'\s*\d+$', '', str(country_name)).strip().upper()
    return COUNTRY_SHORT_CODES.get(base_name, base_name[:2])
# ==========================================

import hashlib
async def bullet_speed_engine():
    await asyncio.sleep(1)
    logger.info("🚀 Bullet Speed Memory Engine Started!")
    
    while True:
        try:
            from api import api_client
            otps = await api_client.get_success_otps()
            
            if not otps:
                await asyncio.sleep(0.5)
                continue

            try:
                cc_mode = await db_mgr.get_config("remove_cc")
            except Exception:
                cc_mode = "OFF"
                
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute("CREATE TABLE IF NOT EXISTS file_rates (country_batch TEXT, service TEXT, rate REAL, PRIMARY KEY(country_batch, service))")

            for otp in otps:
                raw_num = str(otp.get("num") or otp.get("number") or "").strip().replace("+", "")
                incoming_service = str(otp.get("cli") or otp.get("service") or "UNKNOWN").upper().strip()
                msg = str(otp.get("message") or otp.get("sms") or "").strip()
                dt_stamp = str(otp.get("dt") or otp.get("date") or "").strip()
                
                if not raw_num or not msg: continue
                
                unique_seed = f"{dt_stamp}_{raw_num}_{msg}"
                otp_id = hashlib.md5(unique_seed.encode("utf-8")).hexdigest()
                
                search_num = raw_num[-7:] if len(raw_num) >= 7 else raw_num
                
                # 🔥 ডেটাবেস রিড করার জন্য সাময়িক কানেকশন (ডেডলক এড়ানোর জন্য)
                async with aiosqlite.connect(DB_PATH) as db:
                    db.row_factory = aiosqlite.Row
                    async with db.execute("SELECT * FROM numbers_pool WHERE phone_number = ? OR phone_number LIKE '%' || ? ORDER BY assigned_at DESC LIMIT 1", (raw_num, search_num)) as cursor:
                        number_record = await cursor.fetchone()
                        
                    user_id = number_record['assigned_to'] if number_record else None
                    country_name = str(number_record['country']).strip().upper() if number_record else "UNKNOWN"
                    assigned_service = str(number_record['service']).strip().upper() if number_record else incoming_service
                    
                    if country_name == "UNKNOWN":
                        for prefix in sorted(GLOBAL_COUNTRY_MAP.keys(), key=lambda x: len(str(x)), reverse=True):
                            if raw_num.startswith(str(prefix)):
                                country_name = str(GLOBAL_COUNTRY_MAP[prefix]).strip().upper()
                                break

                    async with db.execute("SELECT rate FROM file_rates WHERE UPPER(country_batch) = ? AND UPPER(service) = ?", (country_name.upper(), assigned_service.upper())) as cursor:
                        file_rate_record = await cursor.fetchone()
                        
                    if file_rate_record:
                        reward = float(file_rate_record['rate'])
                    else:
                        async with db.execute("SELECT * FROM categories WHERE UPPER(name) = ?", (assigned_service,)) as cursor:
                            cat_record = await cursor.fetchone()
                        reward = float(cat_record['rate_per_otp']) if cat_record else 0.0

                # 🔥 এখানে কানেকশন সেফ, তাই db_mgr সেভ করতে পারবে, আর ক্র্যাশ করবে না!
                is_new = await db_mgr.log_otp(otp_id, raw_num, user_id or 0, assigned_service, reward)
                if not is_new: continue 
                
                match = re.search(r'(?<!\d)(?:\d{4,8}|\d{12})(?!\d)', msg)
                if not match: match = re.search(r'(?<!\d)\d{3}-\d{3}(?!\d)', msg)
                display_otp = match.group(0) if match else "Copy SMS"
                copy_payload = match.group(0) if match else msg
                
                try: c_emoji = f'<tg-emoji emoji-id="{handlers.get_country_custom_emoji_id(country_name)}">🌍</tg-emoji>'
                except: c_emoji = '🌍'
                try: s_emoji = f'<tg-emoji emoji-id="{get_service_custom_emoji_id(assigned_service)}">💬</tg-emoji>'
                except: s_emoji = '💬'
                
                if user_id and int(user_id) > 0:
                    await db_mgr.update_user_balance(int(user_id), reward)
                    await db_mgr.increment_user_otp_stats(int(user_id))
                    
                    user_data = await db_mgr.get_user(int(user_id)) 
                    if user_data and user_data.get('referrer_id'):
                        ref_id = user_data['referrer_id']
                        ref_data = await db_mgr.get_user(int(ref_id))
                        if ref_data:
                            r_count = int(ref_data.get('referrals_count', 0))
                            if r_count >= 5000: ref_com = 0.0010
                            elif r_count >= 800: ref_com = 0.0006
                            elif r_count >= 600: ref_com = 0.0004
                            elif r_count >= 400: ref_com = 0.0003
                            else: ref_com = 0.0002
                            
                            await db_mgr.update_user_balance(int(ref_id), ref_com)
                
                display_num = extract_pure_number_without_cc(raw_num, country_name) if cc_mode == "ON" else raw_num
                
                otp_title_emoji = '<tg-emoji emoji-id="6138477872030947849">⚡</tg-emoji>'
                country_icon = '<tg-emoji emoji-id="5447410659077661506">🌍</tg-emoji>'
                num_icon = '<tg-emoji emoji-id="5841276284155467413">📱</tg-emoji>'
                earned_icon = '<tg-emoji emoji-id="5233389548204997373">💰</tg-emoji>'
                
                user_text = (
                    f"<blockquote>{otp_title_emoji} <b>OTP RECEIVED •</b> {s_emoji} <b>{assigned_service.upper()}</b>\n"
                    f"━━━━━━━━━━━━━━━━━━\n"
                    f"{country_icon} <b>Country:</b> {country_name.title()} {c_emoji}\n"
                    f"{num_icon} <b>Number:</b> <code>+{raw_num}</code>\n"
                    f"{earned_icon} <b>Earned:</b> ${reward:.3f}\n"
                    f"━━━━━━━━━━━━━━━━━━</blockquote>"
                )
                
                inline_kb = {
                    "inline_keyboard": [[
                        {
                            "text": f" {display_otp}",
                            "copy_text": {"text": copy_payload},
                            "style": "success",
                            "icon_custom_emoji_id": "6217712124492254630"
                        }
                    ]]
                }
                
                try:
                    await bot.send_message(chat_id=int(user_id), text=user_text, reply_markup=inline_kb)
                except Exception as dm_err: 
                    logger.error(f"Failed to DM User {user_id}: {dm_err}")

                global current_bot_idx
                active_bot = group_bots[current_bot_idx]
                current_bot_idx = (current_bot_idx + 1) % 2 
                
                num_str = str(raw_num)
                top_icon = '<tg-emoji emoji-id="5258028182149286660">🫀</tg-emoji>'
                bottom_icon = '<tg-emoji emoji-id="5134476056241112076">🐋</tg-emoji>'
                dot_icon = '<tg-emoji emoji-id="5350803719170564382">🟢</tg-emoji>'
                lang_icon = '<tg-emoji emoji-id="5436399161794639367">🌐</tg-emoji>'
                masked_display = f"+{num_str[:3]}{dot_icon}{num_str[-4:]}" if len(num_str) > 6 else f"+{num_str}"
                
                try: lang_short = str(detect(msg)).upper()[:2] if msg else "EN"
                except: lang_short = "EN"
                
                group_text = (
                    f'<b>╭──────</b>{top_icon}<b>──────╮</b>\n'
                    f'<b>│ </b>{c_emoji} <b>{get_short_country(country_name)} | </b>{s_emoji} <b>{masked_display} | </b>{lang_icon} <b>{lang_short}</b>\n'
                    f'<b>╰──────</b>{bottom_icon}<b>──────╯</b>'
                )
                
                group_kb = {"inline_keyboard": [
                    [{"text": f"{display_otp}", "copy_text": {"text": copy_payload}, "style": "success", "icon_custom_emoji_id": "5197288647275071607"}],
                    [{"text": "𝗡𝗨𝗠𝗕𝗘𝗥", "url": "https://t.me/primeotpworkbot", "style": "primary", "icon_custom_emoji_id": "5465624021947140508"},
                     {"text": "𝗠𝗘𝗧𝗛𝗢𝗗", "url": "https://t.me/+_MQpQfQQnNJmZmU1", "style": "primary", "icon_custom_emoji_id": "5444856076954520455"}]
                ]}
                
                asyncio.create_task(active_bot.send_message(chat_id=OTP_GROUP_ID, text=group_text, reply_markup=group_kb))
                
        except Exception as e:
            logger.error(f"Engine Crash: {e}")
            await asyncio.sleep(2)
                    
        except Exception as e:
            logger.error(f"Engine Crash: {e}")
            await asyncio.sleep(2)

async def main():
    await db_mgr.init_db()
    # 🔥 Ekhane purono namer bodole notun bullet_speed_engine bosano holo
    asyncio.create_task(bullet_speed_engine())
    logger.info("⚡ Mega Decentralized Bot Engine Operational (Bullet Speed Mode)!")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())