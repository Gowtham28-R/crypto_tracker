import os
import re
import pandas as pd
import numpy as np
from datetime import datetime
import time  # Import the time module for the delay
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
# The tabulate library is used for creating formatted tables in the terminal
from tabulate import tabulate
# The yfinance library is used to fetch historical stock and crypto data
import yfinance as yf
# The matplotlib library is used for creating graphical charts
import matplotlib.pyplot as plt
# webdriver-manager is no longer needed for this manual approach, but we can leave it imported.
from webdriver_manager.chrome import ChromeDriverManager

# ==============================
# CONFIGURATION
# ==============================
URL = "https://coinmarketcap.com/"
FILE_NAME = r"F:/crypto mini/crypto_market_data.csv"
TOP_N = 20
UPDATE_INTERVAL_SECONDS = 10 # Auto-update every 10 seconds

# ==============================

def clean_numeric_text(text):
    """Helper function to clean text like '$1,234.56' or '$1.2T' into a number."""
    if not isinstance(text, str):
        return None
    
    text = text.replace('$', '').replace(',', '').replace('%', '').strip()
    
    multiplier = 1
    if 'T' in text:
        multiplier = 1_000_000_000_000
        text = text.replace('T', '')
    elif 'B' in text:
        multiplier = 1_000_000_000
        text = text.replace('B', '')
    elif 'M' in text:
        multiplier = 1_000_000
        text = text.replace('M', '')
        
    try:
        return float(text) * multiplier
    except (ValueError, TypeError):
        return None

def get_top_cryptos(headless=True):
    """Scrapes the top N cryptocurrencies from CoinMarketCap using Selenium."""
    # Initialize driver to None so it can be checked in the finally block
    driver = None
    try:
        print("🚀 Initializing browser with manual driver path...")
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("window-size=1920,1080")

        driver_path = r"F:\crypto mini\chromedriver.exe"
        service = Service(executable_path=driver_path)
        
        # The driver initialization is now inside the try block
        driver = webdriver.Chrome(service=service, options=chrome_options)
        print("✅ Chrome driver initialized successfully.")
        
        driver.get(URL)
        print(f"⏳ Navigated to CoinMarketCap. Waiting for the data table to load...")
        wait = WebDriverWait(driver, 20)
        
        table_selector = "table.cmc-table tbody"
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, table_selector)))
        wait.until(lambda d: len(d.find_elements(By.CSS_SELECTOR, f"{table_selector} tr")) >= TOP_N)
        print("✅ Data table loaded successfully.")

        rows = driver.find_elements(By.CSS_SELECTOR, f"{table_selector} tr")[:TOP_N]
        crypto_data = []
        print(f"Parsing data for top {TOP_N} coins...")

        for row in rows:
            cols = row.find_elements(By.TAG_NAME, 'td')
            if len(cols) < 9: # The table structure now often has more columns
                continue

            try:
                # === UPDATED SELECTORS TO BE MORE ROBUST ===
                name = cols[2].find_element(By.CSS_SELECTOR, 'p.coin-item-symbol').text
                price = clean_numeric_text(cols[3].text)
                change_24h = clean_numeric_text(cols[5].text)
                market_cap = clean_numeric_text(cols[7].text)
                # ============================================

                crypto_data.append({
                    "Name": name,
                    "PriceUSD": price,
                    "Change24h_Percent": change_24h,
                    "MarketCapUSD": market_cap,
                })
            except Exception as e:
                # This helps debug which rows are failing and why
                print(f"Could not parse a row, likely an ad or non-standard entry. Skipping. Error: {e}")
                continue
        
        return pd.DataFrame(crypto_data)

    except Exception as e:
        print(f"❌ An error occurred during scraping: {e}")
        if driver: # Only take screenshot if driver was initialized
            driver.save_screenshot("error_screenshot.png")
            print("📸 A screenshot named 'error_screenshot.png' was saved for debugging.")
        return pd.DataFrame()
    finally:
        # Only try to quit the driver if it was successfully started
        if driver:
            print("Browser closing.")
            driver.quit()

