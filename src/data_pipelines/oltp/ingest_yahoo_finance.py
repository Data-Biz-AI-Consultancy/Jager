import os
import sys
import requests
from datetime import datetime, timezone
import dlt

# Add parent directory to sys.path to resolve 'olap' or 'oltp' imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from olap.utils import setup_logging

# Set up logging
logger = setup_logging("ingest-yahoo-finance")

def run_ingestion():
    symbols_mapping = {
        "S&P500": "^GSPC",
        "DAX": "^GDAXI"
    }
    
    interval = "1h"
    range_val = "5d"
    
    headers = {
        'User-Agent': 'Jager/1.0 (by /u/jager_developer)'
    }
    
    @dlt.resource(
        name="stock_prices",
        write_disposition="merge",
        primary_key=("symbol", "price_timestamp"),
        columns={
            "symbol": {"data_type": "text"},
            "price_timestamp": {"data_type": "timestamp"},
            "open_price": {"data_type": "decimal", "nullable": True},
            "high_price": {"data_type": "decimal", "nullable": True},
            "low_price": {"data_type": "decimal", "nullable": True},
            "close_price": {"data_type": "decimal", "nullable": True},
            "volume": {"data_type": "decimal", "nullable": True}
        }
    )
    def fetch_stock_prices():
        for sym_name, sym_code in symbols_mapping.items():
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym_code}?interval={interval}&range={range_val}"
            logger.info(f"Fetching Yahoo Finance chart data for {sym_name} ({sym_code})")
            try:
                response = requests.get(url, headers=headers, timeout=10)
                if response.status_code != 200:
                    logger.error(f"Failed to fetch {url}: Status code {response.status_code}")
                    continue
                
                data = response.json()
                if not data or "chart" not in data or "result" not in data["chart"] or not data["chart"]["result"]:
                    logger.warning(f"No result found in Yahoo Finance response for {sym_code}")
                    continue
                
                result = data["chart"]["result"][0]
                timestamps = result.get("timestamp", [])
                indicators = result.get("indicators", {})
                quote_list = indicators.get("quote", [])
                if not quote_list:
                    logger.warning(f"No quotes found in indicators for {sym_code}")
                    continue
                
                quote = quote_list[0]
                opens = quote.get("open", [])
                highs = quote.get("high", [])
                lows = quote.get("low", [])
                closes = quote.get("close", [])
                volumes = quote.get("volume", [])
                
                for i in range(len(timestamps)):
                    if timestamps[i] is not None and i < len(closes) and closes[i] is not None:
                        price_timestamp = datetime.fromtimestamp(timestamps[i], tz=timezone.utc)
                        yield {
                            "symbol": sym_code,
                            "price_timestamp": price_timestamp,
                            "open_price": float(opens[i]) if i < len(opens) and opens[i] is not None else None,
                            "high_price": float(highs[i]) if i < len(highs) and highs[i] is not None else None,
                            "low_price": float(lows[i]) if i < len(lows) and lows[i] is not None else None,
                            "close_price": float(closes[i]) if closes[i] is not None else None,
                            "volume": float(volumes[i]) if i < len(volumes) and volumes[i] is not None else None
                        }
            except Exception as ex:
                logger.error(f"Error processing symbol {sym_name}: {ex}")

    logger.info("Setting DLT configuration")
    os.environ["SCHEMA__MAX_TABLE_NESTING"] = "0"
    
    # Configure pipeline destination as postgres using DATABASE_URL
    from dlt.destinations import postgres
    db_url = os.getenv("DATABASE_URL", "postgresql://jager:jager@db:5432/jager")
    pipeline = dlt.pipeline(
        pipeline_name="yahoo_finance_oltp_ingestion",
        destination=postgres(credentials=db_url),
        dataset_name="s_yahoo_finance"  # Target schema name
    )
    
    logger.info("Running pipeline")
    load_info = pipeline.run(fetch_stock_prices())
    logger.info(f"Pipeline finished:\n{load_info}")

if __name__ == "__main__":
    run_ingestion()
