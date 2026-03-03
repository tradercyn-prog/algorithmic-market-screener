import os
import requests
import pandas as pd
import yfinance as yf
import time
import warnings

# Suppress pandas warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

# Create a local directory to hold the market snapshot
DATA_DIR = "market_data"
os.makedirs(DATA_DIR, exist_ok=True)
SNAPSHOT_FILE = os.path.join(DATA_DIR, "master_snapshot.csv")

def get_all_us_tickers():
    """Retrieves all active U.S. stock tickers from the SEC database."""
    print("Retrieving ticker list from SEC Database...")
    url = "https://www.sec.gov/files/company_tickers.json"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        tickers = [company['ticker'] for company in data.values()]
        unique_tickers = sorted(list(set(tickers)))
        print(f"Success: {len(unique_tickers)} equities found.")
        return unique_tickers
    except Exception as e:
        print(f"SEC Request Failed: {e}")
        return ["SPY", "QQQ", "AAPL", "MSFT"]

def download_market_snapshot():
    """Downloads the market data in chunks to respect API rate limits."""
    tickers = get_all_us_tickers()
    clean_tickers = [t.replace(".", "-") for t in tickers]
    
    print("\nInitiating bulk data download...")
    print(f"Targeting {len(clean_tickers)} assets...\n")
    
    start_time = time.time()
    all_data = []
    chunk_size = 1000
    
    for i in range(0, len(clean_tickers), chunk_size):
        chunk = clean_tickers[i:i + chunk_size]
        print(f"   [Status] Downloading batch {i//chunk_size + 1} ({len(chunk)} assets)...")
        
        # threads=False forces sequential downloading
        df = yf.download(chunk, period="1y", interval="1d", threads=False)
        
        if not df.empty:
            try:
                if isinstance(df.columns, pd.MultiIndex):
                    stacked = df.stack(level=1).reset_index()
                else:
                    stacked = df.reset_index()
                    stacked['Ticker'] = chunk[0]
                    
                stacked.columns = stacked.columns.str.lower()
                all_data.append(stacked)
            except Exception as e:
                pass 
                
        # Delay to avoid rate limits
        time.sleep(1) 

    if all_data:
        print("\nCompiling master dataframe...")
        master_df = pd.concat(all_data, ignore_index=True)
        
        expected = ['date', 'ticker', 'open', 'high', 'low', 'close', 'volume']
        existing = [c for c in expected if c in master_df.columns]
        master_df = master_df[existing]
        
        master_df.dropna(subset=['close'], inplace=True)
        master_df.to_csv(SNAPSHOT_FILE, index=False)
        
        unique_count = master_df['ticker'].nunique()
        elapsed_time = round(time.time() - start_time, 2)
        
        print(f"\nDownload complete!")
        print(f"Total Unique Tickers Saved: {unique_count:,}")
        print(f"File saved to: {SNAPSHOT_FILE}")
        print(f"Time Elapsed: {elapsed_time} seconds.")
    else:
        print("\nError: No market data could be compiled.")

if __name__ == "__main__":
    download_market_snapshot()