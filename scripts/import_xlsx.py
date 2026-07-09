import os
import re
import pandas as pd
from sqlalchemy import create_engine, text

# File info
file_path = "/Users/jimmypang/AntigravityProjects/Jager/data/linkedin/AggregateAnalytics_Jimmy Pang_2025-07-05_2026-07-09.xlsx"
base_name = os.path.splitext(os.path.basename(file_path))[0]

# Clean up base name to form a valid, clean prefix
clean_prefix = re.sub(r'[^a-zA-Z0-9_]', '_', base_name)
clean_prefix = re.sub(r'_+', '_', clean_prefix).strip('_')

# Database connection to local OLAP Postgres
db_url = "postgresql://jager:jager@localhost:5432/jager_olap"
engine = create_engine(db_url)

tabs = ["ENGAGEMENT", "TOP POSTS", "FOLLOWERS"]

def clean_column_name(name):
    cleaned = re.sub(r'[^a-zA-Z0-9_]', '_', str(name).strip().lower())
    cleaned = re.sub(r'_+', '_', cleaned).strip('_')
    if cleaned and cleaned[0].isdigit():
        cleaned = f"_{cleaned}"
    return cleaned

with engine.connect() as conn:
    print("Creating schema s_manual...")
    conn.execute(text("CREATE SCHEMA IF NOT EXISTS s_manual;"))
    conn.commit()

for tab in tabs:
    print(f"\nProcessing tab: {tab}...")
    try:
        table_name = f"{clean_prefix}_{tab.lower().replace(' ', '_')}".lower()
        
        if tab == "TOP POSTS":
            # LinkedIn exports TOP POSTS as two side-by-side tables separated by an empty column (column 3):
            # Left: Top 50 by Engagements (cols 0, 1, 2)
            # Right: Top 50 by Impressions (cols 4, 5, 6)
            # Headers are on row 2, data starts on row 3.
            raw_df = pd.read_excel(file_path, sheet_name=tab, header=None)
            
            # Left table: Top 50 by Engagements
            df_left = raw_df.iloc[3:, [0, 1, 2]].copy()
            df_left.columns = ['post_url', 'post_publish_date', 'engagements']
            df_left['impressions'] = None
            
            # Right table: Top 50 by Impressions
            df_right = raw_df.iloc[3:, [4, 5, 6]].copy()
            df_right.columns = ['post_url', 'post_publish_date', 'impressions']
            df_right['engagements'] = None
            
            # Concat the two tables to form exactly 100 records
            df = pd.concat([df_left, df_right], ignore_index=True)
            # Drop rows with no post_url
            df = df.dropna(subset=['post_url'])
            
            # Ensure proper types
            df['engagements'] = pd.to_numeric(df['engagements'], errors='coerce')
            df['impressions'] = pd.to_numeric(df['impressions'], errors='coerce')
        else:
            # Standard import for other tabs
            df = pd.read_excel(file_path, sheet_name=tab)
            df.columns = [clean_column_name(c) for c in df.columns]
            
        print(f"Table name: s_manual.{table_name}")
        print(f"Columns: {list(df.columns)}")
        print(f"Row count: {len(df)}")
        
        # Write to PostgreSQL
        df.to_sql(
            name=table_name,
            con=engine,
            schema="s_manual",
            if_exists="replace",
            index=False
        )
        print(f"Successfully imported {tab} into s_manual.{table_name}")
    except Exception as e:
        print(f"Error importing tab {tab}: {e}")

print("\nDone!")
