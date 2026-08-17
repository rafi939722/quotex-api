import time
import asyncio
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from termcolor import colored

from quotexpy import Quotex
from quotexpy.utils import asset_parse
from quotexpy.utils.candles_period import CandlesPeriod

# ==========================================
# CONFIGURATION & SETUP
# ==========================================

QUOTEX_EMAIL = "vipravith@gmail.com"
QUOTEX_PASSWORD = "@vipravith@12"

# Initialize Quotex Client (on_pin_code=None for Headless Server)
client = Quotex(
    email=QUOTEX_EMAIL,
    password=QUOTEX_PASSWORD,
    headless=True,
    on_pin_code=None
)

app = FastAPI(title="Quotex Real-Time API by RAFI")

# ==========================================
# SERVER LIFECYCLE MANAGEMENT
# ==========================================

async def background_connect():
    """Connects to Quotex in the background without blocking FastAPI startup."""
    print(colored("[STARTUP]: ", "blue"), "Connecting to Quotex in background...")
    try:
        await client.connect()
        print(colored("[SUCCESS]: ", "green"), "Quotex WebSocket Connected Successfully!")
    except Exception as e:
        print(colored("[ERROR]: ", "red"), f"Quotex Connection Error: {e}")

@app.on_event("startup")
async def startup_event():
    """Starts FastAPI immediately so Render binds the port, then connects Quotex in background."""
    asyncio.create_task(background_connect())

@app.on_event("shutdown")
async def shutdown_event():
    """Gracefully closes connection on server stop."""
    print(colored("[SHUTDOWN]: ", "blue"), "Closing Quotex connection...")
    try:
        client.close()
    except Exception:
        pass

# ==========================================
# HELPER FUNCTIONS
# ==========================================

async def ensure_connection():
    """Ensures connection is alive; reconnects if dropped."""
    try:
        client.check_asset(asset_parse("EURUSD"))
    except Exception:
        print(colored("[RECONNECTING]: ", "yellow"), "Connection dropped. Reconnecting...")
        await client.connect()

# ==========================================
# MAIN API ENDPOINT
# ==========================================

@app.get("/api/candle/{asset}")
async def get_realtime_candle(asset: str, request: Request):
    start_time = time.time()
    
    await ensure_connection()
    
    target_asset = asset
    success = False
    data_list = []
    
    try:
        asset_query = asset_parse(asset)
        asset_open = client.check_asset(asset_query)
        
        if not asset_open or not asset_open[2]:
            target_asset = f"{asset}_otc"
            asset_query = asset_parse(target_asset)
            asset_open = client.check_asset(asset_query)
            
            if not asset_open or not asset_open[2]:
                return JSONResponse(content={
                    "Owner_Developer": "RAFI",
                    "Telegram": "@zrtrader1",
                    "Channel": "https://t.me/NEXUSAI_Community",
                    "Broker": "Quotex",
                    "Timeframe": "M1",
                    "Version": "2.00",
                    "Execution_time": f"{time.time() - start_time:.4f} second",
                    "success": False,
                    "message": f"Asset {asset} is entirely closed right now."
                }, status_code=400)

        candles = await client.get_candle_v2(target_asset, CandlesPeriod.ONE_MINUTE, count=3000)
        
        if candles and isinstance(candles, list):
            success = True
            reversed_candles = list(reversed(candles))
            
            for c in reversed_candles:
                c_time = c.get('time', 0)
                c_open = float(c.get('open', 0.0))
                c_close = float(c.get('close', 0.0))
                c_high = float(c.get('high', 0.0))
                c_low = float(c.get('low', 0.0))
                c_vol = int(c.get('volume', 0))
                
                if c_close > c_open:
                    colour = "green"
                elif c_close < c_open:
                    colour = "red"
                else:
                    colour = "doji"
                
                time_str = datetime.fromtimestamp(c_time).strftime('%Y-%m-%d %H:%M:%S')

                data_list.append({
                    "pair": target_asset,
                    "time": time_str,
                    "epoch": c_time,
                    "open": c_open,
                    "high": c_high,
                    "low": c_low,
                    "close": c_close,
                    "colour": colour,
                    "payout": 84,
                    "volume": c_vol
                })

    except Exception as e:
        print(colored("[API ERROR]: ", "red"), str(e))
        success = False
        data_list = []

    execution_time_str = f"{time.time() - start_time:.4f} second"

    response_payload = {
        "Owner_Developer": "RAFI",
        "Telegram": "@zrtrader1",
        "Channel": "https://t.me/NEXUSAI_Community",
        "Broker": "Quotex",
        "Timeframe": "M1",
        "Version": "2.00",
        "Execution_time": execution_time_str,
        "success": success,
        "pair": target_asset,
        "count": len(data_list),
        "data": data_list
    }

    return JSONResponse(content=response_payload)

# ==========================================
# SERVER RUNNER
# ==========================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
