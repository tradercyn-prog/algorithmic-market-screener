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
    
    if any("MACD" in ind for ind in needed_indicators):
        macd = ta.macd(df['close'])
        if macd is not None and not macd.empty:
            df['MACD_LINE'] = macd.iloc[:, 0]
            df['MACD_HIST'] = macd.iloc[:, 1]
            df['MACD_SIGNAL'] = macd.iloc[:, 2]
    
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

    # --- Candlestick Patterns (PURE MATH REPLACEMENT) ---
    pattern_requested = any("Pattern:" in ind for ind in needed_indicators)
    
    if pattern_requested:
        O, H, L, C = df['open'], df['high'], df['low'], df['close']
        O1, H1, L1, C1 = O.shift(1), H.shift(1), L.shift(1), C.shift(1)
        O2, C2 = O.shift(2), C.shift(2)

        body = (C - O).abs()
        body1 = (C1 - O1).abs()
        candle_range = H - L
        
        lower_wick = df[['open', 'close']].min(axis=1) - L
        upper_wick = H - df[['open', 'close']].max(axis=1)
        
        is_bull = C > O
        is_bear = C < O
        is_bull1 = C1 > O1
        is_bear1 = C1 < O1

        if "Pattern: Doji" in needed_indicators:
            df['CDL_DOJI'] = np.where((candle_range > 0) & (body <= (candle_range * 0.1)), 100, 0)
        if "Pattern: Hammer" in needed_indicators:
            df['CDL_HAMMER'] = np.where((candle_range > 0) & (lower_wick >= (body * 2)) & (upper_wick <= (candle_range * 0.1)), 100, 0)
        if "Pattern: Inverted Hammer" in needed_indicators:
            df['CDL_INVERTEDHAMMER'] = np.where((candle_range > 0) & (upper_wick >= (body * 2)) & (lower_wick <= (candle_range * 0.1)), 100, 0)
        if "Pattern: Shooting Star" in needed_indicators:
            df['CDL_SHOOTINGSTAR'] = np.where(is_bear & (candle_range > 0) & (upper_wick >= (body * 2)) & (lower_wick <= (candle_range * 0.1)), 100, 0)
        if "Pattern: Hanging Man" in needed_indicators:
            df['CDL_HANGINGMAN'] = np.where(is_bear & (candle_range > 0) & (lower_wick >= (body * 2)) & (upper_wick <= (candle_range * 0.1)), 100, 0)
        if "Pattern: Engulfing" in needed_indicators:
            bull_engulf = is_bear1 & is_bull & (C > O1) & (O < C1)
            bear_engulf = is_bull1 & is_bear & (O > C1) & (C < O1)
            df['CDL_ENGULFING'] = np.where(bull_engulf | bear_engulf, 100, 0)
        if "Pattern: Harami" in needed_indicators:
            bull_harami = is_bear1 & is_bull & (O > C1) & (C < O1)
            bear_harami = is_bull1 & is_bear & (O < C1) & (C > O1)
            df['CDL_HARAMI'] = np.where(bull_harami | bear_harami, 100, 0)
        if "Pattern: Morning Star" in needed_indicators:
            star_doji = (body1 <= (H1 - L1) * 0.1)
            df['CDL_MORNINGSTAR'] = np.where(is_bear.shift(2) & star_doji & is_bull & (C > (O2 + C2)/2), 100, 0)
        if "Pattern: Evening Star" in needed_indicators:
            star_doji = (body1 <= (H1 - L1) * 0.1)
            df['CDL_EVENINGSTAR'] = np.where(is_bull.shift(2) & star_doji & is_bear & (C < (O2 + C2)/2), 100, 0)
        if "Pattern: Marubozu" in needed_indicators:
            df['CDL_MARUBOZU'] = np.where((body > 0) & (upper_wick <= (body * 0.05)) & (lower_wick <= (body * 0.05)), 100, 0)
        if "Pattern: Piercing Line" in needed_indicators:
            df['CDL_PIERCING'] = np.where(is_bear1 & is_bull & (O < L1) & (C > (O1 + C1)/2), 100, 0)
        if "Pattern: Dark Cloud Cover" in needed_indicators:
            df['CDL_DARKCLOUDCOVER'] = np.where(is_bull1 & is_bear & (O > H1) & (C < (O1 + C1)/2), 100, 0)
        if "Pattern: 3 White Soldiers" in needed_indicators:
            df['CDL_3WHITESOLDIERS'] = np.where(is_bull & is_bull1 & is_bull.shift(2) & (C > C1) & (C1 > C.shift(2)), 100, 0)
        if "Pattern: 3 Black Crows" in needed_indicators:
            df['CDL_3BLACKCROWS'] = np.where(is_bear & is_bear1 & is_bear.shift(2) & (C < C1) & (C1 < C.shift(2)), 100, 0)

    # --- Consecutive Streaks ---
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
        "MACD Line": "MACD_LINE", "MACD Signal": "MACD_SIGNAL", "MACD Histogram": "MACD_HIST",
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
                if pd.isna(ind_val) or ind_val == 0: 
                    passed_all_rules = False
            else:
                passed_all_rules = False
            
            if not passed_all_rules: 
                break
            continue 
        
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