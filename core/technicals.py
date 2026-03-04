import pandas as pd
import pandas_ta as ta
import numpy as np

def apply_indicators(df, rules):
    """Dynamically calculates technical indicators required by user-defined rules."""
    if df.empty or len(df) < 50: 
        return df

    needed_indicators = set([rule["indicator"] for rule in rules] + [rule["value"] for rule in rules])

    # --- Trend (Moving Averages) ---
    if "SMA 10" in needed_indicators: df['SMA_10'] = ta.sma(df['close'], length=10)
    if "SMA 20" in needed_indicators: df['SMA_20'] = ta.sma(df['close'], length=20)
    if "SMA 50" in needed_indicators: df['SMA_50'] = ta.sma(df['close'], length=50)
    if "SMA 200" in needed_indicators: df['SMA_200'] = ta.sma(df['close'], length=200)
    
    if "EMA 10" in needed_indicators: df['EMA_10'] = ta.ema(df['close'], length=10)
    if "EMA 20" in needed_indicators: df['EMA_20'] = ta.ema(df['close'], length=20)
    if "EMA 50" in needed_indicators: df['EMA_50'] = ta.ema(df['close'], length=50)
    if "EMA 200" in needed_indicators: df['EMA_200'] = ta.ema(df['close'], length=200)
    
    if "VWAP" in needed_indicators: df['VWAP'] = ta.vwap(df['high'], df['low'], df['close'], df['volume'])
    
    # --- Oscillators & Momentum ---
    if "RSI (14)" in needed_indicators: df['RSI_14'] = ta.rsi(df['close'], length=14)
    if "RSI (2)" in needed_indicators: df['RSI_2'] = ta.rsi(df['close'], length=2)
    
    # --- Volatility & Dynamic Support/Resistance ---
    if "Bollinger Bands (Lower)" in needed_indicators or "Bollinger Bands (Upper)" in needed_indicators:
        bbands = ta.bbands(df['close'], length=20, std=2)
        if bbands is not None:
            df['BB_LOWER'] = bbands.iloc[:, 0] 
            df['BB_UPPER'] = bbands.iloc[:, 2] 
            
    if "SuperTrend" in needed_indicators:
        sti = ta.supertrend(df['high'], df['low'], df['close'], length=7, multiplier=3.0)
        if sti is not None:
            df['SUPERTREND'] = sti.iloc[:, 0] 

    # --- Candlestick Patterns & Consecutive Streaks ---
    pattern_mapping = {
        "Pattern: Doji": "doji", "Pattern: Hammer": "hammer", "Pattern: Inverted Hammer": "invertedhammer",
        "Pattern: Shooting Star": "shootingstar", "Pattern: Hanging Man": "hangingman", "Pattern: Engulfing": "engulfing",
        "Pattern: Harami": "harami", "Pattern: Morning Star": "morningstar", "Pattern: Evening Star": "eveningstar",
        "Pattern: Marubozu": "marubozu", "Pattern: Piercing Line": "piercing", "Pattern: Dark Cloud Cover": "darkcloudcover",
        "Pattern: 3 White Soldiers": "3whitesoldiers", "Pattern: 3 Black Crows": "3blackcrows"
    }

    for ui_name, ta_name in pattern_mapping.items():
        if ui_name in needed_indicators:
            res = ta.cdl_pattern(df['open'], df['high'], df['low'], df['close'], name=ta_name)
            if res is not None and not res.empty: 
                df[f'CDL_{ta_name.upper()}'] = res.iloc[:, 0]
    
    if "Consecutive Bull" in needed_indicators:
        is_bull = (df['close'] > df['open']).astype(int)
        df['CONSEC_BULL'] = is_bull.groupby((is_bull == 0).cumsum()).cumsum()
        
    if "Consecutive Bear" in needed_indicators:
        is_bear = (df['close'] < df['open']).astype(int)
        df['CONSEC_BEAR'] = is_bear.groupby((is_bear == 0).cumsum()).cumsum()

    return df

