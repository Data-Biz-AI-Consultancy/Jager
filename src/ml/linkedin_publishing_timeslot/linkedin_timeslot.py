import os
import logging
import datetime
import duckdb
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("ml-service.linkedin_timeslot")

def get_motherduck_connection():
    motherduck_token = os.getenv("MOTHERDUCK_TOKEN")
    if not motherduck_token:
        logger.warning("MOTHERDUCK_TOKEN environment variable not set, attempting to use default connection...")
    
    db_name = os.getenv("MOTHERDUCK_DATABASE", "staging")
    connection_str = f"md:{db_name}"
    if motherduck_token:
        connection_str += f"?token={motherduck_token}"
        
    return duckdb.connect(connection_str)

def initialize_schemas(conn):
    logger.info("Initializing ds_training and ds_prediction schemas in MotherDuck if not exist...")
    conn.execute("CREATE SCHEMA IF NOT EXISTS ds_training;")
    conn.execute("CREATE SCHEMA IF NOT EXISTS ds_prediction;")
    
    # Create prediction recommendations table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ds_prediction.timeslot_recommendations (
            channel_type VARCHAR(50),
            day_of_week INTEGER,
            hour_of_day INTEGER,
            predicted_engagement_rate DOUBLE,
            recommendation_rank INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (channel_type, day_of_week, hour_of_day)
        );
    """)
    
    # Create model metadata table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ds_prediction.model_metadata (
            model_name VARCHAR(100),
            channel_type VARCHAR(50),
            trained_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            r2_score DOUBLE,
            sample_size INTEGER,
            hyperparameters VARCHAR(255)
        );
    """)

def fetch_historical_data(conn):
    logger.info("Fetching historical LinkedIn post engagement data from marts...")
    
    # Personal Account posts
    personal_query = """
        SELECT 
            published_at_berlin,
            COALESCE(impressions, 0) as impressions,
            COALESCE(total_interactions, 0) as total_interactions,
            COALESCE(engagement_rate, 0.0) as engagement_rate
        FROM marts.fct_linkedin_personal_account_post_engagement
        WHERE published_at_berlin IS NOT NULL;
    """
    
    # Company Page posts
    company_query = """
        SELECT 
            published_at_berlin,
            COALESCE(impressions, 0) as impressions,
            COALESCE(total_interactions, 0) as total_interactions,
            COALESCE(engagement_rate, 0.0) as engagement_rate
        FROM marts.fct_linkedin_company_page_post_engagement
        WHERE published_at_berlin IS NOT NULL;
    """
    
    try:
        df_personal = conn.execute(personal_query).df()
        df_personal['published_at_berlin'] = pd.to_datetime(df_personal['published_at_berlin'], utc=True).dt.tz_localize(None)
        df_personal['channel_type'] = 'personal'
    except Exception as e:
        logger.warning(f"Could not read from marts.fct_linkedin_personal_account_post_engagement: {e}")
        df_personal = pd.DataFrame(columns=['published_at_berlin', 'impressions', 'total_interactions', 'engagement_rate', 'channel_type'])
        
    try:
        df_company = conn.execute(company_query).df()
        df_company['published_at_berlin'] = pd.to_datetime(df_company['published_at_berlin'], utc=True).dt.tz_localize(None)
        df_company['channel_type'] = 'company'
    except Exception as e:
        logger.warning(f"Could not read from marts.fct_linkedin_company_page_post_engagement: {e}")
        df_company = pd.DataFrame(columns=['published_at_berlin', 'impressions', 'total_interactions', 'engagement_rate', 'channel_type'])
        
    df = pd.concat([df_personal, df_company], ignore_index=True)
    return df


