import os
import sys
import requests
import dlt

# Add parent directory to sys.path to resolve 'olap' or 'oltp' imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from common.utils import setup_logging, get_http_headers, create_postgres_pipeline

# Set up logging
logger = setup_logging("ingest-eurostat-fx")

def run_ingestion():
    url = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/ert_bil_eur_d?format=json&lang=en&currency=USD&currency=HKD&lastTimePeriod=10"
    
    headers = get_http_headers()
    
    @dlt.resource(
        name="fx_rates",
        write_disposition="merge",
        primary_key=("base_currency", "target_currency", "rate_date"),
        columns={
            "base_currency": {"data_type": "text"},
            "target_currency": {"data_type": "text"},
            "rate": {"data_type": "decimal"},
            "rate_date": {"data_type": "date"}
        }
    )
    def fetch_fx_rates():
        logger.info(f"Fetching Eurostat FX Rates from: {url}")
        try:
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code != 200:
                logger.error(f"Failed to fetch {url}: Status code {response.status_code}")
                return
            
            data = response.json()
            size = data.get("size", [])
            values = data.get("value", {})
            dimensions = data.get("dimension", {})
            
            if "currency" not in dimensions or "time" not in dimensions:
                logger.error("Missing required dimensions 'currency' or 'time' in API response")
                return
            
            currency_index = dimensions["currency"]["category"]["index"]
            time_index = dimensions["time"]["category"]["index"]
            
            currency_keys = list(currency_index.keys())
            time_keys = list(time_index.keys())
            
            rates_by_date = {}
            time_size = size[4] if len(size) > 4 else len(time_keys)
            
            for currency in currency_keys:
                i_currency = currency_index[currency]
                for time_val in time_keys:
                    i_time = time_index[time_val]
                    idx = i_currency * time_size + i_time
                    val = values.get(str(idx))
                    
                    if val is not None:
                        if time_val not in rates_by_date:
                            rates_by_date[time_val] = {}
                        rates_by_date[time_val][currency] = float(val)
            
            for date_val, rates in rates_by_date.items():
                if "USD" in rates and rates["USD"] != 0:
                    yield {
                        "base_currency": "USD",
                        "target_currency": "EUR",
                        "rate": float(1.0 / rates["USD"]),
                        "rate_date": date_val
                    }
                if "HKD" in rates:
                    yield {
                        "base_currency": "EUR",
                        "target_currency": "HKD",
                        "rate": float(rates["HKD"]),
                        "rate_date": date_val
                    }
        except Exception as ex:
            logger.error(f"Error processing Eurostat FX API: {ex}")

    pipeline = create_postgres_pipeline("eurostat_fx_oltp_ingestion", "s_euro_stat")
    
    logger.info("Running pipeline")
    load_info = pipeline.run(fetch_fx_rates())
    logger.info(f"Pipeline finished:\n{load_info}")

if __name__ == "__main__":
    run_ingestion()
