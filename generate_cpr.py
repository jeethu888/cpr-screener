import requests
import pandas as pd
import json
from datetime import datetime, timedelta
import pytz
import io
import zipfile

# ─── NSE Headers (required to avoid 403) ─────────────────────────────────────
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/",
}

def get_nse_session():
    """Create a requests session with NSE cookies."""
    session = requests.Session()
    session.headers.update(HEADERS)
    try:
        # Hit the main page first to get cookies (NSE requires this)
        session.get("https://www.nseindia.com", timeout=15)
        # Also hit the API base to warm up
        session.get("https://www.nseindia.com/market-data/live-equity-market", timeout=15)
    except Exception as e:
        print(f"Warning: Could not warm up NSE session: {e}")
    return session

# ─── Step 1: Fetch Dynamic FNO List from NSE ─────────────────────────────────
def get_fno_symbols(session):
    print("Fetching FNO stock list from NSE...")
    url = "https://www.nseindia.com/api/master-quote"
    resp = session.get(url, timeout=15)
    resp.raise_for_status()
    symbols = resp.json()  # Returns a plain list of symbol strings
    print(f"  Found {len(symbols)} F&O stocks")
    return symbols

# ─── Step 2: Download NSE Bhav Copy (EOD OHLC for all stocks) ─────────────────
def get_bhav_copy(session, date):
    """Download NSE equity Bhav Copy for a given date."""
    dd = date.strftime("%d")
    mm = date.strftime("%m")
    yyyy = date.strftime("%Y")
    mon = date.strftime("%b").upper()
    
    # New-format URL (NSE switched to this after 2022)
    url = f"https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_{yyyy}{mm}{dd}_F_0000.csv.zip"
    
    print(f"  Downloading Bhav Copy for {date.strftime('%Y-%m-%d')} from: {url}")
    resp = session.get(url, timeout=30)
    
    if resp.status_code != 200:
        # Try old format
        url_old = f"https://archives.nseindia.com/content/historical/EQUITIES/{yyyy}/{mon}/cm{dd}{mon}{yyyy}bhav.csv.zip"
        print(f"  New format failed, trying old format: {url_old}")
        resp = session.get(url_old, timeout=30)
        resp.raise_for_status()
    
    # Unzip and parse
    with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
        fname = z.namelist()[0]
        with z.open(fname) as f:
            df = pd.read_csv(f)
    
    return df

def find_last_two_trading_days(session):
    """Find last 2 trading days by trying to download Bhav Copies."""
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)
    
    found_dates = []
    attempts = 0
    check_date = now.date()
    
    # If today's market hasn't closed (before 6 PM), skip today
    if now.hour < 18:
        check_date -= timedelta(days=1)
    
    while len(found_dates) < 2 and attempts < 10:
        # Skip weekends
        if check_date.weekday() < 5:  # Mon-Fri
            try:
                df = get_bhav_copy(session, check_date)
                found_dates.append((check_date, df))
                print(f"  [OK] Got Bhav Copy for {check_date}")
            except Exception as e:
                print(f"  [SKIP] No Bhav Copy for {check_date}: {e}")
        check_date -= timedelta(days=1)
        attempts += 1
    
    return found_dates

def parse_bhav(df, symbol):
    """Extract OHLC for a symbol from bhav copy dataframe."""
    # New NSE format columns
    if "TckrSymb" in df.columns:
        symbol_col = "TckrSymb"
        series_col = "SctySrs"
        open_col   = "OpnPric"
        high_col   = "HghPric"
        low_col    = "LwPric"
        close_col  = "ClsPric"
    else:
        # Old format
        symbol_col = "SYMBOL"
        series_col = "SERIES"
        open_col   = "OPEN"
        high_col   = "HIGH"
        low_col    = "LOW"
        close_col  = "CLOSE"

    row = df[(df[symbol_col] == symbol) & (df[series_col] == "EQ")]
    if row.empty:
        return None
    row = row.iloc[0]
    return {
        "open":  float(row[open_col]),
        "high":  float(row[high_col]),
        "low":   float(row[low_col]),
        "close": float(row[close_col]),
    }

# ─── Step 3: CPR Calculation ──────────────────────────────────────────────────
def calculate_cpr(high, low, close):
    p  = (high + low + close) / 3
    bc = (high + low) / 2
    tc = (p - bc) + p
    return {"pivot": p, "bc": bc, "tc": tc, "width": abs(tc - bc)}

# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)
    
    session = get_nse_session()
    
    # Step 1: Get live FNO list from NSE
    try:
        fno_symbols = get_fno_symbols(session)
    except Exception as e:
        print(f"Failed to fetch FNO list: {e}. Using fallback hardcoded list.")
        fno_symbols = [
            "RELIANCE","TCS","HDFCBANK","ICICIBANK","INFY","SBIN","BHARTIARTL",
            "ITC","KOTAKBANK","LT","AXISBANK","BAJFINANCE","MARUTI","ASIANPAINT",
            "TITAN","SUNPHARMA","WIPRO","ONGC","NTPC","POWERGRID","TATASTEEL",
            "TECHM","HCLTECH","DRREDDY","DIVISLAB","JSWSTEEL","ADANIENT",
            "BAJAJFINSV","ULTRACEMCO","GRASIM","INDUSINDBK","CIPLA","EICHERMOT",
            "APOLLOHOSP","BPCL","COALINDIA","BRITANNIA","TATACONSUM","HEROMOTOCO",
            "HINDALCO","SBILIFE","HDFCLIFE","BAJAJ-AUTO","M&M","HINDPETRO",
            "KOTAKBANK","AXISBANK","BLUESTARCO","TORNTPHARM","INDHOTEL","CHOLAFIN",
            "COFORGE","TECHM","PNBHOUSING","HYUNDAI",
        ]
    
    # Step 2: Get last 2 trading days' Bhav Copies
    print("Finding last 2 trading days with available Bhav Copies...")
    trading_days = find_last_two_trading_days(session)
    
    if len(trading_days) < 2:
        print("ERROR: Could not get 2 trading days of data. Exiting.")
        return
    
    # trading_days[0] = most recent (today's closed day => Tomorrow's CPR)
    # trading_days[1] = previous day          => Today's CPR
    today_date, today_bhav   = trading_days[0]
    prev_date,  prev_bhav    = trading_days[1]
    
    print(f"\nUsing:")
    print(f"  Today's CPR  <- {prev_date} OHLC")
    print(f"  Tomorrow's CPR <- {today_date} OHLC")
    
    results = []
    total_scanned = len(fno_symbols)
    
    for symbol in fno_symbols:
        try:
            today_ohlc = parse_bhav(today_bhav, symbol)
            prev_ohlc  = parse_bhav(prev_bhav, symbol)
            
            if today_ohlc is None or prev_ohlc is None:
                continue
            
            close = today_ohlc["close"]
            
            # Today's CPR = built from prev day's OHLC
            today_cpr = calculate_cpr(prev_ohlc["high"], prev_ohlc["low"], prev_ohlc["close"])
            # Tomorrow's CPR = built from today's OHLC
            tom_cpr   = calculate_cpr(today_ohlc["high"], today_ohlc["low"], today_ohlc["close"])
            
            # --- Narrow CPR: Tomorrow's CPR width < 0.1% of close
            is_narrow = tom_cpr["width"] < (close * 0.001)
            
            # --- Inside CPR: Tomorrow's CPR is strictly inside Today's CPR
            today_upper = max(today_cpr["tc"], today_cpr["bc"])
            today_lower = min(today_cpr["tc"], today_cpr["bc"])
            tom_upper   = max(tom_cpr["tc"],   tom_cpr["bc"])
            tom_lower   = min(tom_cpr["tc"],   tom_cpr["bc"])
            is_inside = (tom_upper < today_upper) and (tom_lower > today_lower)
            
            if is_narrow or is_inside:
                results.append({
                    "symbol":         symbol,
                    "category":       "FNO",
                    "close":          round(close, 2),
                    "eod_date":       str(today_date),
                    "tom_cpr_width":  round(tom_cpr["width"], 2),
                    "is_narrow":      bool(is_narrow),
                    "is_inside":      bool(is_inside),
                })
        except Exception as e:
            print(f"  Error processing {symbol}: {e}")
    
    # ── Output ────────────────────────────────────────────────────────────────
    output = {
        "generated_at":  now.strftime("%Y-%m-%d %H:%M:%S IST"),
        "total_scanned": total_scanned,
        "results":       results,
    }
    with open("cpr_data.json", "w") as f:
        json.dump(output, f, indent=4)
    
    print(f"\n[DONE] {len(results)} matches from {total_scanned} F&O stocks -> cpr_data.json")

if __name__ == "__main__":
    main()
