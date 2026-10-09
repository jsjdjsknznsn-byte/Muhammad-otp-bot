import aiosqlite
import logging
import re
from config import DB_PATH, PRIMARY_ADMIN_ID

logger = logging.getLogger("Bot.Database")

GLOBAL_COUNTRY_MAP = country_codes = {
    "1": "USA/Canada", "7": "Russia/Kazakhstan", "20": "Egypt", "27": "South Africa",
    "30": "Greece", "31": "Netherlands", "32": "Belgium", "33": "France",
    "34": "Spain", "36": "Hungary", "39": "Italy", "40": "Romania",
    "41": "Switzerland", "43": "Austria", "44": "United Kingdom", "45": "Denmark",
    "46": "Sweden", "47": "Norway", "48": "Poland", "49": "Germany",
    "51": "Peru", "52": "Mexico", "53": "Cuba", "54": "Argentina",
    "55": "Brazil", "56": "Chile", "57": "Colombia", "58": "Venezuela",
    "60": "Malaysia", "61": "Australia", "62": "Indonesia", "63": "Philippines",
    "64": "New Zealand", "65": "Singapore", "66": "Thailand",
    "81": "Japan", "82": "South Korea", "84": "Vietnam", "86": "China",
    "90": "Turkey", "91": "India", "92": "Pakistan", "93": "Afghanistan",
    "94": "Sri Lanka", "95": "Myanmar", "98": "Iran",
    "211": "South Sudan", "212": "Morocco", "213": "Algeria", "216": "Tunisia",
    "218": "Libya", "220": "Gambia", "221": "Senegal", "222": "Mauritania",
    "223": "Mali", "224": "Guinea", "225": "Ivory Coast", "226": "Burkina Faso",
    "227": "Niger", "228": "Togo", "229": "Benin", "230": "Mauritius",
    "231": "Liberia", "232": "Sierra Leone", "233": "Ghana", "234": "Nigeria",
    "235": "Chad", "236": "Central African Republic", "237": "Cameroon",
    "238": "Cape Verde", "239": "Sao Tome and Principe", "240": "Equatorial Guinea",
    "241": "Gabon", "242": "Republic of the Congo", "243": "DR Congo",
    "244": "Angola", "245": "Guinea-Bissau", "246": "British Indian Ocean Territory",
    "248": "Seychelles", "249": "Sudan", "250": "Rwanda", "251": "Ethiopia",
    "252": "Somalia", "253": "Djibouti", "254": "Kenya", "255": "Tanzania",
    "256": "Uganda", "257": "Burundi", "258": "Mozambique", "260": "Zambia",
    "261": "Madagascar", "262": "Reunion/Mayotte", "263": "Zimbabwe",
    "264": "Namibia", "265": "Malawi", "266": "Lesotho", "267": "Botswana",
    "268": "Eswatini", "269": "Comoros", "290": "Saint Helena", "291": "Eritrea",
    "297": "Aruba", "298": "Faroe Islands", "299": "Greenland",
    "350": "Gibraltar", "351": "Portugal", "352": "Luxembourg", "353": "Ireland",
    "354": "Iceland", "355": "Albania", "356": "Malta", "357": "Cyprus",
    "358": "Finland", "359": "Bulgaria", "370": "Lithuania", "371": "Latvia",
    "372": "Estonia", "373": "Moldova", "374": "Armenia", "375": "Belarus",
    "376": "Andorra", "377": "Monaco", "378": "San Marino", "379": "Vatican City",
    "380": "Ukraine", "381": "Serbia", "382": "Montenegro", "383": "Kosovo",
    "385": "Croatia", "386": "Slovenia", "387": "Bosnia and Herzegovina",
    "389": "North Macedonia", "420": "Czech Republic", "421": "Slovakia",
    "423": "Liechtenstein",
    "500": "Falkland Islands", "501": "Belize", "502": "Guatemala",
    "503": "El Salvador", "504": "Honduras", "505": "Nicaragua", "506": "Costa Rica",
    "507": "Panama", "508": "Saint Pierre and Miquelon", "509": "Haiti",
    "590": "Guadeloupe", "591": "Bolivia", "592": "Guyana", "593": "Ecuador",
    "594": "French Guiana", "595": "Paraguay", "596": "Martinique",
    "597": "Suriname", "598": "Uruguay", "599": "Curacao",
    "670": "East Timor", "672": "Norfolk Island", "673": "Brunei",
    "674": "Nauru", "675": "Papua New Guinea", "676": "Tonga", "677": "Solomon Islands",
    "678": "Vanuatu", "679": "Fiji", "680": "Palau", "681": "Wallis and Futuna",
    "682": "Cook Islands", "683": "Niue", "685": "Samoa", "686": "Kiribati",
    "687": "New Caledonia", "688": "Tuvalu", "689": "French Polynesia",
    "690": "Tokelau", "691": "Micronesia", "692": "Marshall Islands",
    "850": "North Korea", "852": "Hong Kong", "853": "Macau", "855": "Cambodia",
    "856": "Laos", "880": "Bangladesh", "886": "Taiwan",
    "960": "Maldives", "961": "Lebanon", "962": "Jordan", "963": "Syria",
    "964": "Iraq", "965": "Kuwait", "966": "Saudi Arabia", "967": "Yemen",
    "968": "Oman", "970": "Palestine", "971": "UAE", "972": "Israel",
    "973": "Bahrain", "974": "Qatar", "975": "Bhutan", "976": "Mongolia",
    "977": "Nepal", "992": "Tajikistan", "993": "Turkmenistan",
    "994": "Azerbaijan", "249": "Sudan", "996": "Kyrgyzstan", "998": "Uzbekistan"
}

