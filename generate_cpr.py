import os
import requests
import json
from datetime import datetime, timedelta
import pytz
from fyers_apiv3 import fyersModel
import time

def get_nse_fno_symbols():
    """Fetch the live list of F&O stocks from NSE to keep it updated."""
    print("Fetching FNO stock list from NSE...")
    try:
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0",
            "Accept": "*/*",
            "Referer": "https://www.nseindia.com/"
        })
        # Waking up NSE session
        session.get("https://www.nseindia.com", timeout=15)
        
        url = "https://www.nseindia.com/api/master-quote"
        resp = session.get(url, timeout=15)
        resp.raise_for_status()
        symbols = resp.json()
        print(f"  Found {len(symbols)} F&O stocks")
        return symbols
    except Exception as e:
        print(f"  Failed to fetch live FNO list: {e}")
        # Fallback list
        return ["RELIANCE", "HDFCBANK", "ICICIBANK", "INFY", "TCS"]

def get_fyers_client():
    client_id = os.environ.get("FYERS_CLIENT_ID")
    access_token = os.environ.get("FYERS_ACCESS_TOKEN")
    
    if not client_id or not access_token:
        print("ERROR: FYERS_CLIENT_ID or FYERS_ACCESS_TOKEN not set in environment.")
        return None
        
    return fyersModel.FyersModel(client_id=client_id, is_async=False, token=access_token, log_path="")

def calculate_cpr(high, low, close):
    p  = (high + low + close) / 3
    bc = (high + low) / 2
    tc = (p - bc) + p
    return {"pivot": p, "bc": bc, "tc": tc, "width": abs(tc - bc)}

def fetch_history_for_symbol(fyers, symbol_fyers, range_from, range_to):
    data = {
        "symbol": symbol_fyers,
        "resolution": "1D",
        "date_format": "1",
        "range_from": range_from,
        "range_to": range_to,
        "cont_flag": "1"
    }
    
    for _ in range(3): # Retries
        response = fyers.history(data=data)
        if response.get("s") == "ok":
            return response.get("candles", [])
        elif response.get("code") == -300: # Invalid symbol
            return []
        elif response.get("code") == 429: # Rate limit
            time.sleep(1)
            continue
        else:
            time.sleep(0.5)
            
    print(f"  Error fetching {symbol_fyers}: {response}")
    return []

def main():
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)
    
    # Range for history (last 10 days to be safe for weekends/holidays)
    range_to = now.strftime("%Y-%m-%d")
    range_from = (now - timedelta(days=10)).strftime("%Y-%m-%d")
    
    fyers = get_fyers_client()
    if not fyers:
        return

    fno_symbols = get_nse_fno_symbols()
    
    # Indices mapping
    indices = {
        "NIFTY 50": "NSE:NIFTY50-INDEX",
        "BANK NIFTY": "NSE:NIFTYBANK-INDEX",
        "NIFTY IT": "NSE:NIFTYIT-INDEX",
        "NIFTY FIN SVC": "NSE:FINNIFTY-INDEX"
    }

    results = []
    
    # Combine lists
    targets = [{"symbol": k, "fyers": v, "cat": "Indices"} for k, v in indices.items()]
    targets += [{"symbol": s, "fyers": f"NSE:{s}-EQ", "cat": "FNO"} for s in fno_symbols]

    print("Fetching Live Quotes for today's data...")
    fyers_symbols = [t["fyers"] for t in targets]
    quotes_data = {}
    for i in range(0, len(fyers_symbols), 50):
        chunk = fyers_symbols[i:i+50]
        try:
            resp = fyers.quotes(data={"symbols": ",".join(chunk)})
            if resp.get("s") == "ok":
                for item in resp.get("d", []):
                    quotes_data[item["n"]] = item["v"]
        except Exception as e:
            print(f"Quotes API error: {e}")

    print("Fetching historical data for previous CPR...")
    
    for item in targets:
        candles = fetch_history_for_symbol(fyers, item["fyers"], range_from, range_to)
        
        if len(candles) < 2:
            continue
            
        last_history_candle = candles[-1]
        try:
            last_history_date = datetime.fromtimestamp(last_history_candle[0], ist).strftime('%Y-%m-%d')
        except:
            last_history_date = ""

        today_date_str = now.strftime('%Y-%m-%d')

        if last_history_date == today_date_str:
            # Market closed: History has updated with today's EOD candle
            today_high = last_history_candle[2]
            today_low = last_history_candle[3]
            today_close = last_history_candle[4]
            prev_candle = candles[-2]
            today_date = last_history_date
        else:
            # Live Market: History is lagging, use Quotes for today's live data
            prev_candle = last_history_candle
            quote = quotes_data.get(item["fyers"])
            if quote:
                today_high = quote.get("high_price")
                today_low = quote.get("low_price")
                today_close = quote.get("lp")
                today_date = today_date_str
            else:
                # Fallback if no quote available
                today_high = last_history_candle[2]
                today_low = last_history_candle[3]
                today_close = last_history_candle[4]
                prev_candle = candles[-2]
                today_date = last_history_date
        
        # Today's CPR uses Yesterday's OHLC
        today_cpr = calculate_cpr(prev_candle[2], prev_candle[3], prev_candle[4])
        # Tomorrow's CPR uses Today's OHLC
        tom_cpr = calculate_cpr(today_high, today_low, today_close)
        
        is_narrow = tom_cpr["width"] < (today_close * 0.001)
        
        today_upper = max(today_cpr["tc"], today_cpr["bc"])
        today_lower = min(today_cpr["tc"], today_cpr["bc"])
        tom_upper   = max(tom_cpr["tc"],   tom_cpr["bc"])
        tom_lower   = min(tom_cpr["tc"],   tom_cpr["bc"])
        is_inside = (tom_upper < today_upper) and (tom_lower > today_lower)
        
        if is_narrow or is_inside:
            results.append({
                "symbol":         item["symbol"],
                "category":       item["cat"],
                "close":          round(today_close, 2),
                "eod_date":       today_date,
                "tom_cpr_width":  round(tom_cpr["width"], 2),
                "is_narrow":      bool(is_narrow),
                "is_inside":      bool(is_inside),
            })
            
        # Rate limit safety
        time.sleep(0.05)
            
    # ── Output ────────────────────────────────────────────────────────────────
    output = {
        "generated_at":  now.strftime("%Y-%m-%d %H:%M:%S IST"),
        "total_scanned": len(targets),
        "results":       results,
    }
    with open("cpr_data.json", "w") as f:
        json.dump(output, f, indent=4)
    
    print(f"\n[DONE] {len(results)} matches from {len(targets)} symbols -> cpr_data.json")

if __name__ == "__main__":
    main()
