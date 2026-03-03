import streamlit as st
import pandas as pd
import time
import plotly.graph_objects as go
from dotenv import load_dotenv
from components.ai_analyzer import generate_deep_dive
from core.data_fetcher import fetch_crypto_data, fetch_stock_data, load_local_matrix, fetch_local_ticker, fetch_macro_metrics

# Load the hidden API key
load_dotenv()

# Import core analysis modules
from core.data_fetcher import fetch_crypto_data, fetch_stock_data, load_local_matrix, fetch_local_ticker
from core.technicals import apply_indicators, evaluate_screener_rules, map_indicator_to_column

# 1. Page Configuration
st.set_page_config(
    page_title="Market Screener & AI Analyst",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Custom CSS Injection
def load_css(file_name):
    try:
        with open(file_name) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        pass # Fail silently and use default if file isn't found

# 3. Default Ticker Universes (Keep it small for fast demo scans)
CRYPTO_TICKERS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "ADAUSDT", "XRPUSDT", "DOTUSDT", "DOGEUSDT"]
STOCK_TICKERS = ["AAPL", "MSFT", "NVDA", "TSLA", "META", "AMZN", "GOOGL"]

def main():
    # --- SIDEBAR: THE DYNAMIC RULE BUILDER ---
    with st.sidebar:
        # Lock LCARS as the default startup theme in the memory bank
        if "active_theme" not in st.session_state:
            st.session_state.active_theme = "Star Trek: TNG (LCARS)"
            
        st.title("Scan Parameters")
        asset_type = st.selectbox("Market", ["Equities (Stocks)", "Cryptocurrency"])
        
        # --- THE DATABASE UPLINK BUTTON ---
        if asset_type == "Equities (Stocks)":
            if st.button("🔄 Update Local Market Database", use_container_width=True):
                with st.spinner("Downloading full U.S. Market Snapshot. This takes several minutes..."):
                    try:
                        from core.matrix import download_market_snapshot
                        download_market_snapshot()
                        st.cache_data.clear() # Purge the old RAM cache so the new data loads!
                        st.success("Matrix Uplink Complete. Database is fresh.")
                        time.sleep(2)
                        st.rerun() # Refresh the UI to clear the success message
                    except Exception as e:
                        st.error(f"Uplink Failed: {e}")

        st.divider()

        # --- STRATEGY PRESETS AUTOLOADER ---
        st.markdown("### Strategy Presets")
        
        # Define favorite setups here
        presets = {
            "Custom (Manual Entry)": [],
            "Mean Reversion (Oversold)": [
                {"indicator": "RSI (14)", "condition": "Less Than", "value": "30"},
                {"indicator": "Price", "condition": "Greater Than", "value": "SMA 200"}
            ],
            "The True Golden Cross": [
                {"indicator": "SMA 50", "condition": "Crosses Above", "value": "SMA 200"}
            ],
            "Momentum Breakout": [
                {"indicator": "Price", "condition": "Greater Than", "value": "Bollinger Bands (Upper)"},
                {"indicator": "Volume", "condition": "Greater Than", "value": "SMA 20"}
            ],
            "MACD Trend Reversal": [
                {"indicator": "MACD Line", "condition": "Crosses Above", "value": "MACD Signal"},
                {"indicator": "Price", "condition": "Greater Than", "value": "VWAP"}
            ]
        }
        
        selected_preset = st.selectbox("Load Playbook Setup:", list(presets.keys()), label_visibility="collapsed")
        
        # 1. Initialize the Rule Memory Bank & Reset Counter
        if 'scan_rules' not in st.session_state:
            st.session_state.scan_rules = [] # Start completely blank!
        if 'rule_reset_counter' not in st.session_state:
            st.session_state.rule_reset_counter = 0

        # --- THE PRESET APPLY BUTTON UPDATE ---
        if st.button("Apply Preset Strategy", use_container_width=True):
            import copy
            
            # Load new rules
            if selected_preset == "Custom (Manual Entry)":
                st.session_state.scan_rules = [] # Wipe clean
            else:
                st.session_state.scan_rules = copy.deepcopy(presets[selected_preset])
                
            # KEY ROTATION FIX: Rotate the keys so Streamlit generates brand new UI boxes
            st.session_state.rule_reset_counter += 1
            st.rerun() 
            
        st.divider()
        st.markdown("### Custom Technical Rules")

        # 2. Function to inject a new empty rule row
        def add_rule():
            st.session_state.scan_rules.append({"indicator": "Price", "condition": "Greater Than", "value": "SMA 200"})

        # 3. Render the existing rules dynamically using the Key Rotation
        rules_to_delete = []
        
        # List of available indicators
        available_indicators = [
            "Price", "Volume", "VWAP",
            "SMA 10", "SMA 20", "SMA 50", "SMA 200",
            "EMA 10", "EMA 20", "EMA 50", "EMA 200",
            "HMA 20", "HMA 50", "SuperTrend", "ADX (14)", "Parabolic SAR",
            "RSI (14)", "RSI (2)", "Stochastic %K", "Stochastic %D",
            "MACD Line", "MACD Signal", "MACD Histogram",
            "CCI (20)", "Awesome Oscillator",
            "Bollinger Bands (Upper)", "Bollinger Bands (Lower)",
            "Keltner Channel (Upper)", "Keltner Channel (Lower)", "ATR (14)", 
            "Donchian Channel (High)", "Donchian Channel (Low)",
            "Fibonacci Retracement (0.618)",
            "Pattern: Doji", "Pattern: Hammer", "Pattern: Inverted Hammer",
            "Pattern: Shooting Star", "Pattern: Hanging Man", "Pattern: Engulfing",
            "Pattern: Harami", "Pattern: Morning Star", "Pattern: Evening Star",
            "Pattern: Marubozu", "Pattern: Piercing Line", "Pattern: Dark Cloud Cover",
            "Pattern: 3 White Soldiers", "Pattern: 3 Black Crows"
        ]
        
        # Grab the current rotation key
        reset_id = st.session_state.rule_reset_counter

        for i, rule in enumerate(st.session_state.scan_rules):
            col1, col2, col3, col4 = st.columns([3, 2, 3, 1])
            
            with col1:
                rule["indicator"] = st.selectbox(
                    f"Ind_{i}", available_indicators, 
                    index=available_indicators.index(rule["indicator"]) if rule["indicator"] in available_indicators else 0,
                    key=f"ind_{i}_{reset_id}", label_visibility="collapsed"
                )
            with col2:
                readable_conditions = ["Greater Than", "Less Than", "Equals", "Crosses Above", "Crosses Below"]
                current_cond = rule["condition"]
                if current_cond == ">": current_cond = "Greater Than"
                if current_cond == "<": current_cond = "Less Than"
                if current_cond == "==": current_cond = "Equals"
                
                rule["condition"] = st.selectbox(
                    f"Cond_{i}", readable_conditions, 
                    index=readable_conditions.index(current_cond) if current_cond in readable_conditions else 0,
                    key=f"cond_{i}_{reset_id}", label_visibility="collapsed"
                )
            with col3:
                rule["value"] = st.text_input(
                    f"Val_{i}", rule["value"], 
                    key=f"val_{i}_{reset_id}", label_visibility="collapsed"
                )
            with col4:
                if st.button("✖", key=f"del_{i}_{reset_id}"):
                    rules_to_delete.append(i)
                    
        # 4. Clean up deleted rules
        if rules_to_delete:
            for i in sorted(rules_to_delete, reverse=True):
                st.session_state.scan_rules.pop(i)
            st.rerun()

        # 5. The Add Rule Button
        st.button("Add Condition", on_click=add_rule, use_container_width=True)
        
        st.divider()
        run_scan = st.button("Run Market Scan", use_container_width=True, type="primary")
        
        # UI Theme Toggle Logic
        st.divider()
        
        theme_list = [
            "Star Trek: TNG (LCARS)", 
            "Midnight Dark", "Terminal Green", "Bloomberg Terminal", "Cyberpunk Grid",
            "FFXIV: Black Mage", "FFXIV: Summoner", "FFXIV: Dragoon", "FFXIV: Paladin",
            "FFXIV: Dark Knight", "FFXIV: White Mage", "FFXIV: Scholar", "FFXIV: Astrologian",
            "FFXIV: Sage", "FFXIV: Warrior", "FFXIV: Gunbreaker", "FFXIV: Machinist", 
            "FFXIV: Samurai", "FFXIV: Red Mage", "FFXIV: Reaper", "FFXIV: Pictomancer", "FFXIV: Beastmaster",
            "FFXIV: Monk", "FFXIV: Ninja", "FFXIV: Viper", "FFXIV: Bard", "FFXIV: Dancer", "FFXIV: Blue Mage",
            "WoW: Undead (Forsaken)", "WoW: Goblin (Bilgewater)", "WoW: Orc (Orgrimmar)", 
            "WoW: Blood Elf (Silvermoon)", "WoW: Tauren (Thunder Bluff)", "WoW: Troll (Darkspear)",
            "WoW: Human (Stormwind)", "WoW: Dwarf (Ironforge)", "WoW: Night Elf (Darnassus)", 
            "WoW: Gnome (Gnomeregan)", "WoW: Draenei (Exodar)", "WoW: Worgen (Gilneas)", 
            "WoW: Pandaren (Pandaria)", "WoW: Dracthyr (Valdrakken)"
        ]

        theme_choice = st.selectbox(
            "UI Theme", 
            theme_list,
            key="active_theme"
        )
        
        if theme_choice == "Midnight Dark": load_css("assets/style.css")
        elif theme_choice == "Terminal Green": load_css("assets/terminal_green.css")
        elif theme_choice == "Bloomberg Terminal": load_css("assets/bloomberg.css")
        elif theme_choice == "Cyberpunk Grid": load_css("assets/cyberpunk.css")
        elif theme_choice == "Star Trek: TNG (LCARS)": load_css("assets/startrek_tng.css")
        
        elif theme_choice == "FFXIV: Black Mage": load_css("assets/ff14_blackmage.css")
        elif theme_choice == "FFXIV: Summoner": load_css("assets/ff14_summoner.css")
        elif theme_choice == "FFXIV: Dragoon": load_css("assets/ff14_dragoon.css")
        elif theme_choice == "FFXIV: Paladin": load_css("assets/ff14_paladin.css")
        elif theme_choice == "FFXIV: Dark Knight": load_css("assets/ff14_darkknight.css")
        elif theme_choice == "FFXIV: White Mage": load_css("assets/ff14_whitemage.css")
        elif theme_choice == "FFXIV: Scholar": load_css("assets/ff14_scholar.css")
        elif theme_choice == "FFXIV: Astrologian": load_css("assets/ff14_astrologian.css")
        elif theme_choice == "FFXIV: Sage": load_css("assets/ff14_sage.css")
        elif theme_choice == "FFXIV: Warrior": load_css("assets/ff14_warrior.css")
        elif theme_choice == "FFXIV: Gunbreaker": load_css("assets/ff14_gunbreaker.css")
        elif theme_choice == "FFXIV: Machinist": load_css("assets/ff14_machinist.css")
        elif theme_choice == "FFXIV: Samurai": load_css("assets/ff14_samurai.css")
        elif theme_choice == "FFXIV: Red Mage": load_css("assets/ff14_redmage.css")
        elif theme_choice == "FFXIV: Reaper": load_css("assets/ff14_reaper.css")
        elif theme_choice == "FFXIV: Pictomancer": load_css("assets/ff14_pictomancer.css")
        elif theme_choice == "FFXIV: Beastmaster": load_css("assets/ff14_beastmaster.css")
        elif theme_choice == "FFXIV: Monk": load_css("assets/ff14_monk.css")
        elif theme_choice == "FFXIV: Ninja": load_css("assets/ff14_ninja.css")
        elif theme_choice == "FFXIV: Viper": load_css("assets/ff14_viper.css")
        elif theme_choice == "FFXIV: Bard": load_css("assets/ff14_bard.css")
        elif theme_choice == "FFXIV: Dancer": load_css("assets/ff14_dancer.css")
        elif theme_choice == "FFXIV: Blue Mage": load_css("assets/ff14_bluemage.css")

        elif theme_choice == "WoW: Undead (Forsaken)": load_css("assets/wow_undead.css")
        elif theme_choice == "WoW: Goblin (Bilgewater)": load_css("assets/wow_goblin.css")
        elif theme_choice == "WoW: Orc (Orgrimmar)": load_css("assets/wow_orc.css")
        elif theme_choice == "WoW: Blood Elf (Silvermoon)": load_css("assets/wow_bloodelf.css")
        elif theme_choice == "WoW: Tauren (Thunder Bluff)": load_css("assets/wow_tauren.css")
        elif theme_choice == "WoW: Troll (Darkspear)": load_css("assets/wow_troll.css")
        elif theme_choice == "WoW: Human (Stormwind)": load_css("assets/wow_human.css")
        elif theme_choice == "WoW: Dwarf (Ironforge)": load_css("assets/wow_dwarf.css")
        elif theme_choice == "WoW: Night Elf (Darnassus)": load_css("assets/wow_nightelf.css")
        elif theme_choice == "WoW: Gnome (Gnomeregan)": load_css("assets/wow_gnome.css")
        elif theme_choice == "WoW: Draenei (Exodar)": load_css("assets/wow_draenei.css")
        elif theme_choice == "WoW: Worgen (Gilneas)": load_css("assets/wow_worgen.css")
        elif theme_choice == "WoW: Pandaren (Pandaria)": load_css("assets/wow_pandaren.css")
        elif theme_choice == "WoW: Dracthyr (Valdrakken)": load_css("assets/wow_dracthyr.css")

    # --- MAIN STAGE: DASHBOARD ---
    st.title("Market Screener Intelligence")
    
    # Fetch live macro data based on selected asset class
    macros = fetch_macro_metrics(asset_type)
    
    # Top Row: Dynamic Macro Metrics
    m1, m2, m3, m4 = st.columns(4)
    m1.metric(label=macros["M1_Label"], value=macros["M1_Val"], delta=macros["M1_Delta"])
    m2.metric(label=macros["M2_Label"], value=macros["M2_Val"], delta=macros["M2_Delta"], delta_color="inverse" if asset_type == "Equities (Stocks)" else "normal")
    m3.metric(label=macros["M3_Label"], value=macros["M3_Val"], delta=macros["M3_Delta"])
    m4.metric(label="System Status", value="Online")
    
    st.divider()
    
    # 1. Initialize the memory bank
    if 'passed_tickers' not in st.session_state:
        st.session_state.passed_tickers = []
    
    if run_scan:
        # ---> DATABASE INTEGRATION <---
        master_db = None
        if asset_type == "Equities (Stocks)":
            master_db = load_local_matrix()
            if master_db is not None:
                tickers_to_scan = master_db['ticker'].unique() 
                st.info(f"Local Database: Scanning {len(tickers_to_scan)} U.S. Equities locally.")
            else:
                st.warning("Matrix data not found. Scanning default list via internet.")
                tickers_to_scan = STOCK_TICKERS
        else:
            # Tap directly into Binance for the live Crypto universe
            st.info("Connecting to Binance API for live Crypto Universe...")
            try:
                import requests
                resp = requests.get("https://api.binance.com/api/v3/ticker/24hr")
                data = resp.json()
                # Filter for USDT pairs with >15M volume to exclude low-liquidity assets
                tickers_to_scan = [
                    item['symbol'] for item in data 
                    if item['symbol'].endswith('USDT') and float(item['quoteVolume']) > 15000000
                ]
                st.success(f"Connected: Scanning {len(tickers_to_scan)} high-volume crypto assets.")
            except Exception as e:
                st.warning("API unavailable. Using default backup list.")
                tickers_to_scan = CRYPTO_TICKERS
            
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # 2. Clear the session state for a fresh scan
        st.session_state.passed_tickers = []
        
        for i, ticker in enumerate(tickers_to_scan):
            status_text.text(f"Scanning {ticker} ({i+1}/{len(tickers_to_scan)})...")
            passed = False 
            
            # Route to local database for stocks, or the internet for Crypto/Failback
            if asset_type == "Equities (Stocks)" and master_db is not None:
                df = fetch_local_ticker(ticker, master_db)
            elif asset_type == "Equities (Stocks)":
                df = fetch_stock_data(ticker)
            else:
                df = fetch_crypto_data(ticker)
                
            if not df.empty:
                df = apply_indicators(df, st.session_state.scan_rules)
                passed, latest_data = evaluate_screener_rules(df, st.session_state.scan_rules)
                
            if passed:
                    current_price = latest_data.get('close', 0)
                    rsi_val = latest_data.get('RSI_14', None)
                    sma_200_val = latest_data.get('SMA_200', None)
                    vol_val = latest_data.get('volume', 0)

                    # 3. Save winning tickers to the memory bank
                    st.session_state.passed_tickers.append({
                        "Ticker": ticker,
                        "Price": f"${round(current_price, 2)}" if pd.notna(current_price) else "N/A",
                        "RSI (14)": round(rsi_val, 2) if pd.notna(rsi_val) else "N/A",
                        "200 SMA": round(sma_200_val, 2) if pd.notna(sma_200_val) else "N/A",
                        "Volume": round(vol_val, 2) if pd.notna(vol_val) else "N/A"
                    })
            
            progress_bar.progress((i + 1) / len(tickers_to_scan))
            
        status_text.text("Scan Complete.")

    # --- DISPLAY RESULTS ---
    if st.session_state.passed_tickers:
        st.markdown("### FILTER RESULTS")
        # Build the header row
        h1, h2, h3, h4, h5, h6 = st.columns([1.5, 1.5, 1.5, 1.5, 2, 2])
        h1.markdown("**Ticker**"); h2.markdown("**Price**"); h3.markdown("**RSI (14)**")
        h4.markdown("**200 SMA**"); h5.markdown("**Volume**"); h6.markdown("**Action**")
        st.divider()
        
        # Build the interactive rows
        for t_data in st.session_state.passed_tickers:
            c1, c2, c3, c4, c5, c6 = st.columns([1.5, 1.5, 1.5, 1.5, 2, 2])
            c1.write(f"**{t_data['Ticker']}**")
            c2.write(t_data["Price"])
            c3.write(t_data["RSI (14)"])
            c4.write(t_data["200 SMA"])
            c5.write(t_data["Volume"])
            
            # Chart Trigger Button: Instantly sets this ticker as the active chart target
            if c6.button("📈 Plot Chart", key=f"plot_btn_{t_data['Ticker']}", use_container_width=True):
                st.session_state.selected_ticker = t_data['Ticker']
                st.rerun()
                
    elif run_scan:
        st.warning("No assets matched your technical criteria in the current universe.")

   # --- AI ANALYST ---
    st.divider()
    st.subheader("AI Analyst Conviction Report")
    
    with st.expander("Expand for Deep Dive on Scanned Assets", expanded=True):
        if st.session_state.passed_tickers:
            
            ticker_options = [t['Ticker'] for t in st.session_state.passed_tickers]
            
            # Read the button click from the matrix table memory bank
            default_idx = 0
            if "selected_ticker" in st.session_state and st.session_state.selected_ticker in ticker_options:
                default_idx = ticker_options.index(st.session_state.selected_ticker)
                
            selected_ticker = st.selectbox("Select Asset for AI Analysis:", ticker_options, index=default_idx)
            
            # --- PLOTLY CHART INTEGRATION ---
            with st.spinner(f"Loading chart data for {selected_ticker}..."):
                # Fetch fresh data just for the chart display (180 days)
                if asset_type == "Equities (Stocks)":
                    chart_df = fetch_stock_data(selected_ticker, period="6mo")
                else:
                    chart_df = fetch_crypto_data(selected_ticker, limit=180)
                
                if not chart_df.empty:
                    
                    # 1. THE MASTER COLOR ROUTER
                    color_map = {
                        # Standard / Institutional
                        "Terminal Green": {"up": "#39FF14", "down": "#39FF14", "bg": "plotly_dark"},
                        "Bloomberg Terminal": {"up": "#FF9900", "down": "#FF9900", "bg": "plotly_dark"},
                        "Cyberpunk Grid": {"up": "#00F3FF", "down": "#FF003C", "bg": "plotly_dark"},
                        "Star Trek: TNG (LCARS)": {"up": "#99ccff", "down": "#cc6666", "bg": "plotly_dark"},

                        # FFXIV
                        "FFXIV: Black Mage": {"up": "#00CCFF", "down": "#FF4500", "bg": "plotly_dark"},
                        "FFXIV: Summoner": {"up": "#1abc9c", "down": "#f39c12", "bg": "plotly_dark"},
                        "FFXIV: Dragoon": {"up": "#4a90e2", "down": "#e63946", "bg": "plotly_dark"},
                        "FFXIV: Paladin": {"up": "#ffffff", "down": "#f1c40f", "bg": "plotly_dark"},
                        "FFXIV: Dark Knight": {"up": "#c1121f", "down": "#4a0a77", "bg": "plotly_dark"},
                        "FFXIV: White Mage": {"up": "#88f2ce", "down": "#f4baba", "bg": "plotly_dark"},
                        "FFXIV: Scholar": {"up": "#58d68d", "down": "#d4af37", "bg": "plotly_dark"},
                        "FFXIV: Astrologian": {"up": "#ffe699", "down": "#8a2be2", "bg": "plotly_dark"},
                        "FFXIV: Sage": {"up": "#00e5ff", "down": "#ffffff", "bg": "plotly_dark"},
                        "FFXIV: Warrior": {"up": "#ff2a00", "down": "#8a0303", "bg": "plotly_dark"},
                        "FFXIV: Gunbreaker": {"up": "#00bfff", "down": "#b5a642", "bg": "plotly_dark"},
                        "FFXIV: Machinist": {"up": "#00e5ff", "down": "#ff4500", "bg": "plotly_dark"},
                        "FFXIV: Samurai": {"up": "#111111", "down": "#b71c1c", "bg": "plotly_white"}, 
                        "FFXIV: Red Mage": {"up": "#f8f9fa", "down": "#d90429", "bg": "plotly_dark"},
                        "FFXIV: Reaper": {"up": "#2ecc71", "down": "#8b0000", "bg": "plotly_dark"},
                        "FFXIV: Pictomancer": {"up": "#00c8ff", "down": "#ff0080", "bg": "plotly_white"}, 
                        "FFXIV: Beastmaster": {"up": "#d4a373", "down": "#8b5a2b", "bg": "plotly_dark"},
                        "FFXIV: Monk": {"up": "#ffc300", "down": "#cc3300", "bg": "plotly_dark"},
                        "FFXIV: Ninja": {"up": "#b05fe6", "down": "#ff1a1a", "bg": "plotly_dark"},
                        "FFXIV: Viper": {"up": "#99ff33", "down": "#2a402a", "bg": "plotly_dark"},
                        "FFXIV: Bard": {"up": "#88d49e", "down": "#ffb703", "bg": "plotly_dark"},
                        "FFXIV: Dancer": {"up": "#ff7096", "down": "#ff0a54", "bg": "plotly_dark"},
                        "FFXIV: Blue Mage": {"up": "#0077b6", "down": "#ffd166", "bg": "plotly_dark"},

                        # WoW
                        "WoW: Undead (Forsaken)": {"up": "#72ff14", "down": "#4b0082", "bg": "plotly_dark"},
                        "WoW: Goblin (Bilgewater)": {"up": "#32cd32", "down": "#ff4500", "bg": "plotly_dark"},
                        "WoW: Orc (Orgrimmar)": {"up": "#ff1a1a", "down": "#4a0000", "bg": "plotly_dark"},
                        "WoW: Blood Elf (Silvermoon)": {"up": "#32cd32", "down": "#daa520", "bg": "plotly_dark"},
                        "WoW: Tauren (Thunder Bluff)": {"up": "#20b2aa", "down": "#ff8c00", "bg": "plotly_dark"},
                        "WoW: Troll (Darkspear)": {"up": "#40e0d0", "down": "#f5f5dc", "bg": "plotly_dark"},
                        "WoW: Human (Stormwind)": {"up": "#ffd700", "down": "#0033aa", "bg": "plotly_dark"},
                        "WoW: Dwarf (Ironforge)": {"up": "#ff8c00", "down": "#14110f", "bg": "plotly_dark"},
                        "WoW: Night Elf (Darnassus)": {"up": "#e6e6fa", "down": "#9370db", "bg": "plotly_dark"},
                        "WoW: Gnome (Gnomeregan)": {"up": "#39ff14", "down": "#daa520", "bg": "plotly_dark"},
                        "WoW: Draenei (Exodar)": {"up": "#00ffff", "down": "#ee82ee", "bg": "plotly_dark"},
                        "WoW: Worgen (Gilneas)": {"up": "#daa520", "down": "#8b0000", "bg": "plotly_dark"},
                        "WoW: Pandaren (Pandaria)": {"up": "#1e5c3a", "down": "#8b0000", "bg": "plotly_white"}, 
                        "WoW: Dracthyr (Valdrakken)": {"up": "#ffd700", "down": "#dc143c", "bg": "plotly_dark"},
                        
                        "default": {"up": "#39FF14", "down": "#FF4136", "bg": "plotly_dark"}
                    }

                    # Fetch the colors for the current theme, or use default
                    theme_colors = color_map.get(theme_choice, color_map["default"])

                    # Force calculate standard MAs for the visual chart
                    chart_df['SMA_20'] = chart_df['close'].rolling(window=20).mean()
                    chart_df['SMA_50'] = chart_df['close'].rolling(window=50).mean()
                    chart_df['SMA_200'] = chart_df['close'].rolling(window=200).mean()

                    # 2. Plot the main Candlesticks
                    fig = go.Figure(data=[go.Candlestick(
                        x=chart_df.index, open=chart_df['open'], high=chart_df['high'],
                        low=chart_df['low'], close=chart_df['close'], name="Price"
                    )])
        
                    # 3. Add the Moving Average lines
                    colors = {20: '#00F0FF', 50: '#FFB000', 200: '#FF003C'} 
                    for ma, color in colors.items():
                        if f'SMA_{ma}' in chart_df.columns:
                            fig.add_trace(go.Scatter(
                                x=chart_df.index, y=chart_df[f'SMA_{ma}'], 
                                mode='lines', name=f'SMA {ma}', 
                                line=dict(color=color, width=1.5)
                            ))
                    
                    # 4. DYNAMIC OVERLAYS
                    chart_df = apply_indicators(chart_df, st.session_state.scan_rules)
                    overlays_to_plot = set()
                    for rule in st.session_state.scan_rules:
                        for key in ['indicator', 'value']:
                            val = str(rule.get(key, ""))
                            if any(x in val for x in ["SMA", "EMA", "HMA", "VWAP", "SuperTrend", "Bands", "Channel"]):
                                overlays_to_plot.add(val)
                    
                    line_colors = ["#ff00ff", "#00ffff", "#ffff00", "#ffaa00", "#ffffff"]
                    color_idx = 0
                
                    for overlay in overlays_to_plot:
                        col_name = map_indicator_to_column(overlay)
                        if col_name and col_name in chart_df.columns:
                            fig.add_trace(go.Scatter(
                                x=chart_df.index, y=chart_df[col_name], 
                                mode='lines', name=overlay, 
                                line=dict(width=1.5, color=line_colors[color_idx % len(line_colors)])
                            ))
                            color_idx += 1

                    # 5. UPDATE LAYOUT
                    fig.update_layout(
                        title=f"{selected_ticker} - 6 Month Price Action",
                        template=theme_colors['bg'], 
                        margin=dict(l=0, r=0, t=40, b=0),
                        xaxis_rangeslider_visible=False,
                        height=400,
                        paper_bgcolor='rgba(0,0,0,0)', 
                        plot_bgcolor='rgba(0,0,0,0)',
                        showlegend=True,
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                    )
                    
                    fig.update_xaxes(showspikes=True, spikemode="across", spikethickness=1, spikedash="dot", spikecolor="#999999")
                    fig.update_yaxes(showspikes=True, spikemode="across", spikethickness=1, spikedash="dot", spikecolor="#999999")

                    st.plotly_chart(fig, use_container_width=True, key=f"chart_{selected_ticker}")

            # --- QUANTITATIVE ANALYSIS REPORT ---
            st.divider()
            if st.button(f"Generate Quant Report for {selected_ticker}", type="primary", use_container_width=True):
                with st.spinner(f"Aggregating technical and fundamental data for {selected_ticker}..."):
                    ai_report = generate_deep_dive(selected_ticker, asset_type)
                    st.markdown(ai_report)

if __name__ == "__main__":
    main()