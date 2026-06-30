import argparse
import os
import requests
import json
from datetime import datetime, timedelta, date
import pytz
from fyers_apiv3 import fyersModel
import time
import math

def get_nse_fno_symbols():
    print("Fetching FNO stock list from NSE...")
    try:
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0",
            "Accept": "*/*",
            "Referer": "https://www.nseindia.com/"
        })
        session.get("https://www.nseindia.com", timeout=15)
        url = "https://www.nseindia.com/api/master-quote"
        resp = session.get(url, timeout=15)
        resp.raise_for_status()
        symbols = resp.json()
        print(f"  Found {len(symbols)} F&O stocks")
        return symbols
    except Exception as e:
        print(f"  Failed to fetch live FNO list: {e}")
        return ["RELIANCE", "HDFCBANK", "ICICIBANK", "INFY", "TCS"]

def fetch_live_quotes(fyers, symbols):
    quotes_data = {}
    for i in range(0, len(symbols), 50):
        chunk = symbols[i:i+50]
        try:
            resp = fyers.quotes(data={"symbols": ",".join(chunk)})
            if resp.get("s") == "ok":
                for item in resp.get("d", []):
                    quotes_data[item["n"]] = item["v"]
        except Exception:
            pass
    return quotes_data

def get_fyers_client():
    client_id = os.environ.get("FYERS_CLIENT_ID")
    if not client_id:
        client_id = "WY1A1JUOA0-100"  # Fallback to known App ID
        
    access_token = os.environ.get("FYERS_ACCESS_TOKEN")
    
    if not access_token:
        print("FYERS_ACCESS_TOKEN not set in environment.")
        access_token = input("Enter your Fyers Access Token: ").strip()
        if not access_token:
            print("ERROR: No token provided.")
            return None
        
    return fyersModel.FyersModel(client_id=client_id, is_async=False, token=access_token, log_path="")

def fetch_history_for_symbol(fyers, symbol_fyers, range_from, range_to):
    data = {"symbol": symbol_fyers, "resolution": "1D", "date_format": "1", "range_from": range_from, "range_to": range_to, "cont_flag": "1"}
    for attempt in range(5):
        try:
            response = fyers.history(data=data)
            if response.get("s") == "ok":
                return response.get("candles", [])
            elif response.get("code") == -300:
                return []  # Invalid symbol
            elif response.get("code") == 429:
                time.sleep(2)
                continue
            else:
                if attempt == 0:
                    print(f"  API response for {symbol_fyers}: code={response.get('code')} msg={response.get('message','')[:80]}")
                time.sleep(1)
        except Exception as e:
            time.sleep(2)
    return []

def get_zone_label(c, pivot, tc, bc, r1, r2, s1, s2):
    upper = max(tc, bc)
    lower = min(tc, bc)
    r3 = r1 + (r1 - s1)
    r4 = r3 + (r1 - s1)
    s3 = s1 - (r1 - s1)
    s4 = s3 - (r1 - s1)
    if c >= r4: return "▲R4"
    if c >= r3: return "▲R3"
    if c >= r2: return "▲R2"
    if c >= r1: return "▲R1"
    if c >= upper: return "▲Pvt"
    if c >= lower: return "InCPR"
    if c >= pivot: return "▼TC"
    if c >= s1: return "▼Pvt"
    if c >= s2: return "▼S1"
    if c >= s3: return "▼S2"
    if c >= s4: return "▼S3"
    return "▼S4"

def get_daily_code(c, tc, bc, r1, s1, pdh, pdl):
    upper = max(tc, bc)
    lower = min(tc, bc)
    abv = c > upper
    blw = c < lower
    if abv and (c > r1 or c > pdh): return "VBull"
    if blw and (c < s1 or c < pdl): return "VBear"
    if abv: return "WBull"
    if blw: return "WBear"
    return "Neutral"

def get_weekly_code(c, wpiv):
    return "WBull" if c >= wpiv else "WBear"

