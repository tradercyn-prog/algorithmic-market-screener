import os
from google import genai
from dotenv import load_dotenv
from core.omni_feed import generate_omni_feed

# Load your secure API key from the .env file
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

# Initialize the new GenAI client
client = genai.Client(api_key=api_key) if api_key else None

def generate_deep_dive(ticker, asset_type):
    """Calls the Omni-Feed and feeds it to Gemini for a pro-level analysis."""
    if not client:
        return "API KEY MISSING: Please add GEMINI_API_KEY to your .env file."

    try:
        # 1. Gather the Omni-Feed Data (Technicals + News)
        omni_payload = generate_omni_feed(ticker, asset_type)
        
        # 2. Construct the Quant Prompt
        # We instruct the AI to adopt a highly experienced, institutional persona
        prompt = f"""
        You are an elite quantitative analyst and portfolio manager with 15 years of institutional trading experience.
        I am passing you a raw data feed containing the latest technical indicators and news sentiment for {ticker}.
        
        RAW OMNI-FEED DATA:
        {omni_payload}
        
        YOUR TASK:
        Write a high-conviction, professional trading report for {ticker}. 
        Do NOT just repeat the data back to me. Synthesize it. 
        - What is the current trend telling us based on the moving averages?
        - Are there any red flags in the news or divergence in the momentum?
        - What are the key levels to watch based on volatility and bands?
        - Write a clear, actionable verdict (Bullish, Bearish, or Neutral) and a brief justification, and rate it on a scale of 1-10 for conviction, 1-10 for risk, and 1-10 for reward.
        
        CRITICAL FORMATTING RULE: Do NOT use the USD symbol anywhere in your report. Streamlit interprets it as LaTeX math formatting and it breaks the UI. Use the word "USD" or simply write the number.
        Format the report cleanly using Markdown. Be concise, objective, and lethal.
        """
        
        # 3. Call the Gemini Model (Using the new v1 SDK syntax)
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        
        return response.text
        
    except Exception as e:
        return f"Communications Array Error: Unable to reach AI core. Details: {e}"