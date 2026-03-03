# Algorithmic Market Screener & AI Quant Analyst

An enterprise-grade, locally-hosted market screener and quantitative analysis dashboard built with Python. 

## Architecture Overview
This application is designed to process massive financial datasets locally to bypass strict API rate limits. It integrates a dynamic technical rule builder, live chart rendering, and an LLM-powered AI analyst that synthesizes technical indicators and fundamental news into actionable reports.

## Key Features
* **Local Matrix Database:** Asynchronous data processing handles 128MB+ datasets for rapid U.S. Equity scanning without API throttling.
* **Live API Uplinks:** Direct integration with the Binance API for real-time cryptocurrency screening.
* **Dynamic Rule Engine:** Custom technical indicator parsing (SMA, EMA, RSI, MACD, Bollinger Bands, Candlestick Patterns) using `pandas-ta`.
* **AI Quant Analyst:** Utilizes the Google GenAI SDK (Gemini 2.5 Flash) to generate high-conviction fundamental and technical synthesis.
* **Custom UI Theming:** Extensive CSS injection system supporting 40+ modular visual themes.

## Tech Stack
* **Frontend:** Streamlit, Plotly
* **Backend:** Python, Pandas, Pandas-TA
* **Data Routing:** yfinance, Binance API, Requests
* **AI Integration:** Google GenAI SDK
* **Security:** python-dotenv

## Local Installation & Quick Start
1. Clone the repository to your local machine.
2. Install the required dependencies: 
   `pip install -r requirements.txt`
3. Create a `.env` file in the root directory and add your secure API key: 
   `GEMINI_API_KEY=your_key_here`
4. Initialize the dashboard: 
   `streamlit run app.py`

---
*Developed as a standalone quantitative analysis tool. Codebase optimized for low-latency local execution.*
