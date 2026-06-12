import pandas as pd
import yfinance as yf
import sqlite3
import logging
from datetime import date

# Configure clear logging to track the ETL execution
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def ingest_market_data(ticker: str, start_date: str) -> bool:
    """
    Extracts historical market data from yfinance API and loads it into a local SQLite database.
    """
    today_str = date.today().strftime("%Y-%m-%d")
    logging.info(f"Starting ingestion lifecycle for asset: {ticker}")
    
    try:
        # 1. Extraction Layer
        # Note: multi_level_index=False ensures clean columns in recent yfinance versions
        raw_data = yf.download(ticker, start=start_date, end=today_str, multi_level_index=False)
        
        if raw_data.empty:
            logging.error(f"No market data returned for ticker: {ticker}. Aborting pipeline.")
            return False
            
        raw_data.reset_index(inplace=True)
        
        # 2. Transformation Layer
        processed_df = pd.DataFrame()
        processed_df['Date'] = pd.to_datetime(raw_data['Date'])
        processed_df['Close_Price'] = raw_data['Close'].astype(float)
            
        logging.info(f"Successfully processed {len(processed_df)} records. Commencing Database write.")
        
        # 3. Loading Layer (Relational Storage)
        connection = sqlite3.connect('fintech_risk.db')
        
        # Save raw data into its own dedicated historical table
        processed_df.to_sql(
            name='raw_market_history', 
            con=connection, 
            if_exists='replace', 
            index=False
        )
        connection.close()
        logging.info("Database state updated successfully: table 'raw_market_history' is online. ✅")
        return True
        
    except Exception as e:
        logging.error(f"Pipeline failure during ingestion phase: {str(e)}")
        return False

if __name__ == "__main__":
    # Ingesting Bitcoin data from Jan 1, 2022 to the current date
    success = ingest_market_data(ticker="BTC-USD", start_date="2022-01-01")
    if success:
        print("\n[SUCCESS] File 1 runs flawlessly. Your local SQL database has been initialized.")