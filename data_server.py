import asyncio
import logging
import hashlib
import aiosqlite
import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from config import DB_PATH
from database import db_mgr
from api import api_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s")
logger = logging.getLogger("LiveDataServer")

app = FastAPI(title="Elite OTP Central Data Matrix")

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="2">
    <title>IVA Elite OTP - Live Data Feed</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        * {{ box-sizing: border-box; }}
        body {{
            font-family: 'Inter', 'Segoe UI', sans-serif;
            background: radial-gradient(circle at top left, #1a1f2b, #0a0c10 65%);
            color: #e4e6eb;
            margin: 0;
            padding: 30px 20px;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}

        .header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            flex-wrap: wrap;
            gap: 10px;
            margin-bottom: 24px;
        }}
        h1 {{
            background: linear-gradient(90deg, #4CAF50, #8bc34a 70%);
            -webkit-background-clip: text;
            background-clip: text;
            color: transparent;
            font-weight: 800;
            font-size: 27px;
            margin: 0;
            letter-spacing: -0.02em;
        }}
        .live-dot {{
            display: inline-block;
            width: 9px; height: 9px;
            background: #4CAF50;
            border-radius: 50%;
            margin-right: 8px;
            box-shadow: 0 0 8px #4CAF50;
            animation: pulse 1.4s infinite;
        }}
        @keyframes pulse {{
            0% {{ opacity: 1; transform: scale(1); }}
            50% {{ opacity: .4; transform: scale(1.3); }}
            100% {{ opacity: 1; transform: scale(1); }}
        }}
        .live-label {{ font-size: 13px; color: #8b8f9a; display:flex; align-items:center; }}

        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
            gap: 14px;
            margin-bottom: 22px;
        }}
        .stat-card {{
            background: linear-gradient(160deg, #171b25, #12151d);
            border: 1px solid #262b36;
            border-radius: 14px;
            padding: 16px 18px;
            position: relative;
            overflow: hidden;
        }}
        .stat-card::before {{
            content: "";
            position: absolute;
            top: 0; left: 0; right: 0;
            height: 3px;
            background: linear-gradient(90deg, #4CAF50, #8bc34a);
        }}
        .stat-card.pending::before {{ background: linear-gradient(90deg, #f57c00, #ffb300); }}
        .stat-label {{ font-size: 11px; text-transform: uppercase; letter-spacing: .07em; color: #8b8f9a; margin-bottom: 6px; }}
        .stat-value {{ font-size: 26px; font-weight: 800; color: #f0f2f5; }}

        .table-wrap {{
            background: rgba(22, 26, 34, 0.75);
            backdrop-filter: blur(10px);
            border: 1px solid #262b36;
            border-radius: 16px;
            overflow: hidden;
            box-shadow: 0 10px 30px rgba(0,0,0,0.4);
        }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{
            padding: 14px 18px;
            text-align: left;
            font-size: 13.5px;
        }}
        thead th {{
            background: #1b202b;
            color: #6fcf73;
            text-transform: uppercase;
            letter-spacing: .06em;
            font-size: 11.5px;
            font-weight: 700;
            border-bottom: 1px solid #2a2f3d;
        }}
        tbody tr {{
            border-bottom: 1px solid #1f2430;
            transition: background .15s ease;
            animation: fadeIn .4s ease;
        }}
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(-4px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        tbody tr:hover {{ background: #1c2130; }}
        tbody tr:last-child {{ border-bottom: none; }}

        td:nth-child(1) {{ color: #8b8f9a; font-family: 'JetBrains Mono', monospace; font-size: 12.5px; }}
        td:nth-child(2) {{ font-family: 'JetBrains Mono', monospace; color: #cfd3da; }}

        code {{
            background: #0e1116;
            padding: 4px 9px;
            border-radius: 6px;
            color: #9fd6a3;
            font-size: 12.5px;
            font-family: 'JetBrains Mono', monospace;
        }}

        .badge {{
            background: linear-gradient(90deg, #2e7d32, #43a047);
            color: #fff;
            padding: 5px 11px;
            border-radius: 20px;
            font-size: 10.5px;
            font-weight: 700;
            letter-spacing: .04em;
            box-shadow: 0 2px 8px rgba(76,175,80,0.25);
        }}
        .badge.pending {{
            background: linear-gradient(90deg, #e65100, #f57c00);
            box-shadow: 0 2px 8px rgba(245,124,0,0.25);
        }}

        .empty-state {{
            text-align: center;
            color: #666;
            padding: 44px 0;
            font-size: 14px;
        }}

        ::-webkit-scrollbar {{ height: 8px; width: 8px; }}
        ::-webkit-scrollbar-thumb {{ background: #2a2f3d; border-radius: 8px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>IVA Central Live Data Matrix</h1>
            <div class="live-label"><span class="live-dot"></span>Live Feed - auto-refresh 2s</div>
        </div>

        <div class="stats">
            <div class="stat-card">
                <div class="stat-label">Total Records</div>
                <div class="stat-value">{total_count}</div>
            </div>
            <div class="stat-card pending">
                <div class="stat-label">Pending</div>
                <div class="stat-value">{pending_count}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Completed</div>
                <div class="stat-value">{done_count}</div>
            </div>
        </div>

        <div class="table-wrap">
            <table>
                <thead>
                    <tr>
                        <th>Timestamp</th>
                        <th>Phone Number</th>
                        <th>Target Service</th>
                        <th>Message Payload</th>
                        <th>Queue Status</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_placeholder}
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    rows_html = ""
    total_count = pending_count = done_count = 0
    try:
        async with aiosqlite.connect(DB_PATH, timeout=20.0) as db:
            db.row_factory = aiosqlite.Row
            await db.execute("PRAGMA journal_mode=WAL;")
            
            # 🔥 OTP MISS না যাওয়ার আসল ট্রিক: dt_stamp এর বদলে rowid দিয়ে সাজানো হলো 
            # ফলে ডাটাবেসে যেই ডেটা সবার শেষে ঢুকবে, সেটাই সবার আগে (উপরে) দেখাবে!
            async with db.execute("SELECT * FROM otp_buffer ORDER BY rowid DESC LIMIT 50") as cursor:
                records = await cursor.fetchall()

        total_count = len(records)
        pending_count = sum(1 for r in records if r["status"] == "PENDING")
        done_count = total_count - pending_count

        for r in records:
            status_class = "pending" if r["status"] == "PENDING" else ""
            rows_html += f"""
            <tr>
                <td>{r['dt_stamp']}</td>
                <td>+{r['phone_number']}</td>
                <td><b style="color: #4CAF50;">{r['service']}</b></td>
                <td><code>{r['message']}</code></td>
                <td><span class="badge {status_class}">{r['status']}</span></td>
            </tr>
            """
    except Exception as e:
        rows_html = f"<tr><td colspan='5' class='empty-state'>Loading datastream updates... ({e})</td></tr>"

    if not rows_html:
        rows_html = "<tr><td colspan='5' class='empty-state'>No data in transmission stream yet.</td></tr>"

    return HTML_TEMPLATE.format(
        rows_placeholder=rows_html,
        total_count=total_count,
        pending_count=pending_count,
        done_count=done_count,
    )

async def live_api_fetcher_loop():
    await db_mgr.init_db()
    logger.info("📡 Central API Ingestion Fetcher Daemon Initiated (Smart Parser Mode)...")
    while True:
        try:
            otps = await api_client.get_success_otps()
            if otps and isinstance(otps, list):
                async with aiosqlite.connect(DB_PATH, timeout=20.0) as db:
                    await db.execute("PRAGMA journal_mode=WAL;")
                    for otp in otps:
                        if not isinstance(otp, dict):
                            continue
                            
                        # 🔥 rezsms.org এর "number" ফরম্যাট এখানে অটো ডিটেক্ট হবে!
                        raw_num = str(otp.get("num") or otp.get("number") or "").strip().replace("+", "")
                        service = str(otp.get("cli") or otp.get("service") or "Unknown").upper().strip()
                        msg = str(otp.get("message") or otp.get("sms") or "").strip()
                        dt_stamp = str(otp.get("dt") or otp.get("date") or "").strip()

                        # যদি নাম্বার বা মেসেজ ফাঁকা থাকে, তবেই স্কিপ করবে
                        if not raw_num or not msg:
                            continue

                        unique_seed = f"{dt_stamp}_{raw_num}_{msg}"
                        otp_id = hashlib.md5(unique_seed.encode("utf-8")).hexdigest()

                        cursor = await db.execute(
                            "INSERT OR IGNORE INTO otp_buffer (otp_id, phone_number, service, message, dt_stamp, status) VALUES (?, ?, ?, ?, ?, 'PENDING')",
                            (otp_id, raw_num, service, msg, dt_stamp),
                        )
                        
                        if cursor.rowcount > 0:
                            print(f"🔥 [NEW OTP CAPTURED] ➜ {service} | +{raw_num} | Time: {dt_stamp}")
                            
                    await db.commit()
        except Exception as e:
            logger.error(f"Fetcher Network Loop Exception: {e}")
        await asyncio.sleep(3)

@app.on_event("startup")
async def on_startup():
    asyncio.create_task(live_api_fetcher_loop())

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)