def resolve_universal_country(phone: str) -> str:
    clean = re.sub(r'\D', '', str(phone).strip())
    for prefix in sorted(GLOBAL_COUNTRY_MAP.keys(), key=len, reverse=True):
        if clean.startswith(prefix):
            return GLOBAL_COUNTRY_MAP[prefix]
    return "UNKNOWN"

class MasterDatabase:
    def __init__(self):
        self.db_path = DB_PATH

    async def init_db(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("PRAGMA foreign_keys = ON;")
            
            # Full structured users table execution
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    balance REAL DEFAULT 0.0,
                    referrer_id INTEGER DEFAULT NULL,
                    referrals_count INTEGER DEFAULT 0,
                    otp_received_count INTEGER DEFAULT 0,
                    total_withdrawn REAL DEFAULT 0.0,
                    wallet_type TEXT DEFAULT NULL,
                    wallet_number TEXT DEFAULT NULL,
                    is_banned INTEGER DEFAULT 0,
                    min_withdraw REAL DEFAULT 5.0
                );
            """)
            
            # Advanced Schema Migrations for existing DB integrity mapping
            for col_def in [
                "referrer_id INTEGER DEFAULT NULL",
                "referrals_count INTEGER DEFAULT 0",
                "otp_received_count INTEGER DEFAULT 0",
                "total_withdrawn REAL DEFAULT 0.0",
                "wallet_type TEXT DEFAULT NULL",
                "wallet_number TEXT DEFAULT NULL",
                "is_banned INTEGER DEFAULT 0",
                "min_withdraw REAL DEFAULT 5.0"
            ]:
                try:
                    await db.execute(f"ALTER TABLE users ADD COLUMN {col_def}")
                except Exception:
                    pass

            await db.execute("CREATE TABLE IF NOT EXISTS admins (user_id INTEGER PRIMARY KEY);")
            await db.execute("CREATE TABLE IF NOT EXISTS categories (name TEXT PRIMARY KEY, nums_per_user INTEGER DEFAULT 1, rate_per_otp REAL DEFAULT 0.0);")
            await db.execute("CREATE TABLE IF NOT EXISTS services (name TEXT PRIMARY KEY);")
            
            # global_config thik kora holo
            await db.execute("""
                CREATE TABLE IF NOT EXISTS global_config (
                    config_key TEXT PRIMARY KEY,
                    config_value TEXT
                );
            """)
            
            # notun api_panels add kora holo
            await db.execute("""
                CREATE TABLE IF NOT EXISTS api_panels (
                    name TEXT PRIMARY KEY,
                    url TEXT,
                    status TEXT DEFAULT 'ON'
                );
            """)
            
            # Default Panels insert hobe
            default_panels = ["Blue SMS", "Fox SMS", "Rez SMS", "Zed SMS", "SMS Hadi"]
            for p in default_panels:
                await db.execute("INSERT OR IGNORE INTO api_panels (name, url, status) VALUES (?, NULL, 'ON')", (p,))
                
            await db.execute("""
                CREATE TABLE IF NOT EXISTS numbers_pool (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    phone_number TEXT UNIQUE,
                    country TEXT,
                    service TEXT,
                    assigned_to INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'AVAILABLE',
                    assigned_at TIMESTAMP,
                    FOREIGN KEY(service) REFERENCES categories(name) ON DELETE CASCADE
                );
            """)
            
            await db.execute("""
                CREATE TABLE IF NOT EXISTS otp_history (
                    otp_id TEXT PRIMARY KEY,
                    phone_number TEXT,
                    user_id INTEGER,
                    service TEXT,
                    reward REAL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            await db.execute("""
                CREATE TABLE IF NOT EXISTS otp_buffer (
                    otp_id TEXT PRIMARY KEY,
                    phone_number TEXT,
                    service TEXT,
                    message TEXT,
                    dt_stamp TEXT,
                    status TEXT DEFAULT 'PENDING'
                );
            """)
            
            await db.execute("""
                CREATE TABLE IF NOT EXISTS withdraw_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    amount REAL,
                    method TEXT,
                    wallet_number TEXT,
                    status TEXT DEFAULT 'PENDING',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # loop ta complete kora holo
            for col_def in ["method TEXT", "wallet_number TEXT"]:
                try:
                    await db.execute(f"ALTER TABLE withdraw_requests ADD COLUMN {col_def}")
                except Exception:
                    pass

            await db.execute("INSERT OR IGNORE INTO global_config (config_key, config_value) VALUES ('remove_cc', 'OFF');")
            await db.execute("INSERT OR IGNORE INTO global_config (config_key, config_value) VALUES ('support_username', 'support_bot');")
            await db.execute("INSERT OR IGNORE INTO global_config (config_key, config_value) VALUES ('withdraw_enabled', 'ON');")
            
            for default_service in ["Tiktok", "Facebook", "Telegram", "Instagram", "Paypal"]:
                await db.execute("INSERT OR IGNORE INTO services (name) VALUES (?)", (default_service,))
            await db.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?);", (PRIMARY_ADMIN_ID,))
            await db.commit()
            
        # 🔥 ZYRON/SPARROW table initialize korar function ekhane call deya holo
        await self.init_secure_panels()

    async def get_user(self, user_id: int) -> dict:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            query = """
                SELECT u.*, 
                (SELECT config_value FROM global_config WHERE config_key = 'support_username') as support_username
                FROM users u WHERE u.user_id = ?
            """
            async with db.execute(query, (user_id,)) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else {"balance": 0.0, "support_username": "support_bot", "min_withdraw": 5.0, "referrals_count": 0, "otp_received_count": 0, "total_withdrawn": 0.0, "wallet_type": None, "wallet_number": None}

    async def set_global_setting(self, key: str, value):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("INSERT OR REPLACE INTO global_config (config_key, config_value) VALUES (?, ?)", (key, str(value)))
            await db.commit()

    async def get_config(self, key: str) -> str:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT config_value FROM global_config WHERE config_key = ?", (key,)) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else "OFF"

    async def toggle_config(self, key: str):
        async with aiosqlite.connect(self.db_path) as db:
            current = await self.get_config(key)
            new_val = "ON" if current == "OFF" else "OFF"
            await db.execute("INSERT OR REPLACE INTO global_config (config_key, config_value) VALUES (?, ?)", (key, new_val))
            await db.commit()
            return new_val

    async def register_user(self, user_id: int, referrer_id: int = None):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,)) as cursor:
                exists = await cursor.fetchone()
                
            if not exists:
                if referrer_id and referrer_id != user_id:
                    await db.execute("INSERT INTO users (user_id, referrer_id) VALUES (?, ?)", (user_id, referrer_id))
                    await db.execute("UPDATE users SET referrals_count = referrals_count + 1 WHERE user_id = ?", (referrer_id,))
                else:
                    await db.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
                await db.commit()

    async def set_user_wallet(self, user_id: int, wallet_type: str, wallet_number: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE users SET wallet_type = ?, wallet_number = ? WHERE user_id = ?", (wallet_type, wallet_number, user_id))
            await db.commit()

    async def update_user_balance(self, user_id: int, amount: float):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
            await db.commit()

    async def increment_user_otp_stats(self, user_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE users SET otp_received_count = otp_received_count + 1 WHERE user_id = ?", (user_id,))
            await db.commit()

    async def is_admin(self, user_id: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT 1 FROM admins WHERE user_id = ?", (user_id,)) as cursor:
                return await cursor.fetchone() is not None

    async def add_admin(self, user_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (user_id,))
            await db.commit()

    async def remove_admin(self, user_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM admins WHERE user_id = ?", (user_id,))
            await db.commit()

    async def get_admins(self) -> list:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT user_id FROM admins") as cursor:
                return [row[0] for row in await cursor.fetchall()]

    async def add_service(self, name: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("INSERT OR IGNORE INTO services (name) VALUES (?)", (name.strip().title(),))
            await db.commit()

    async def get_services(self) -> list:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT name FROM services ORDER BY name") as cursor:
                return [row[0] for row in await cursor.fetchall()]

    async def save_category(self, name: str, nums_per_user: int, rate: float):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("INSERT OR REPLACE INTO categories (name, nums_per_user, rate_per_otp) VALUES (?, ?, ?)", (name.upper(), nums_per_user, rate))
            await db.commit()

    async def get_categories(self) -> list:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM categories") as cursor:
                return [dict(row) for row in await cursor.fetchall()]

    async def remove_category(self, name: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM categories WHERE name = ?", (name.upper(),))
            await db.commit()

    async def bulk_insert_numbers(self, data: list):
        async with aiosqlite.connect(self.db_path) as db:
            formatted_data = []
            for item in data:
                if len(item) >= 3:
                    phone = str(item[0]).replace("+", "").strip()
                    country = str(item[1]).strip()
                    if not country or country.upper() == "UNKNOWN":
                        country = resolve_universal_country(phone)
                    service = str(item[2]).upper().strip()
                    formatted_data.append((phone, country, service, 0, 'AVAILABLE'))
            if formatted_data:
                await db.executemany("INSERT OR IGNORE INTO numbers_pool (phone_number, country, service, assigned_to, status) VALUES (?, ?, ?, ?, ?)", formatted_data)
                await db.commit()

    async def get_inventory_summary(self) -> list:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT service, COUNT(*), COUNT(assigned_to) FROM numbers_pool WHERE status = 'AVAILABLE' OR assigned_to = 0 GROUP BY service") as cursor:
                return await cursor.fetchall()
                
    async def get_live_stock_detailed(self) -> list:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT country, service, COUNT(*) FROM numbers_pool WHERE status = 'AVAILABLE' OR assigned_to = 0 GROUP BY country, service") as cursor:
                return await cursor.fetchall()
                
    async def get_active_numbers_for_user(self, user_id: int) -> list:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM numbers_pool WHERE assigned_to = ?", (user_id,)) as cursor:
                return [dict(row) for row in await cursor.fetchall()]

    async def get_active_countries_for_service(self, service: str) -> list:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT DISTINCT country FROM numbers_pool WHERE UPPER(service) = UPPER(?) AND (status = 'AVAILABLE' OR assigned_to = 0 OR assigned_to IS NULL)", (service.upper(),)) as cursor:
                return [row[0] for row in await cursor.fetchall()]

    async def allocate_numbers_to_user(self, user_id: int, service: str, country: str, limit: int) -> list:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT phone_number FROM numbers_pool WHERE UPPER(service) = UPPER(?) AND UPPER(country) = UPPER(?) AND (assigned_to = 0 OR assigned_to IS NULL OR status = 'AVAILABLE') LIMIT ?", (service.upper(), country.upper(), limit)) as cursor:
                rows = await cursor.fetchall()
                nums = [r[0] for r in rows]
            if nums:
                placeholders = ",".join("?" for _ in nums)
                await db.execute(f"UPDATE numbers_pool SET assigned_to = ?, status = 'ASSIGNED', assigned_at = CURRENT_TIMESTAMP WHERE phone_number IN ({placeholders})", [user_id] + nums)
                await db.commit()
            return nums

    async def clear_user_numbers(self, user_id: int, service: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM numbers_pool WHERE assigned_to = ? AND service = ?", (user_id, service.upper()))
            await db.commit()

    async def log_otp(self, otp_id: str, phone_number: str, user_id: int, service: str, reward: float) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            try:
                await db.execute("INSERT INTO otp_history (otp_id, phone_number, user_id, service, reward) VALUES (?, ?, ?, ?, ?)", (otp_id, phone_number, user_id, service.upper(), reward))
                await db.commit()
                return True
            except aiosqlite.IntegrityError: re