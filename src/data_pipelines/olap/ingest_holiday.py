import os
import sys
import dlt
import time
import urllib.request
import json
import urllib.error

# Add parent directory of the script's directory to sys.path to resolve 'olap'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from olap.utils import setup_logging, create_motherduck_pipeline

# Set up logging
logger = setup_logging("ingest-holiday")

def fetch_json(url):
    req = urllib.request.Request(
        url,
        headers={'User-Agent': 'Mozilla/5.0'}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        logger.warning(f"HTTP Error {e.code} for URL: {url}")
        return None
    except Exception as e:
        logger.warning(f"Error fetching URL {url}: {e}")
        return None

def run_ingestion():
    logger.info("Fetching available countries")
    countries = fetch_json("https://date.nager.at/api/v4/Countries/Available")
    if not countries:
        logger.error("Failed to fetch available countries list.")
        sys.exit(1)
    
    logger.info(f"Found {len(countries)} available countries.")
    
    # We will fetch holidays for years 2025, 2026, and 2027
    years = [2025, 2026, 2027]
    
    @dlt.resource(name="public_holidays", write_disposition="replace")
    def get_public_holidays():
        for country in countries:
            country_code = country.get("countryCode")
            if not country_code:
                continue
            for year in years:
                url = f"https://date.nager.at/api/v4/Holidays/{country_code}/{year}"
                logger.info(f"Fetching holidays for {country_code} in {year}")
                holidays_data = fetch_json(url)
                if holidays_data:
                    for holiday in holidays_data:
                        yield holiday
                # Polite rate limiting sleep
                time.sleep(0.05)

    logger.info("Starting DLT pipeline for public holidays")
    pipeline = create_motherduck_pipeline(
        pipeline_name="holiday_ingestion",
        dataset_name="s_holiday",  # Target schema name
    )

    # Run the pipeline
    load_info = pipeline.run(get_public_holidays)
    logger.info(f"Pipeline execution completed successfully:\n{load_info}")

if __name__ == "__main__":
    run_ingestion()
