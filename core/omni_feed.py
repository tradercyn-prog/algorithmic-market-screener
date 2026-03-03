import yfinance as yf
import pandas as pd
import pandas_ta as ta
from core.data_fetcher import fetch_stock_data, fetch_crypto_data

def generate_omni_feed(ticker, asset_type):
    """
    Compiles live technical data and fundamental news into a raw text string 
    for AI analysis.
    """
    payload = f"--- ASSET: {ticker.upper()} ---\n\n"
    
    # -----------------------------------------
    # 1. TECHNICAL DATA 
    # -----------------------------------------
    payload += "1. TECHNICAL INDICATORS (Latest Daily Close):\n"
    
    if asset_type == "Equities (Stocks)":
        df = fetch_stock_data(ticker, period="1y")
    else:
        df = fetch_crypto_data(ticker)
        
    if not df.empty:
        df['SMA_20'] = ta.sma(df['close'], length=20)
        df['SMA_50'] = ta.sma(df['close'], length=50)
        df['SMA_200'] = ta.sma(df['close'], length=200)
        df['RSI_14'] = ta.rsi(df['close'], length=14)
        
        macd = ta.macd(df['close'])
        if macd is not None and not macd.empty:
            df['MACD'] = macd[macd.columns[0]]
            df['MACD_SIGNAL'] = macd[macd.columns[2]]
        
        latest = df.iloc[-1]
        
        payload += f"Current Price: {latest.get('close', 0):.2f}\n"
        payload += f"Volume: {latest.get('volume', 0):,.0f}\n"
        payload += f"SMA 20: {latest.get('SMA_20', 0):.2f}\n"
        payload += f"SMA 50: {latest.get('SMA_50', 0):.2f}\n"
        payload += f"SMA 200: {latest.get('SMA_200', 0):.2f}\n"
        payload += f"RSI (14): {latest.get('RSI_14', 0):.2f}\n"
        payload += f"MACD Line: {latest.get('MACD', 0):.2f} | Signal: {latest.get('MACD_SIGNAL', 0):.2f}\n\n"
    else:
        payload += "Technical data unavailable or asset delisted.\n\n"
        

    # -----------------------------------------
    # 2. FUNDAMENTAL NEWS 
    # -----------------------------------------
    payload += "2. LATEST FUNDAMENTAL NEWS:\n"
    news_string = ""
    
    if asset_type == "Equities (Stocks)":
        try:
            raw_news = yf.Ticker(ticker).news
            if raw_news:
                for item in raw_news[:4]: 
                    content = item.get('content', item) 
                    title = content.get('title', '')
                    
                    publisher = content.get('provider', {}).get('displayName', '')
                    if not publisher:
                        publisher = content.get('publisher', 'Financial Press')
                        
                    if title:
                        news_string += f"- {title} ({publisher})\n"
                        
            if not news_string.strip():
                news_string = "No major news catalysts found in the last 24 hours.\n"
                
        except Exception as e:
            news_string = f"News API offline. Rely solely on technicals. (Error: {e})\n"
    else:
        news_string = "Cryptocurrency selected. Rely strictly on technicals and momentum.\n"
        
    payload += news_string
    
    return payload