def get_bias(dCode, wCode):
    bull_codes = {"WBull", "VBull", "Neutral"}
    bear_codes = {"WBear", "VBear", "Neutral"}
    if wCode == "WBull" and dCode in bull_codes:
        return "BULL"
    if wCode == "WBear" and dCode in bear_codes:
        return "BEAR"
    return "NONE"

def near_level(val, lvl, thresh):
    if not lvl or lvl <= 0: return False
    return abs(val - lvl) / lvl <= thresh

def check_one(lc, lvl, name, thresh):
    if not lvl or lvl <= 0.0: return "", 999.0
    d = abs(lc - lvl) / lvl
    if d <= thresh:
        ok = lc < lvl if name in ["R1", "PDH"] else lc > lvl if name in ["S1", "PDL"] else True
        if ok: return name, d
    return "", 999.0

def lvl_eval(lc, pdh, pdl, r1, s1, thresh):
    n1, d1 = check_one(lc, pdh, "PDH", thresh)
    n2, d2 = check_one(lc, pdl, "PDL", thresh)
    n3, d3 = check_one(lc, r1, "R1", thresh)
    n4, d4 = check_one(lc, s1, "S1", thresh)
    if d1 <= d2 and d1 <= d3 and d1 <= d4: return n1
    if d2 <= d3 and d2 <= d4: return n2
    if d3 <= d4: return n3
    return n4

def get_next_level_dist(z, dt, db, dp, dr1, dr2, dr3, dr4, ds1, ds2, ds3, ds4):
    rg = dr1 - ds1
    lvlFrom = None
    lvlTo = None
    if z=="▲R1": lvlFrom, lvlTo = dr1, dr2
    elif z=="▲R2": lvlFrom, lvlTo = dr2, dr3
    elif z=="▲R3": lvlFrom, lvlTo = dr3, dr4
    elif z=="▲R4": lvlFrom, lvlTo = dr4, dr4+rg
    elif z=="▲Pvt": lvlFrom, lvlTo = max(dt,db), dr1
    elif z=="InCPR": lvlFrom, lvlTo = min(dt,db), max(dt,db)
    elif z=="▼TC": lvlFrom, lvlTo = dp, max(dt,db)
    elif z=="▼Pvt": lvlFrom, lvlTo = ds1, dp
    elif z=="▼S1": lvlFrom, lvlTo = ds2, ds1
    elif z=="▼S2": lvlFrom, lvlTo = ds3, ds2
    elif z=="▼S3": lvlFrom, lvlTo = ds4, ds3
    elif z=="▼S4": lvlFrom, lvlTo = ds4-rg, ds4
    
    if lvlFrom and lvlFrom > 0:
        return abs(lvlTo - lvlFrom) / lvlFrom * 100.0
    return None

def load_history_data(fyers, targets, range_from, range_to):
    history_map = {}
    for item in targets:
        candles = fetch_history_for_symbol(fyers, item["fyers"], range_from, range_to)
        if candles:
            history_map[item["fyers"]] = candles
        time.sleep(0.15) # Fyers allows ~10 req/s, 0.15s delay helps prevent 429
    return history_map