def save_to_csv(df, filename):
    """Efficiently appends data to a CSV file."""
    # The exist_ok=True argument prevents an error if the directory already exists.
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    df["Timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    cols = ["Timestamp"] + [col for col in df.columns if col != "Timestamp"]
    df = df[cols]
    
    write_header = not os.path.exists(filename)
    df.to_csv(filename, mode='a', header=write_header, index=False)
    print(f"✅ Data for {len(df)} coins appended successfully to {filename}")

def display_advanced_analysis(df):
    """Calculates and prints advanced market statistics to the terminal."""
    print("--- Advanced Market Analysis ---")
    
    # 1. Overall Market Sentiment
    avg_change = df['Change24h_Percent'].mean()
    sentiment = "Bullish 🐂" if avg_change > 0 else "Bearish 🐻"
    print(f"Overall Market Sentiment: {sentiment} ({avg_change:.2f}% avg change)")

    # 2. Price Analysis
    highest_price_coin = df.loc[df['PriceUSD'].idxmax()]
    lowest_price_coin = df.loc[df['PriceUSD'].idxmin()]
    print(f"Highest Price Coin: {highest_price_coin['Name']} at ${highest_price_coin['PriceUSD']:,.2f}")
    print(f"Lowest Price Coin: {lowest_price_coin['Name']} at ${lowest_price_coin['PriceUSD']:,.4f}")
    print("--------------------------------\n")


def display_highly_advanced_analysis(df):
    """Calculates and prints highly advanced market statistics."""
    print("--- Highly Advanced Analysis ---")

    # 1. Market Volatility
    volatility = df['Change24h_Percent'].std()
    print(f"Market Volatility (Std Dev of 24h Change): {volatility:.2f}%")

    # 2. Market-Cap Weighted Sentiment
    weighted_avg_change = (df['Change24h_Percent'] * df['MarketCapUSD']).sum() / df['MarketCapUSD'].sum()
    weighted_sentiment = "Bullish 🐂" if weighted_avg_change > 0 else "Bearish 🐻"
    print(f"Market-Cap Weighted Sentiment: {weighted_sentiment} ({weighted_avg_change:.2f}% change)")

    # 3. Market Cap Tiers
    large_cap = df[df['MarketCapUSD'] >= 10_000_000_000].shape[0]
    mid_cap = df[(df['MarketCapUSD'] >= 1_000_000_000) & (df['MarketCapUSD'] < 10_000_000_000)].shape[0]
    small_cap = df[df['MarketCapUSD'] < 1_000_000_000].shape[0]
    print("\nMarket Structure by Cap Tiers:")
    print(f"  - Large-Cap (> $10B): {large_cap} coins")
    print(f"  - Mid-Cap ($1B - $10B): {mid_cap} coins")
    print(f"  - Small-Cap (< $1B): {small_cap} coins")

    # 4. Full Statistical Summary with Coin Names
    print("\nStatistical Summary of Key Metrics:")
    summary_df = df[['PriceUSD', 'Change24h_Percent', 'MarketCapUSD']].describe()

    # Create a new column for coin name details, initialized as empty strings
    summary_df['Details'] = ''

    # Get coin names for the 'max' row
    max_price_name = df.loc[df['PriceUSD'].idxmax(), 'Name']
    max_change_name = df.loc[df['Change24h_Percent'].idxmax(), 'Name']
    max_mcap_name = df.loc[df['MarketCapUSD'].idxmax(), 'Name']
    
    # Get coin names for the 'min' row
    min_price_name = df.loc[df['PriceUSD'].idxmin(), 'Name']
    min_change_name = df.loc[df['Change24h_Percent'].idxmin(), 'Name']
    min_mcap_name = df.loc[df['MarketCapUSD'].idxmin(), 'Name']

    # Add the coin names to the respective rows in the 'Details' column
    summary_df.at['max', 'Details'] = f"({max_price_name} / {max_change_name} / {max_mcap_name})"
    summary_df.at['min', 'Details'] = f"({min_price_name} / {min_change_name} / {min_mcap_name})"

    # Rename the column for clarity
    summary_df.rename(columns={'Details': 'Coin for Min/Max (Price/Change/MCap)'}, inplace=True)

    print(tabulate(summary_df, headers='keys', tablefmt='grid'))
    print("--------------------------------\n")

def display_recommendation_assistant(df):
    """Provides a speculative recommendation based on a simple scoring model."""
    print("--- Final Recommendation Assistant ---")
    print("⚠️  DISCLAIMER: This is not financial advice. All analysis is for educational purposes based on a simplified model and scraped data. Do your own research.")

    # Simple scoring model: 50% Market Cap, 50% 24h Change
    df['mc_norm'] = (df['MarketCapUSD'] - df['MarketCapUSD'].min()) / (df['MarketCapUSD'].max() - df['MarketCapUSD'].min())
    df['ch_norm'] = (df['Change24h_Percent'] - df['Change24h_Percent'].min()) / (df['Change24h_Percent'].max() - df['Change24h_Percent'].min())
    df['score'] = 0.5 * df['mc_norm'] + 0.5 * df['ch_norm']
    
    recommendation = df.loc[df['score'].idxmax()]
    rec_name = recommendation['Name']
    
    reason = f"Recommended due to a strong combination of high market capitalization (indicating stability) and positive recent momentum ({recommendation['Change24h_Percent']:.2f}%). Its dominant market position suggests a lower risk profile compared to other assets in the list."

    print(f"\n✅ Recommendation: Consider researching {rec_name}")
    print(f"\nReasoning: {reason}")

    # --- ADDED: Scenario-Based Speculative Growth Outlook ---
    print(f"\nSpeculative Long-Term Growth Scenarios for {rec_name}:")
    
    scenarios = {
        "Conservative": 0.20, # 20% annual growth
        "Moderate": 0.50,     # 50% annual growth
        "Aggressive": 1.20      # 120% annual growth
    }
    
    projections = []
    for year in [1, 5, 10]:
        row = {"Timeframe (Years)": year}
        for name, rate in scenarios.items():
            # Project future price with compounding
            future_price = recommendation['PriceUSD'] * ((1 + rate) ** year)
            growth_percent = ((future_price - recommendation['PriceUSD']) / recommendation['PriceUSD']) * 100
            row[f"{name} Growth %"] = f"{growth_percent:,.2f}%"
        projections.append(row)
    
    projection_df = pd.DataFrame(projections)
    print(tabulate(projection_df, headers='keys', tablefmt='grid', showindex=False))
    print("\nNOTE: Projections are based on hypothetical annual growth rates and do not represent actual predictions.")
    # ---------------------------------------------------------

    # --- Historical Data Chart ---
    generate_historical_chart(rec_name)


def generate_historical_chart(coin_name):
    """Fetches historical data and generates a graphical chart."""
    print(f"\n--- Historical Price Chart for {coin_name} ---")
    try:
        # Fetch data from Yahoo Finance for the last year
        ticker = f"{coin_name}-USD"
        data = yf.download(ticker, period="1y")

        if data.empty:
            print(f"Could not fetch historical data for {ticker}. The ticker may be incorrect or delisted.")
            return

        # Create the plot
        plt.style.use('seaborn-v0_8-darkgrid')
        fig, ax = plt.subplots(figsize=(12, 7))

        ax.plot(data['Close'], label='Close Price (USD)', color='cyan')
        ax.plot(data['Open'], label='Open Price (USD)', color='magenta', linestyle='--')

        # Formatting the chart
        ax.set_title(f'{coin_name} Price Trend (Last 1 Year)', fontsize=16)
        ax.set_xlabel('Date', fontsize=12)
        ax.set_ylabel('Price (USD)', fontsize=12)
        ax.legend()
        ax.grid(True)
        plt.xticks(rotation=45)
        plt.tight_layout()

        # Save the chart to a file
        chart_filename = 'historical_growth_chart.png'
        plt.savefig(chart_filename)
        print(f"✅ Chart saved as '{chart_filename}'")
        plt.close()

    except Exception as e:
        print(f"❌ An error occurred while generating the chart: {e}")


def main():
    """Main function to orchestrate the crypto scraper."""
    # --- NEW: Added a continuous loop for auto-updating ---
    try:
        while True:
            data = get_top_cryptos(headless=True)

            if data.empty or len(data) < TOP_N:
                print("⚠ Scraping finished with incomplete or no data. Please check the error messages above or 'error_screenshot.png'.")
            else:
                # Display Timestamp in Terminal
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(f"\n📈 Market Data as of: {current_time}\n")

                print("--- Scraped Data Sample ---")
                print(tabulate(data, headers='keys', tablefmt='grid', showindex=False))
                print("--------------------------\n")

                # Perform all analysis
                data['Change24h_Percent'] = pd.to_numeric(data['Change24h_Percent'], errors='coerce')
                analysis_data = data.dropna(subset=['Change24h_Percent', 'PriceUSD', 'MarketCapUSD'])

                top_gainers = analysis_data.sort_values(by='Change24h_Percent', ascending=False).head(5)
                top_losers = analysis_data.sort_values(by='Change24h_Percent', ascending=True).head(5)

                print("--- Top 5 Gainers (24h) ---")
                print(tabulate(top_gainers[['Name', 'PriceUSD', 'Change24h_Percent']], headers='keys', tablefmt='grid', showindex=False))
                print("---------------------------\n")
                
                print("--- Top 5 Losers (24h) ----")
                print(tabulate(top_losers[['Name', 'PriceUSD', 'Change24h_Percent']], headers='keys', tablefmt='grid', showindex=False))
                print("---------------------------\n")

                display_advanced_analysis(analysis_data.copy())
                display_highly_advanced_analysis(analysis_data)
                display_recommendation_assistant(analysis_data.copy())
                
                save_to_csv(data, FILE_NAME)

            # Wait for the next update
            print(f"\n🕒 Waiting {UPDATE_INTERVAL_SECONDS} seconds for the next update... (Press Ctrl+C to stop)")
            time.sleep(UPDATE_INTERVAL_SECONDS)

    except KeyboardInterrupt:
        print("\n\n🛑 Auto-updating stopped by user. Exiting.")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")


if __name__ == "__main__":
    main()

