import yfinance as yf
import pandas as pd
import json
from datetime import datetime
import pytz

# Group symbols by category
SYMBOLS = {
    "FNO": [
        "AARTIIND.NS", "ABB.NS", "ABBOTINDIA.NS", "ABCAPITAL.NS", "ABFRL.NS",
        "ACC.NS", "ADANIENT.NS", "ADANIPORTS.NS", "ALKEM.NS", "AMBUJACEM.NS",
        "ANGELONE.NS", "APLAPOLLO.NS", "APOLLOHOSP.NS", "APOLLOTYRE.NS",
        "ASHOKLEY.NS", "ASIANPAINT.NS", "ASTRAL.NS", "AUROPHARMA.NS",
        "AXISBANK.NS", "BAJAJ-AUTO.NS", "BAJAJFINSV.NS", "BAJFINANCE.NS",
        "BALKRISIND.NS", "BANDHANBNK.NS", "BANKBARODA.NS", "BANKINDIA.NS",
        "BATAINDIA.NS", "BEL.NS", "BERGEPAINT.NS", "BHARATFORG.NS",
        "BHARTIARTL.NS", "BHEL.NS", "BIOCON.NS", "BLUESTARCO.NS",
        "BOSCHLTD.NS", "BPCL.NS", "BRITANNIA.NS", "CAMS.NS",
        "CANFINHOME.NS", "CANBK.NS", "CDSL.NS", "CEATLTD.NS",
        "CGPOWER.NS", "CHAMBLFERT.NS", "CHOLAFIN.NS", "CIPLA.NS",
        "COALINDIA.NS", "COCHINSHIP.NS", "COFORGE.NS", "COLPAL.NS",
        "CONCOR.NS", "COROMANDEL.NS", "CROMPTON.NS", "CUMMINSIND.NS",
        "CYIENT.NS", "DABUR.NS", "DALBHARAT.NS", "DEEPAKNTR.NS",
        "DIVISLAB.NS", "DIXON.NS", "DLF.NS", "DRREDDY.NS",
        "EICHERMOT.NS", "ESCORTS.NS", "FEDERALBNK.NS", "FORTIS.NS",
        "GAIL.NS", "GLAND.NS", "GLENMARK.NS", "GMRAIRPORT.NS",
        "GODREJCP.NS", "GODREJPROP.NS", "GRANULES.NS", "GRASIM.NS",
        "HAL.NS", "HAVELLS.NS", "HCLTECH.NS", "HDFCAMC.NS",
        "HDFCBANK.NS", "HDFCLIFE.NS", "HEROMOTOCO.NS", "HINDALCO.NS",
        "HINDCOPPER.NS", "HINDPETRO.NS", "HINDUNILVR.NS", "HINDZINC.NS",
        "HUDCO.NS", "HYUNDAI.NS", "ICICIGI.NS", "ICICIBANK.NS",
        "ICICIPRULI.NS", "IDFCFIRSTB.NS", "IEX.NS",
        "INDHOTEL.NS", "INDIGO.NS", "INDUSINDBK.NS",
        "INDUSTOWER.NS", "INFY.NS", "IOC.NS", "IRCTC.NS",
        "IRFC.NS", "ITC.NS", "JINDALSTEL.NS", "JSWSTEEL.NS",
        "JUBLFOOD.NS", "KAJARIACER.NS", "KOTAKBANK.NS", "KPITTECH.NS",
        "LTF.NS", "LAURUSLABS.NS", "LICHSGFIN.NS", "LT.NS",
        "LTTS.NS", "LUPIN.NS", "M&M.NS",
        "M&MFIN.NS", "MANAPPURAM.NS", "MARICO.NS", "MARUTI.NS",
        "MCX.NS", "MFSL.NS", "MPHASIS.NS", "MRF.NS",
        "MUTHOOTFIN.NS", "NATIONALUM.NS", "NAUKRI.NS", "NAVINFLUOR.NS",
        "NESTLEIND.NS", "NHPC.NS", "NMDC.NS", "NTPC.NS",
        "NYKAA.NS", "OBEROIRLTY.NS", "OFSS.NS", "ONGC.NS",
        "PAGEIND.NS", "PERSISTENT.NS", "PETRONET.NS",
        "PFC.NS", "PIIND.NS", "PNB.NS", "PNBHOUSING.NS",
        "POLYCAB.NS", "POWERGRID.NS", "PRESTIGE.NS", "PVRINOX.NS",
        "RBLBANK.NS", "RECLTD.NS", "RELIANCE.NS", "RVNL.NS",
        "SAIL.NS", "SBICARD.NS", "SBILIFE.NS", "SBIN.NS",
        "SHREECEM.NS", "SHRIRAMFIN.NS", "SIEMENS.NS", "SJVN.NS",
        "SONACOMS.NS", "SRF.NS", "STARHEALTH.NS", "SUNPHARMA.NS",
        "SYNGENE.NS", "TATACHEM.NS", "TATACOMM.NS", "TATAELXSI.NS",
        "TATAPOWER.NS", "TATASTEEL.NS", "TATATECH.NS",
        "TCS.NS", "TECHM.NS", "TIINDIA.NS", "TITAN.NS",
        "TORNTPHARM.NS", "TRENT.NS", "TVSMOTOR.NS", "ULTRACEMCO.NS",
        "UNIONBANK.NS", "UPL.NS", "VEDL.NS", "VOLTAS.NS",
        "WIPRO.NS", "YESBANK.NS", "ETERNAL.NS", "ZYDUSLIFE.NS",
    ],
    "Indices": [
        "^NSEI",       # Nifty 50
        "^NSEBANK",    # Bank Nifty
        "^CNXIT",      # Nifty IT
        "^CNXFMCG",    # Nifty FMCG
        "^CNXPHARMA",  # Nifty Pharma
        "^CNXAUTO",    # Nifty Auto
        "^CNXMETAL",   # Nifty Metal
        "^CNXINFRA",   # Nifty Infra
        "NIFTY_FIN_SERVICE.NS",  # Nifty Financial Services
    ],
    "Commodities": [
        "CL=F",   # Crude Oil
        "GC=F",   # Gold
        "SI=F",   # Silver
        "NG=F",   # Natural Gas
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
            
            # Check if last row is today and market hasn't closed (assuming 16:00 IST for all to be safe)
            ist = pytz.timezone('Asia/Kolkata')
            now = datetime.now(ist)
            
            last_date = df.index[-1].date()
            if last_date == now.date() and now.hour < 16:
                # Drop the live/incomplete today's row
                df = df.iloc[:-1]
                
            if len(df) < 2:
                print(f"Not enough finalized data for {ticker}")
                continue
                
            # Get last 2 trading days
            yesterday = df.iloc[-2]
            today = df.iloc[-1]
            
            today_close = today['Close']
            
            # Extract EOD Date
            eod_date = today.name.strftime('%Y-%m-%d')
            
            # Calculate Today's CPR (using yesterday's data)
            today_cpr = calculate_cpr(yesterday['High'], yesterday['Low'], yesterday['Close'])
            
            # Calculate Tomorrow's CPR (using today's data)
            tom_cpr = calculate_cpr(today['High'], today['Low'], today['Close'])
            
            # Conditions
            # 1. Narrow CPR: Width < 0.1% of Close
            is_narrow = tom_cpr['width'] < (today_close * 0.001)
            
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
                if name == "^CNXFMCG": name = "NIFTY FMCG"
                if name == "^CNXPHARMA": name = "NIFTY PHARMA"
                if name == "^CNXAUTO": name = "NIFTY AUTO"
                if name == "^CNXMETAL": name = "NIFTY METAL"
                if name == "^CNXINFRA": name = "NIFTY INFRA"
                if name == "NIFTY_FIN_SERVICE": name = "NIFTY FIN SVC"
                if name == "ETERNAL": name = "ZOMATO (ETERNAL)"
                if name == "CL": name = "CRUDE OIL"
                if name == "GC": name = "GOLD"
                if name == "SI": name = "SILVER"
                if name == "NG": name = "NATURAL GAS"
                
                results.append({
                    "symbol": name,
                    "ticker": ticker,
                    "category": category_map[ticker],
                    "close": round(today_close, 2),
                    "eod_date": eod_date,
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
