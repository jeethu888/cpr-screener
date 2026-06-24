import yfinance as yf
import pandas as pd
import json
from datetime import datetime
import pytz

# Group symbols by category
SYMBOLS = {
    "FNO": [
        "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS", 
        "SBIN.NS", "BHARTIARTL.NS", "ITC.NS", "KOTAKBANK.NS", "LT.NS",
        "AXISBANK.NS", "BAJFINANCE.NS", "MARUTI.NS", "ASIANPAINT.NS", "TITAN.NS",
        "SUNPHARMA.NS", "NESTLEIND.NS", "WIPRO.NS", "ONGC.NS", "NTPC.NS",
        "POWERGRID.NS", "TATASTEEL.NS", "TECHM.NS", "HCLTECH.NS", "DRREDDY.NS",
        "DIVISLAB.NS", "JSWSTEEL.NS", "ADANIENT.NS", "BAJAJFINSV.NS", "ULTRACEMCO.NS",
        "GRASIM.NS", "INDUSINDBK.NS", "CIPLA.NS", "EICHERMOT.NS", "APOLLOHOSP.NS",
        "BPCL.NS", "COALINDIA.NS", "BRITANNIA.NS", "TATACONSUM.NS", "HEROMOTOCO.NS",
        "HINDALCO.NS", "SBILIFE.NS", "HDFCLIFE.NS", "BAJAJ-AUTO.NS", "M&M.NS"
    ],
    "Indices": [
        "^NSEI",     # Nifty 50
        "^NSEBANK",  # Bank Nifty
        "^CNXIT"     # Nifty IT
    ],
    "Commodities": [
        "CL=F",      # Crude Oil (NYMEX proxy for MCX Crude)
        "GC=F",      # Gold (COMEX proxy for MCX Gold)
        "SI=F",      # Silver (COMEX proxy for MCX Silver)
        "NG=F"       # Natural Gas (NYMEX proxy for MCX NatGas)
    ]
}

def calculate_cpr(high, low, close):
    p = (high + low + close) / 3
    bc = (high + low) / 2
    tc = (p - bc) + p
    return {"pivot": p, "bc": bc, "tc": tc, "width": abs(tc - bc)}

def main():
    all_tickers = []
    category_map = {}
    
    for cat, syms in SYMBOLS.items():
        all_tickers.extend(syms)
        for s in syms:
            category_map[s] = cat

    print(f"Fetching data for {len(all_tickers)} symbols...")
    
    # Download last 5 days to ensure we have at least 2 valid trading days
    data = yf.download(all_tickers, period="5d", group_by="ticker", threads=True, progress=False)
    
    results = []
    
    for ticker in all_tickers:
        try:
            if len(all_tickers) == 1:
                df = data
            else:
                df = data[ticker]
            
            # Drop NaN rows (holidays, etc)
            df = df.dropna()
            
            if len(df) < 2:
                print(f"Not enough data for {ticker}")
                continue
                
            # Get last 2 trading days
            yesterday = df.iloc[-2]
            today = df.iloc[-1]
            
            today_close = today['Close']
            
            # Calculate Today's CPR (using yesterday's data)
            today_cpr = calculate_cpr(yesterday['High'], yesterday['Low'], yesterday['Close'])
            
            # Calculate Tomorrow's CPR (using today's data)
            tom_cpr = calculate_cpr(today['High'], today['Low'], today['Close'])
            
            # Conditions
            # 1. Narrow CPR: Width < 0.1% of Close
            is_narrow = today_cpr['width'] < (today_close * 0.001)
            
            # 2. Inside CPR: Tomorrow's CPR is strictly inside Today's CPR
            today_upper = max(today_cpr['tc'], today_cpr['bc'])
            today_lower = min(today_cpr['tc'], today_cpr['bc'])
            
            tom_upper = max(tom_cpr['tc'], tom_cpr['bc'])
            tom_lower = min(tom_cpr['tc'], tom_cpr['bc'])
            
            is_inside = (tom_upper < today_upper) and (tom_lower > today_lower)
            
            if is_narrow or is_inside:
                # Format name nicely
                name = ticker.replace(".NS", "").replace("=F", "")
                if name == "^NSEI": name = "NIFTY 50"
                if name == "^NSEBANK": name = "BANK NIFTY"
                if name == "^CNXIT": name = "NIFTY IT"
                if name == "CL": name = "CRUDE OIL"
                if name == "GC": name = "GOLD"
                if name == "SI": name = "SILVER"
                if name == "NG": name = "NATURAL GAS"
                
                results.append({
                    "symbol": name,
                    "ticker": ticker,
                    "category": category_map[ticker],
                    "close": round(today_close, 2),
                    "today_cpr_width": round(today_cpr['width'], 2),
                    "tom_cpr_width": round(tom_cpr['width'], 2),
                    "is_narrow": bool(is_narrow),
                    "is_inside": bool(is_inside)
                })
        except Exception as e:
            print(f"Error processing {ticker}: {e}")

    # Generate output
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)
    
    output = {
        "generated_at": now.strftime("%Y-%m-%d %H:%M:%S IST"),
        "total_scanned": len(all_tickers),
        "results": results
    }
    
    with open("cpr_data.json", "w") as f:
        json.dump(output, f, indent=4)
        
    print(f"Successfully generated cpr_data.json with {len(results)} matches.")

if __name__ == "__main__":
    main()
