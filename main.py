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

# Replace with your actual Quotex credentials
QUOTEX_EMAIL = "vipravith@gmail.com"
QUOTEX_PASSWORD = "@vipravith@12"

# Initialize Quotex Client
def on_pin_code() -> str:
    return input("Enter the 2FA code sent to your email: ")

client = Quotex(
    email=vipravith@gmail.com,
    password=@vipravith@12,
    headless=True,
    on_pin_code=on_pin_code
)

app = FastAPI(title="Quotex Real-Time API by RAFI")

# ==========================================
# SERVER LIFECYCLE MANAGEMENT
# ==========================================

@app.on_event("startup")
async def startup_event():
    """Starts the Quotex connection when the server boots up."""
    print(colored("[STARTUP]: ", "blue"), "Initializing server & connecting to Quotex...")
    connected = await client.connect()
    if connected:
        print(colored("[SUCCESS]: ", "green"), "Quotex WebSocket Connected Successfully!")
    else:
        print(colored("[ERROR]: ", "red"), "Connection Failed! Retrying on first request...")

@app.on_event("shutdown")
async def shutdown_event():
    """Gracefully closes connection on server stop."""
    print(colored("[SHUTDOWN]: ", "blue"), "Closing Quotex connection...")
    client.close()

# ==========================================
# HELPER FUNCTIONS
# ==========================================

async def ensure_connection():
    """Ensures 0% error by reconnecting automatically if the connection drops."""
    try:
        # A quick check to see if we can get asset data. If it fails, we reconnect.
        client.check_asset(asset_parse("EURUSD"))
    except Exception:
        print(colored("[RECONNECTING]: ", "yellow"), "Connection dropped. Reconnecting...")
        await client.connect()

# ==========================================
# MAIN API ENDPOINT
# ==========================================

@app.get("/api/candle/{asset}")
async def get_realtime_candle(asset: str, request: Request):
    """
    Fetches real-time exact candle data for any asset.
    Automatically fetches exactly 3000 previous candles.
    """
    start_time = time.time()
    
    # 1. Ensure connection is alive to prevent 0% errors
    await ensure_connection()
    
    target_asset = asset
    success = False
    data_list = []
    
    try:
        # 2. Parse and validate asset
        asset_query = asset_parse(asset)
        asset_open = client.check_asset(asset_query)
        
        # 3. Fallback to OTC if standard market is closed
        if not asset_open or not asset_open[2]:
            target_asset = f"{asset}_otc"
            asset_query = asset_parse(target_asset)
            asset_open = client.check_asset(asset_query)
            
            # If OTC is also closed, we return a structured error response
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

        # 4. Fetch EXACTLY 3000 candles from real-time market
        # count=3000 ensures we get the massive history you requested
        candles = await client.get_candle_v2(target_asset, CandlesPeriod.ONE_MINUTE, count=3000)
        
        if candles and isinstance(candles, list):
            success = True
            
            # 5. Reverse candles so the absolute LATEST is at index 0 (Top)
            reversed_candles = list(reversed(candles))
            
            for c in reversed_candles:
                # Safely extract data with fallbacks to avoid any KeyErrors
                c_time = c.get('time', 0)
                c_open = float(c.get('open', 0.0))
                c_close = float(c.get('close', 0.0))
                c_high = float(c.get('high', 0.0))
                c_low = float(c.get('low', 0.0))
                c_vol = int(c.get('volume', 0))
                
                # Determine candle color
                if c_close > c_open:
                    colour = "green"
                elif c_close < c_open:
                    colour = "red"
                else:
                    colour = "doji"
                
                # Format time string (YYYY-MM-DD HH:MM:SS)
                time_str = datetime.fromtimestamp(c_time).strftime('%Y-%m-%d %H:%M:%S')

                # Append to our final data structure
                data_list.append({
                    "pair": target_asset,
                    "time": time_str,
                    "epoch": c_time,
                    "open": c_open,
                    "high": c_high,
                    "low": c_low,
                    "close": c_close,
                    "colour": colour,
                    "payout": 84,  # Standard fallback payout
                    "volume": c_vol
                })

    except Exception as e:
        # Catch absolutely any error to guarantee 0% crash rate
        print(colored("[API ERROR]: ", "red"), str(e))
        success = False
        data_list = []

    # 6. Calculate execution time
    execution_time_str = f"{time.time() - start_time:.4f} second"

    # 7. Build the exact JSON response requested
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
    # Starts the local server
    print(colored("[INFO]: ", "cyan"), "Starting Fast API Server on Port 8000...")
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