def map_indicator_to_column(indicator_name):
    """Translates the UI dropdown selection to the DataFrame column name."""
    mapping = {
        "Price": "close", "Volume": "volume", "VWAP": "VWAP",
        "SMA 10": "SMA_10", "SMA 20": "SMA_20", "SMA 50": "SMA_50", "SMA 200": "SMA_200",
        "EMA 10": "EMA_10", "EMA 20": "EMA_20", "EMA 50": "EMA_50", "EMA 200": "EMA_200",
        "RSI (14)": "RSI_14", "RSI (2)": "RSI_2", "SuperTrend": "SUPERTREND",
        "Bollinger Bands (Lower)": "BB_LOWER", "Bollinger Bands (Upper)": "BB_UPPER",
        "Consecutive Bull": "CONSEC_BULL", "Consecutive Bear": "CONSEC_BEAR",
        
        # Candlestick Map
        "Pattern: Doji": "CDL_DOJI", "Pattern: Hammer": "CDL_HAMMER", 
        "Pattern: Inverted Hammer": "CDL_INVERTEDHAMMER", "Pattern: Shooting Star": "CDL_SHOOTINGSTAR", 
        "Pattern: Hanging Man": "CDL_HANGINGMAN", "Pattern: Engulfing": "CDL_ENGULFING",
        "Pattern: Harami": "CDL_HARAMI", "Pattern: Morning Star": "CDL_MORNINGSTAR", 
        "Pattern: Evening Star": "CDL_EVENINGSTAR", "Pattern: Marubozu": "CDL_MARUBOZU", 
        "Pattern: Piercing Line": "CDL_PIERCING", "Pattern: Dark Cloud Cover": "CDL_DARKCLOUDCOVER",
        "Pattern: 3 White Soldiers": "CDL_3WHITESOLDIERS", "Pattern: 3 Black Crows": "CDL_3BLACKCROWS"
    }
    return mapping.get(indicator_name, None)

def evaluate_screener_rules(df, rules):
    """Evaluates the applied indicators against the custom rules."""
    df = apply_indicators(df, rules)
    
    if df.empty or len(df) < 2:
        return False, None

    latest = df.iloc[-1]
    prev = df.iloc[-2] 
    passed_all_rules = True

    for rule in rules:
        ind_col = map_indicator_to_column(rule["indicator"])
        
        # FIX: If the indicator failed to generate, fail the stock
        if not ind_col or ind_col not in latest:
            passed_all_rules = False
            break

        ind_val = latest[ind_col]
        cond = rule["condition"] 

        # 2. Candlestick Pattern Logic (MOVED TO THE TOP!)
        if "Pattern:" in rule["indicator"]:
            if cond == "==" and str(rule["value"]).lower() == "true":
                # pandas_ta returns 0 if there is no pattern
                if pd.isna(ind_val) or ind_val == 0: 
                    passed_all_rules = False
            else:
                passed_all_rules = False
            
            if not passed_all_rules: 
                break
            continue # Skip the math checks below and move to the next rule!
        
        # 3. Target Math Logic
        target_col = map_indicator_to_column(rule["value"])
        if target_col and target_col in latest:
            compare_val = latest[target_col]
            prev_compare_val = prev[target_col]
        else:
            try:
                compare_val = float(rule["value"])
                prev_compare_val = compare_val 
            except ValueError:
                # CRITICAL FIX: Instantly fail the stock instead of skipping the rule!
                passed_all_rules = False
                break 

        # --- SAFETY GUARD: Prevent NaNs from passing ---
        if pd.isna(ind_val) or pd.isna(compare_val) or pd.isna(prev[ind_col]) or pd.isna(prev_compare_val):
            passed_all_rules = False
            break

        # 4. Standard Logic Engine
        if cond == ">":
            if not (ind_val > compare_val): passed_all_rules = False
        elif cond == "<":
            if not (ind_val < compare_val): passed_all_rules = False
        elif cond == "==":
            if not (ind_val == compare_val): passed_all_rules = False
        elif cond == "Crosses Above":
            if not (prev[ind_col] <= prev_compare_val and ind_val > compare_val): passed_all_rules = False
        elif cond == "Crosses Below":
            if not (prev[ind_col] >= prev_compare_val and ind_val < compare_val): passed_all_rules = False

        if not passed_all_rules:
            break 

    return passed_all_rules, latest.to_dict()