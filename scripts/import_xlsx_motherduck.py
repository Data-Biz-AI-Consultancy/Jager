import os
import re
import sys
import glob
import pandas as pd
import duckdb

# Load .env file manually if it exists
env_vars = {}
if os.path.exists(".env"):
    with open(".env", "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, val = line.split("=", 1)
                env_vars[key.strip()] = val.strip().strip('"').strip("'")

# Find the latest LinkedIn export file in the data/linkedin directory
search_dir = "/Users/jimmypang/AntigravityProjects/Jager/data/linkedin"
excel_files = glob.glob(os.path.join(search_dir, "AggregateAnalytics_*.xlsx"))

if not excel_files:
    print(f"Error: No LinkedIn AggregateAnalytics export files found in {search_dir}")
    sys.exit(1)

# Pick the latest modified file
file_path = max(excel_files, key=os.path.getmtime)
print(f"Selected latest file for import: {file_path}")

base_name = os.path.splitext(os.path.basename(file_path))[0]

# Clean up base name to form a valid table prefix
clean_prefix = re.sub(r'[^a-zA-Z0-9_]', '_', base_name)
clean_prefix = re.sub(r'_+', '_', clean_prefix).strip('_')

# Get Motherduck credentials based on environment
is_prod = "--prod" in sys.argv

if is_prod:
    print("Running in PRODUCTION mode...")
    motherduck_token = os.environ.get("MOTHERDUCK_TOKEN_PROD") or env_vars.get("MOTHERDUCK_TOKEN_PROD")
    motherduck_database = os.environ.get("MOTHERDUCK_DATABASE_PROD") or env_vars.get("MOTHERDUCK_DATABASE_PROD") or "production"
    
    if not motherduck_token:
        print("Error: MOTHERDUCK_TOKEN_PROD not found in environment or .env file.")
        sys.exit(1)
else:
    print("Running in STAGING mode (default)...")
    motherduck_token = os.environ.get("MOTHERDUCK_TOKEN") or env_vars.get("MOTHERDUCK_TOKEN")
    motherduck_database = os.environ.get("MOTHERDUCK_DATABASE") or env_vars.get("MOTHERDUCK_DATABASE") or "staging"
    
    if not motherduck_token:
        print("Error: MOTHERDUCK_TOKEN not found in environment or .env file.")
        sys.exit(1)

print(f"Connecting to Motherduck database: {motherduck_database}")
conn = duckdb.connect(f"md:{motherduck_database}?token={motherduck_token}")

tabs = ["ENGAGEMENT", "TOP POSTS", "FOLLOWERS"]

def clean_column_name(name):
    cleaned = re.sub(r'[^a-zA-Z0-9_]', '_', str(name).strip().lower())
    cleaned = re.sub(r'_+', '_', cleaned).strip('_')
    if cleaned and cleaned[0].isdigit():
        cleaned = f"_{cleaned}"
    return cleaned

print("Creating schema s_manual in Motherduck if it does not exist...")
conn.execute("CREATE SCHEMA IF NOT EXISTS s_manual;")

for tab in tabs:
    print(f"\nProcessing tab: {tab}...")
    try:
        table_name = f"{clean_prefix}_{tab.lower().replace(' ', '_')}".lower()
        
        if tab == "TOP POSTS":
            raw_df = pd.read_excel(file_path, sheet_name=tab, header=None)
            
            # Left table: Top 50 by Engagements
            df_left = raw_df.iloc[3:, [0, 1, 2]].copy()
            df_left.columns = ['post_url', 'post_publish_date', 'engagements']
            df_left['impressions'] = None
            
            # Right table: Top 50 by Impressions
            df_right = raw_df.iloc[3:, [4, 5, 6]].copy()
            df_right.columns = ['post_url', 'post_publish_date', 'impressions']
            df_right['engagements'] = None
            
            # Concat the two tables
            df = pd.concat([df_left, df_right], ignore_index=True)
            df = df.dropna(subset=['post_url'])
            
            # Ensure proper types
            df['engagements'] = pd.to_numeric(df['engagements'], errors='coerce')
            df['impressions'] = pd.to_numeric(df['impressions'], errors='coerce')
        elif tab == "FOLLOWERS":
            raw_df = pd.read_excel(file_path, sheet_name=tab, header=None)
            df = raw_df.iloc[3:].copy()
            df.columns = [clean_column_name(c) for c in raw_df.iloc[2]]
        else:
            df = pd.read_excel(file_path, sheet_name=tab)
            df.columns = [clean_column_name(c) for c in df.columns]
            
        print(f"Table name: s_manual.{table_name}")
        print(f"Columns: {list(df.columns)}")
        print(f"Row count: {len(df)}")
        
        # Write to Motherduck
        # DuckDB can register and query pandas dataframes in the local scope directly.
        # We will register it under a temporary name and write it into the target schema.
        conn.register("temp_df", df)
        conn.execute(f"CREATE OR REPLACE TABLE s_manual.{table_name} AS SELECT * FROM temp_df;")
        conn.unregister("temp_df")
        
        print(f"Successfully imported {tab} into Motherduck: s_manual.{table_name}")
    except Exception as e:
        print(f"Error importing tab {tab}: {e}")

print("\nDone!")