def build_results(now, targets, history_map, quotes_data, pct_elapsed):
    results = []
    for item in targets:
        candles = history_map.get(item["fyers"], [])
        if len(candles) < 3:
            continue

        last_history_candle = candles[-1]
        try:
            last_history_date = datetime.fromtimestamp(last_history_candle[0], pytz.timezone('Asia/Kolkata')).date()
        except:
            last_history_date = now.date()

        quote = quotes_data.get(item["fyers"])

        if last_history_date == now.date():
            today_candle = last_history_candle
            yest_candle = candles[-2]
            yest2_candle = candles[-3] if len(candles) > 2 else yest_candle

            if quote:
                today_candle = [
                    today_candle[0],
                    quote.get("open_price", today_candle[1]),
                    max(today_candle[2], quote.get("high_price", today_candle[2])),
                    min(today_candle[3], quote.get("low_price", today_candle[3])),
                    quote.get("lp", today_candle[4]),
                    quote.get("volume", today_candle[5])
                ]
        else:
            yest_candle = last_history_candle
            yest2_candle = candles[-2]
            if quote:
                today_candle = [0, quote.get("open_price"), quote.get("high_price"), quote.get("low_price"), quote.get("lp"), quote.get("volume")]
            else:
                today_candle = last_history_candle

        current_week = now.date().isocalendar()[1]
        prev_week_candles = []
        for c in candles:
            dt = datetime.fromtimestamp(c[0], pytz.timezone('Asia/Kolkata')).date()
            if dt.isocalendar()[1] == current_week - 1:
                prev_week_candles.append(c)

        if prev_week_candles:
            _wh2 = max([c[2] for c in prev_week_candles])
            _wl2 = min([c[3] for c in prev_week_candles])
            _wc2 = prev_week_candles[-1][4]
        else:
            _wh2 = yest_candle[2]
            _wl2 = yest_candle[3]
            _wc2 = yest_candle[4]

        _dh = yest_candle[2]
        _dl = yest_candle[3]
        _dc = yest_candle[4]
        _pdvol = yest_candle[5]

        _dh2 = yest2_candle[2]
        _dl2 = yest2_candle[3]
        _dc2 = yest2_candle[4]

        _currH = today_candle[2]
        _currL = today_candle[3]
        _lc = today_candle[4]
        _dopen = today_candle[1]
        _dvol = today_candle[5]

        _dpiv = (_dh + _dl + _dc) / 3
        _dbc = (_dh + _dl) / 2
        _dtc = max((_dpiv - _dbc) + _dpiv, _dbc)
        _dbc = min((_dpiv - _dbc) + _dpiv, _dbc)
        _rg = _dh - _dl
        _dr1 = 2 * _dpiv - _dl
        _ds1 = 2 * _dpiv - _dh
        _dr2 = _dpiv + _rg
        _ds2 = _dpiv - _rg
        _rg1 = _dr1 - _ds1
        _dr3 = _dr1 + _rg1
        _ds3 = _ds1 - _rg1
        _dr4 = _dr3 + _rg1
        _ds4 = _ds3 - _rg1
        _pdh = _dh
        _pdl = _dl

        _wpiv = (_wh2 + _wl2 + _wc2) / 3
        _wbc = (_wh2 + _wl2) / 2
        _wtc = max((_wpiv - _wbc) + _wpiv, _wbc)
        _wbc = min((_wpiv - _wbc) + _wpiv, _wbc)
        _wr1 = 2 * _wpiv - _wl2
        _ws1 = 2 * _wpiv - _wh2
        _wr2 = _wpiv + (_wh2 - _wl2)
        _ws2 = _wpiv - (_wh2 - _wl2)

        _ypiv = (_dh2 + _dl2 + _dc2) / 3
        _yybc = (_dh2 + _dl2) / 2
        _yytc = max((_ypiv - _yybc) + _ypiv, _yybc)
        _yybc = min((_ypiv - _yybc) + _ypiv, _yybc)
        _icpr = _dtc <= max(_yytc, _yybc) and _dbc >= min(_yytc, _yybc)

        _cpr_width = abs(_dtc - _dbc)
        _narrow_cpr = _cpr_width < (_lc * 0.001) if _lc > 0 else False
        _inside_cpr = _icpr

        dCode = get_daily_code(_lc, _dtc, _dbc, _dr1, _ds1, _pdh, _pdl)
        wCode = get_weekly_code(_lc, _wpiv)
        dZone = get_zone_label(_lc, _dpiv, _dtc, _dbc, _dr1, _dr2, _ds1, _ds2)
        wZone = get_zone_label(_lc, _wpiv, _wtc, _wbc, _wr1, _wr2, _ws1, _ws2)
        bias = get_bias(dCode, wCode)

        _vRatio = (_dvol / (_pdvol * pct_elapsed)) if (_pdvol * pct_elapsed) > 0 else 0.0

        _tol = 0.001
        _reachedTop = _currH >= min(_dr1, _pdh) * (1 - _tol)
        _reachedBot = _currL <= max(_ds1, _pdl) * (1 + _tol)
        _bearRev = _reachedTop and _currH < _dr2 and _lc < _dbc
        _bullRev = _reachedBot and _currL > _ds2 and _lc > _dtc
        _revStr = ""
        if _bearRev and _bullRev: _revStr = "BearRev" if _lc < _dpiv else "BullRev"
        elif _bearRev: _revStr = "BearRev"
        elif _bullRev: _revStr = "BullRev"

        _nl = lvl_eval(_lc, _pdh, _pdl, _dr1, _ds1, 0.003)
        _apB2 = (_nl in ["R1", "PDH"]) and (dCode in ["Neutral", "WBull", "VBull"]) and (wCode in ["Neutral", "WBull", "VBull"])
        _apBr2 = (_nl in ["S1", "PDL"]) and (dCode in ["Neutral", "WBear", "VBear"]) and (wCode in ["Neutral", "WBear", "VBear"])

        def opened_near(op, tc, bc, piv, klvl, phl, t):
            return near_level(op, tc, t) or near_level(op, bc, t) or near_level(op, piv, t) or near_level(op, klvl, t) or near_level(op, phl, t)
        nearDBear = opened_near(_dopen, _dtc, _dbc, _dpiv, _ds1, _wl2, 0.006)
        nearWBear = opened_near(_dopen, _wtc, _wbc, _wpiv, _ws1, _wl2, 0.003)
        nearDBull = opened_near(_dopen, _dtc, _dbc, _dpiv, _dr1, _pdh, 0.006)
        nearWBull = opened_near(_dopen, _wtc, _wbc, _wpiv, _wr1, _wh2, 0.003)
        isBear = bias in ["BEAR", "Both"]
        isBull = bias in ["BULL", "Both"]
        bearSetup = isBear and nearDBear and nearWBear
        bullSetup = isBull and nearDBull and nearWBull
        sig = 1 if (bearSetup and bullSetup) else -1 if bearSetup else 1 if bullSetup else 0
        wDist = 999.0
        if sig != 0:
            l4 = _ws1 if sig == -1 else _wr1
            l5 = _wl2 if sig == -1 else _wh2
            dists = [abs(_dopen-lvl)/lvl for lvl in [_wtc, _wbc, _wpiv, l4, l5] if lvl > 0]
            if dists: wDist = min(dists)
        setupStr = f"{sig}|{wDist}"

        nlPct = get_next_level_dist(dZone, _dtc, _dbc, _dpiv, _dr1, _dr2, _dr3, _dr4, _ds1, _ds2, _ds3, _ds4)

        results.append({
            "symbol": item["symbol"],
            "fyers_symbol": item["fyers"],
            "category": item["cat"],
            "close": round(_lc, 2),
            "live_price": round(_lc, 2),
            "eod_date": now.strftime("%Y-%m-%d"),
            "bias": bias,
            "dZone": dZone,
            "wZone": wZone,
            "icpr": bool(_icpr),
            "setup": setupStr,
            "nl_pct": round(nlPct, 2) if nlPct else None,
            "vRatio": round(_vRatio, 2),
            "revStr": _revStr,
            "apB": bool(_apB2),
            "apBr": bool(_apBr2),
            "narrow_cpr": bool(_narrow_cpr),
            "inside_cpr": bool(_inside_cpr),
            # Full pivot levels for frontend tick-by-tick calc
            "tc": round(_dtc, 2),
            "bc": round(_dbc, 2),
            "pivot": round(_dpiv, 2),
            "r1": round(_dr1, 2),
            "r2": round(_dr2, 2),
            "s1": round(_ds1, 2),
            "s2": round(_ds2, 2),
            "dr3": round(_dr3, 2),
            "dr4": round(_dr4, 2),
            "ds3": round(_ds3, 2),
            "ds4": round(_ds4, 2),
            "pdh": round(_pdh, 2),
            "pdl": round(_pdl, 2),
            "weekly_pivot": round(_wpiv, 2),
            "weekly_tc": round(_wtc, 2),
            "weekly_bc": round(_wbc, 2),
            "weekly_r1": round(_wr1, 2),
            "weekly_s1": round(_ws1, 2),
            "wh2": round(_wh2, 2),
            "wl2": round(_wl2, 2),
            "d_open": round(_dopen, 2)
        })

    return results


