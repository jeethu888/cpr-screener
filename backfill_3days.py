import json
import os
import pytz
from datetime import datetime, timedelta
import generate_cpr

def backfill():
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)
    
    # Authenticate Fyers
    fyers = generate_cpr.get_fyers_client()
    if not fyers:
        print("Failed to authenticate with Fyers.")
        return

    # Prepare targets
    fno_symbols = generate_cpr.get_nse_fno_symbols()
    indices = {
        "NIFTY 50": "NSE:NIFTY50-INDEX",
        "BANK NIFTY": "NSE:NIFTYBANK-INDEX",
        "NIFTY IT": "NSE:NIFTYIT-INDEX",
        "NIFTY FIN SVC": "NSE:FINNIFTY-INDEX"
    }
    targets = [{"symbol": k, "fyers": v, "cat": "Indices"} for k, v in indices.items()]
    targets += [{"symbol": s, "fyers": f"NSE:{s}-EQ", "cat": "FNO"} for s in fno_symbols]

    # Generate dates to backfill
    days_to_backfill = 3
    dates_to_run = []
    current = now
    while len(dates_to_run) < days_to_backfill:
        current -= timedelta(days=1)
        if current.weekday() < 5:  # Mon-Fri only
            dates_to_run.append(current)

    available_dates = []
    if os.path.exists("available_dates.json"):
        with open("available_dates.json", "r") as f:
            available_dates = json.load(f)

    for target_dt in dates_to_run:
        # We need history up to target_dt
        range_to = target_dt.strftime("%Y-%m-%d")
        range_from = (target_dt - timedelta(days=25)).strftime("%Y-%m-%d")
        
        print(f"\nFetching history up to {range_to}...")
        history_map = generate_cpr.load_history_data(fyers, targets, range_from, range_to)
        
        print(f"Building results for {range_to}...")
        # Empty quotes data since we rely entirely on the EOD history candle
        quotes_data = {}
        
        # pct_elapsed = 1.0 because EOD is done
        results = generate_cpr.build_results(target_dt, targets, history_map, quotes_data, 1.0)
        
        output = {
            "generated_at": target_dt.strftime("%Y-%m-%d %H:%M:%S IST") + " (Backfilled)",
            "total_scanned": len(targets),
            "results": results,
        }
        
        # CPR generated on a given day is for the NEXT trading session
        next_dt = target_dt + timedelta(days=1)
        if next_dt.weekday() == 5:
            next_dt += timedelta(days=2)
        elif next_dt.weekday() == 6:
            next_dt += timedelta(days=1)
            
        session_date = next_dt.strftime("%Y-%m-%d")
        filename = f"cpr_data_{session_date}.json"
        
        with open(filename, "w") as f:
            json.dump(output, f, indent=4)
            
        if session_date not in available_dates:
            available_dates.append(session_date)
            
        print(f"Saved {filename}")

    # Update available_dates.json
    available_dates.sort(reverse=True)
    with open("available_dates.json", "w") as f:
        json.dump(available_dates, f, indent=4)
    print("\nBackfill complete!")

if __name__ == '__main__':
    backfill()
