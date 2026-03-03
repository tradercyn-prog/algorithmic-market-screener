import pandas as pd
import requests
import yfinance as yf
import streamlit as st
import os
from datetime import datetime

def fetch_crypto_data(symbol="BTCUSDT", interval="1d", limit=300):
    url = "https://api.binance.com/api/v3/klines"
    params = {
        "symbol": symbol.upper(),
        "interval": interval,
        "limit": limit
    }
     
    try:
        response = requests.get(url, params=params)
        response.raise_for_status() 
        data = response.json()
        
        # Extract primary OHLCV columns from Binance response
        df = pd.DataFrame(data, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume', 
            'close_time', 'qav', 'num_trades', 'taker_base_vol', 'taker_quote_vol', 'ignore'
        ])
        
        # Format dataframe structure
        df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        
        # Cast string values to numeric for calculation
        df = df.astype(float)
        
        return df

    except requests.exceptions.RequestException as e:
        print(f"Error fetching data for {symbol}: {e}")
        return pd.DataFrame() 

def fetch_stock_data(symbol="SPY", period="1y", interval="1d"):
    """
    Fetches historical stock data using yfinance.
    Returns a clean DataFrame ready for technical analysis.
    """
    try:
        ticker = yf.Ticker(symbol.upper())
        df = ticker.history(period=period, interval=interval)
        
        if df.empty:
            return df
            
        # Standardize column naming convention
        df.columns = df.columns.str.lower()
        df = df[['open', 'high', 'low', 'close', 'volume']]
        
        return df
        
    except Exception as e:
        print(f"Error fetching stock data for {symbol}: {e}")
        return pd.DataFrame()
    
@st.cache_data
def load_local_matrix():
    """Loads the local market database into memory for rapid scanning."""
    file_path = "market_data/master_snapshot.csv"
    if not os.path.exists(file_path):
        return None
        
    print("Loading database into RAM...")
    df = pd.read_csv(file_path)
    
    # Set index to Date for accurate time-series operations
    if 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'], utc=True)
        df.set_index('Date', inplace=True)
        
    return df

def fetch_local_ticker(ticker, master_df):
    """Extracts a single ticker from the master database."""
    if master_df is None or master_df.empty:
        return pd.DataFrame()
        
    # Filter master dataframe for specific ticker
    ticker_df = master_df[master_df['ticker'] == ticker].copy()
    
    # Standardize columns for the analysis engine
    if not ticker_df.empty:
        ticker_df = ticker_df[['open', 'high', 'low', 'close', 'volume']]
        
    return ticker_df

@st.cache_data(ttl=900)
def fetch_macro_metrics(asset_type):
    """Pulls macro data based on the active market selection."""
    metrics = {
        "M1_Label": "Loading...", "M1_Val": "--", "M1_Delta": "",
        "M2_Label": "Loading...", "M2_Val": "--", "M2_Delta": "",
        "M3_Label": "Loading...", "M3_Val": "--", "M3_Delta": ""
    }
    
    try:
        if asset_type == "Equities (Stocks)":
            # 1. SPY Trend
            spy = yf.Ticker("SPY").history(period="3mo")
            if not spy.empty:
                curr_spy = spy['Close'].iloc[-1]
                sma_50 = spy['Close'].rolling(window=50).mean().iloc[-1]
                metrics["M1_Label"] = "SPY Trend"
                metrics["M1_Val"] = "Bullish" if curr_spy > sma_50 else "Bearish"
                metrics["M1_Delta"] = "Above 50 SMA" if curr_spy > sma_50 else "Below 50 SMA"

            # 2. VIX (Market Volatility)
            vix = yf.Ticker("^VIX").history(period="5d")
            if not vix.empty:
                curr_vix = vix['Close'].iloc[-1]
                prev_vix = vix['Close'].iloc[-2]
                metrics["M2_Label"] = "Market Vol (VIX)"
                metrics["M2_Val"] = f"{curr_vix:.2f}"
                metrics["M2_Delta"] = f"{curr_vix - prev_vix:+.2f}"
                
            # 3. NASDAQ Trend
            qqq = yf.Ticker("QQQ").history(period="5d")
            if not qqq.empty:
                curr_q = qqq['Close'].iloc[-1]
                prev_q = qqq['Close'].iloc[-2]
                metrics["M3_Label"] = "NASDAQ (QQQ)"
                metrics["M3_Val"] = f"${curr_q:.2f}"
                metrics["M3_Delta"] = f"{((curr_q - prev_q) / prev_q) * 100:+.2f}%"

        else:
            # 1. Bitcoin Live via Binance
            btc_data = requests.get("https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT").json()
            metrics["M1_Label"] = "Bitcoin (BTC)"
            metrics["M1_Val"] = f"${float(btc_data['lastPrice']):,.0f}"
            metrics["M1_Delta"] = f"{float(btc_data['priceChangePercent']):+.2f}%"

            # 2. Ethereum Live via Binance
            eth_data = requests.get("https://api.binance.com/api/v3/ticker/24hr?symbol=ETHUSDT").json()
            metrics["M2_Label"] = "Ethereum (ETH)"
            metrics["M2_Val"] = f"${float(eth_data['lastPrice']):,.0f}"
            metrics["M2_Delta"] = f"{float(eth_data['priceChangePercent']):+.2f}%"

            # 3. BTC Dominance via CoinGecko
            cg_resp = requests.get("https://api.coingecko.com/api/v3/global").json()
            btc_dom = cg_resp['data']['market_cap_percentage']['btc']
            metrics["M3_Label"] = "BTC Dominance"
            metrics["M3_Val"] = f"{btc_dom:.1f}%"
            metrics["M3_Delta"] = "Live"

    except Exception as e:
        print(f"Metrics fetch failed: {e}")
        pass

    return metrics