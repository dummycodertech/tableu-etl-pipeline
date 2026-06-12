import pandas as pd
from prophet import Prophet
import sqlite3
import logging

# Configure systematic logging to track model training and data writes
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def run_forecasting_pipeline(forecast_horizon: int = 30):
    """
    Reads raw market data from local SQLite, trains a Prophet model, 
    decomposes trend/seasonality components, stores the predictive matrix to SQL,
    and exports a CSV bridge for Tableau Public.
    """
    logging.info("Initiating quantitative forecasting phase...")
    db_name = 'fintech_risk.db'
    
    try:
        # 1. Extraction Layer from Local SQL
        connection = sqlite3.connect(db_name)
        query = "SELECT * FROM raw_market_history"
        raw_history = pd.read_sql_query(query, connection)
        logging.info(f"Successfully loaded {len(raw_history)} historical rows from SQLite database.")
        
        # 2. Transformation Layer for Prophet
        # Prophet strictly requires columns to be named exactly 'ds' (datestamp) and 'y' (target value)
        modeling_df = pd.DataFrame()
        modeling_df['ds'] = pd.to_datetime(raw_history['Date'])
        modeling_df['y'] = raw_history['Close_Price'].astype(float)
        
        # 3. Machine Learning Modeling Layer
        logging.info("Fitting data to Prophet mathematical engine. This may take a few seconds...")
        model = Prophet(
            daily_seasonality=True,
            weekly_seasonality=True,
            yearly_seasonality=True
        )
        model.fit(modeling_df)
        
        # Generate an empty future timeline extending 30 days out
        future_timeline = model.make_future_dataframe(periods=forecast_horizon)
        
        logging.info(f"Generating forward projections for a {forecast_horizon}-day horizon...")
        forecast_output = model.predict(future_timeline)
        
        # 4. Data Engineering & Analytics Integration
        # Isolate target metrics and merge them back with actual historical values
        analytics_columns = ['ds', 'yhat', 'yhat_lower', 'yhat_upper', 'trend']
        extracted_predictions = forecast_output[analytics_columns]
        
        unified_matrix = extracted_predictions.merge(modeling_df, on='ds', how='left')
        
        # Structure columns to match corporate, institutional schemas for BI ingestion
        unified_matrix.rename(
            columns={
                'ds': 'Calendar_Date',
                'y': 'Actual_Market_Value',
                'yhat': 'Algorithmic_Forecast_Value',
                'yhat_lower': 'Lower_Risk_Bound',
                'yhat_upper': 'Upper_Risk_Bound',
                'trend': 'Underlying_Macro_Trend'
            },
            inplace=True
        )
        
        # 5. Loading Layer back to SQLite
        logging.info("Writing finalized analytical matrix to SQLite...")
        unified_matrix.to_sql(
            name='market_forecasting_metrics',
            con=connection,
            if_exists='replace',
            index=False
        )
        connection.close()
        logging.info("Database state updated successfully: table 'market_forecasting_metrics' is live! ✅")
        
        # 6. Tableau Public Bridge Layer
        logging.info("Exporting CSV bridge for Tableau Public...")
        unified_matrix.to_csv('fintech_risk_export.csv', index=False)
        logging.info("CSV export complete: 'fintech_risk_export.csv' is ready for BI ingestion. 🚀")
        
        return True
        
    except Exception as e:
        logging.error(f"Pipeline failure during modeling/forecasting phase: {str(e)}")
        return False

if __name__ == "__main__":
    success = run_forecasting_pipeline(forecast_horizon=30)
    if success:
        print("\n[SUCCESS] Pipeline completed. Run your Tableau Public app and connect to 'fintech_risk_export.csv'.")