def train_and_predict_timeslots():
    conn = get_motherduck_connection()
    try:
        initialize_schemas(conn)
        df = fetch_historical_data(conn)
        
        if df.empty or len(df) < 5:
            logger.warning(f"Insufficient historical LinkedIn engagement data to train ML model (got {len(df)} records). Using fallback heuristic rule.")
            generate_heuristic_recommendations(conn)
            return {"status": "success", "message": "Insufficient data; generated heuristic recommendations."}
        
        # Feature Engineering: Extract Day of Week and Hour of Day
        df['published_at_berlin'] = pd.to_datetime(df['published_at_berlin'])
        df['day_of_week'] = df['published_at_berlin'].dt.dayofweek # 0=Monday, 6=Sunday
        df['hour_of_day'] = df['published_at_berlin'].dt.hour
        
        # Save training data to ds_training schema
        logger.info("Saving aggregated historical features to ds_training.linkedin_post_history...")
        conn.execute("CREATE TABLE IF NOT EXISTS ds_training.linkedin_post_history AS SELECT * FROM df WHERE 1=0;")
        conn.execute("TRUNCATE TABLE ds_training.linkedin_post_history;")
        conn.execute("INSERT INTO ds_training.linkedin_post_history SELECT * FROM df;")
        
        results = {}
        
        for channel in ['personal', 'company']:
            df_chan = df[df['channel_type'] == channel].copy()
            if len(df_chan) < 3:
                logger.warning(f"Insufficient data for channel: {channel}. Using fallback heuristic for this channel.")
                generate_heuristic_for_channel(conn, channel)
                continue
                
            X = df_chan[['day_of_week', 'hour_of_day']].values
            y = df_chan['engagement_rate'].values
            
            model = RandomForestRegressor(n_estimators=50, random_state=42)
            model.fit(X, y)
            r2 = float(model.score(X, y))
            
            candidate_slots = []
            for dow in range(7):
                for hod in range(24):
                    candidate_slots.append({'day_of_week': dow, 'hour_of_day': hod})
            
            df_candidates = pd.DataFrame(candidate_slots)
            preds = model.predict(df_candidates[['day_of_week', 'hour_of_day']].values)
            df_candidates['predicted_engagement_rate'] = preds
            df_candidates['channel_type'] = channel
            
            df_candidates = df_candidates.sort_values(by='predicted_engagement_rate', ascending=False)
            df_candidates['recommendation_rank'] = range(1, len(df_candidates) + 1)
            
            logger.info(f"Saving timeslot predictions for channel {channel} to ds_prediction.timeslot_recommendations...")
            conn.execute("DELETE FROM ds_prediction.timeslot_recommendations WHERE channel_type = ?;", [channel])
            conn.execute("INSERT INTO ds_prediction.timeslot_recommendations SELECT channel_type, day_of_week, hour_of_day, predicted_engagement_rate, recommendation_rank, CURRENT_TIMESTAMP FROM df_candidates;")
            
            conn.execute("""
                INSERT INTO ds_prediction.model_metadata (model_name, channel_type, trained_at, r2_score, sample_size, hyperparameters)
                VALUES (?, ?, CURRENT_TIMESTAMP, ?, ?, ?);
            """, ["random_forest_timeslots", channel, r2, len(df_chan), "n_estimators=50"])
            
            results[channel] = {
                "sample_size": len(df_chan),
                "r2_score": r2,
                "top_slots": df_candidates.head(5)[['day_of_week', 'hour_of_day', 'predicted_engagement_rate']].to_dict(orient='records')
            }
            
        return {"status": "success", "results": results}
    finally:
        conn.close()

def generate_heuristic_recommendations(conn):
    for channel in ['personal', 'company']:
        generate_heuristic_for_channel(conn, channel)

def generate_heuristic_for_channel(conn, channel):
    conn.execute("DELETE FROM ds_prediction.timeslot_recommendations WHERE channel_type = ?;", [channel])
    
    candidate_slots = []
    for dow in range(7):
        for hod in range(24):
            rate = 0.01
            if dow in [1, 2, 3]:
                rate += 0.005
            if hod in [9, 12, 14, 17]:
                rate += 0.015
            elif hod in [8, 10, 11, 13, 15, 16]:
                rate += 0.005
                
            candidate_slots.append({
                'channel_type': channel,
                'day_of_week': dow,
                'hour_of_day': hod,
                'predicted_engagement_rate': rate
            })
            
    df_heuristics = pd.DataFrame(candidate_slots)
    df_heuristics = df_heuristics.sort_values(by='predicted_engagement_rate', ascending=False)
    df_heuristics['recommendation_rank'] = range(1, len(df_heuristics) + 1)
    
    conn.execute("INSERT INTO ds_prediction.timeslot_recommendations SELECT channel_type, day_of_week, hour_of_day, predicted_engagement_rate, recommendation_rank, CURRENT_TIMESTAMP FROM df_heuristics;")
    
    conn.execute("""
        INSERT INTO ds_prediction.model_metadata (model_name, channel_type, trained_at, r2_score, sample_size, hyperparameters)
        VALUES (?, ?, CURRENT_TIMESTAMP, 0.0, 0, ?);
    """, ["heuristic_fallback", channel, "heuristic_rules_v1"])
