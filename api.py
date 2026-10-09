import aiohttp
import asyncio
import logging
import time
import json
from urllib.parse import urlparse
from database import db_mgr

logger = logging.getLogger("Bot.API")

class EliteAPIClient:
    def __init__(self):
        self.session = None
        self.auth_lock = asyncio.Lock()
        self.global_seen_ids = set() # Structure dhorar jonno rekhechi, kintu filter disable kora

    def initialize_session(self):
        if self.session is None or self.session.closed:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json, text/javascript, */*; q=0.01',
            }
            connector = aiohttp.TCPConnector(ssl=False)
            self.session = aiohttp.ClientSession(connector=connector, headers=headers)

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

    # ==================== HYPER ENGINE API FETCH (NO SPAM FILTER - CATCHES ALL) ====================
    async def _fetch_single(self, url: str) -> list:
        if not url or not str(url).strip().startswith("http"): 
            return []
        
        parsed_url = urlparse(url)
        short_name = parsed_url.netloc if parsed_url.netloc else "Unknown_API"
        
        try:
            async with self.session.get(url, timeout=7.0) as resp:
                if resp.status == 200:
                    try:
                        # টেক্সট হিসেবে নিয়ে জোর করে JSON বানাবে
                        text_data = await resp.text()
                        res_data = json.loads(text_data)
                    except Exception as e:
                        print(f"⚠️ [{short_name}] JSON Parse Error: {e}")
                        return []

                    raw_records = []
                    
                    # 🔥 ১. রেসপন্স ডাইরেক্ট লিস্ট হলে সরাসরি ধরে নেবে
                    if isinstance(res_data, list):
                        raw_records = res_data
                        
                    # 🔥 ২. রেসপন্স ডিকশনারি হলে হাইপার-স্ক্যানিং করবে (নতুন প্যানেলের রুট কি সহ)
                    elif isinstance(res_data, dict):
                        for key in ["data", "records", "otps", "aaData", "result", "messages", "items", "payload", "response", "list"]:
                            if key in res_data and isinstance(res_data[key], list):
                                raw_records = res_data[key]
                                break
                        
                        if not raw_records:
                            for val in res_data.values():
                                if isinstance(val, list) and len(val) > 0 and isinstance(val[0], (dict, list, tuple)):
                                    raw_records = val
                                    break
                                    
                        if not raw_records and ("number" in res_data or "num" in res_data) and ("content" in res_data or "message" in res_data):
                            raw_records = [res_data]

                    if not raw_records:
                        return []

                    normalized_data = []
                    for item in raw_records:
                        # 🔥 ডিকশনারি আইটেম হ্যান্ডেলিং (All formats including time, content, number)
                        if isinstance(item, dict):
                            date_str = str(item.get("time", item.get("dt", item.get("date", item.get("created_at", item.get("timestamp", "")))))).strip()
                            num = str(item.get("number", item.get("num", item.get("phone", item.get("mobile", item.get("receiver", "")))))).strip()
                            cli = str(item.get("cli", item.get("service", item.get("sender", item.get("gateway", item.get("app", "")))))).strip()
                            msg = str(item.get("content", item.get("message", item.get("text", item.get("sms", item.get("body", "")))))).strip()
                            
                            range_info = str(item.get("range", item.get("country", item.get("region", "")))).strip()
                            country_name = range_info.split()[0] if range_info else "Unknown"

                            if len(num) >= 5 and msg:
                                # 🔥 NO SPAM FILTER - সরাসরি লিস্টে যুক্ত হবে
                                normalized_data.append({
                                    "dt": date_str,
                                    "num": num,
                                    "cli": cli,
                                    "message": msg,
                                    "country": country_name
                                })
                        
                        # 🔥 পুরনো লিস্ট/টাপল আইটেম হ্যান্ডেলিং
                        elif isinstance(item, (list, tuple)) and len(item) >= 6:
                            date_str = str(item[0]).strip()
                            num = str(item[2]).strip()
                            cli = str(item[3]).strip()
                            msg = str(item[5]).strip()

                            if len(num) >= 5 and msg:
                                # 🔥 NO SPAM FILTER - সরাসরি লিস্টে যুক্ত হবে
                                normalized_data.append({
                                    "dt": date_str,
                                    "num": num,
                                    "cli": cli,
                                    "message": msg,
                                    "country": "Unknown"
                                })

                    if normalized_data:
                        print(f"✅ [{short_name}] FETCHED {len(normalized_data)} RECORDS DIRECTLY!")
                    return normalized_data

                else:
                    print(f"🚫 [{short_name}] Server Error/Blocked! Status: {resp.status}")
                    return []
                    
        except asyncio.TimeoutError:
            print(f"⏰ [{short_name}] Timeout! Server is too slow.")
        except Exception as e:
            print(f"💥 [{short_name}] Error: {e}")
        
        return []

    # ==================== MAIN GATHERER ====================
    async def get_success_otps(self) -> list:
        self.initialize_session()
        
        # Direct API Panels fetch
        panels = await db_mgr.get_all_panels()
        active_urls = [p['url'] for p in panels if p['status'] == 'ON' and p['url'] and p['url'].startswith("http")]
        tasks = [self._fetch_single(url.strip()) for url in active_urls]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        combined_otps = []
        for res in results:
            if isinstance(res, list):
                combined_otps.extend(res)
                
        return combined_otps

api_client = EliteAPIClient()