def main(args):
    ist = pytz.timezone('Asia/Kolkata')

    fyers = get_fyers_client()
    if not fyers:
        return

    fno_symbols = get_nse_fno_symbols()
    indices = {
        "NIFTY 50": "NSE:NIFTY50-INDEX",
        "BANK NIFTY": "NSE:NIFTYBANK-INDEX",
        "NIFTY IT": "NSE:NIFTYIT-INDEX",
        "NIFTY FIN SVC": "NSE:FINNIFTY-INDEX"
    }

    targets = [{"symbol": k, "fyers": v, "cat": "Indices"} for k, v in indices.items()]
    targets += [{"symbol": s, "fyers": f"NSE:{s}-EQ", "cat": "FNO"} for s in fno_symbols]
    fyers_symbols = [t["fyers"] for t in targets]

    now = datetime.now(ist)
    range_to = now.strftime("%Y-%m-%d")
    range_from = (now - timedelta(days=25)).strftime("%Y-%m-%d")
    history_map = load_history_data(fyers, targets, range_from, range_to)

    while True:
        now = datetime.now(ist)
        print("Fetching Live Quotes for today's data...")
        quotes_data = fetch_live_quotes(fyers, fyers_symbols)

        startOfDay = now.replace(hour=9, minute=15, second=0, microsecond=0)
        current_time = now
        elapsed_mins = max(1, int((current_time - startOfDay).total_seconds() / 60))
        elapsed_mins = min(elapsed_mins, 375)
        pct_elapsed = max(0.01, elapsed_mins / 375.0)

        print("Analyzing live data and generating output...")
        results = build_results(now, targets, history_map, quotes_data, pct_elapsed)

        output = {
            "generated_at": now.strftime("%Y-%m-%d %H:%M:%S IST"),
            "total_scanned": len(targets),
            "results": results,
        }

        # If it's >= 4 PM IST, this data is for tomorrow's session, else today's
        is_after_4pm = now.hour >= 16
        session_date = (now + timedelta(days=1)).strftime("%Y-%m-%d") if is_after_4pm else now.strftime("%Y-%m-%d")
        
        filename = f"cpr_data_{session_date}.json"
        
        # Save historical/dated file
        with open(filename, "w") as f:
            json.dump(output, f, indent=4)
            
        # Also update the main cpr_data.json for backwards compatibility or default loading
        with open("cpr_data.json", "w") as f:
            json.dump(output, f, indent=4)
            
        print(f"\n[DONE] {len(results)} matches saved to {filename} and cpr_data.json")

        # Update available_dates.json
        available_dates = []
        if os.path.exists("available_dates.json"):
            try:
                with open("available_dates.json", "r") as f:
                    available_dates = json.load(f)
            except:
                pass
        
        if session_date not in available_dates:
            available_dates.append(session_date)
            # Sort dates descending
            available_dates.sort(reverse=True)
            with open("available_dates.json", "w") as f:
                json.dump(available_dates, f, indent=4)

        if args.interval <= 0:
            break
        print(f"Sleeping {args.interval} seconds before next update...\n")
        time.sleep(args.interval)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate CPR screener data with optional live polling")
    parser.add_argument("--interval", type=float, default=0.0, help="Poll interval in seconds for live updates. 0 means run once.")
    args = parser.parse_args()
    main(args)
