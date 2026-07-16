import os
import logging
import duckdb
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("ml-service.utils")


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
    logger.info("Initializing ds_features, ds_training, and ds_prediction schemas in MotherDuck if not exist...")
    conn.execute("CREATE SCHEMA IF NOT EXISTS ds_features;")
    conn.execute("CREATE SCHEMA IF NOT EXISTS ds_training;")
    conn.execute("CREATE SCHEMA IF NOT EXISTS ds_prediction;")

    # Create a lightweight feature catalog for discoverability.
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ds_features.feature_catalog (
            feature_name VARCHAR(100),
            feature_table VARCHAR(100),
            entity_type VARCHAR(100),
            data_type VARCHAR(50),
            description VARCHAR(500),
            owner VARCHAR(100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE
        );
    """)

    # Reusable post-level features for LinkedIn publishing-time models.
    conn.execute("DROP TABLE IF EXISTS ds_features.linkedin_post_engagement_features;")
    conn.execute("""
        CREATE TABLE ds_features.linkedin_post_engagement_features (
            feature_row_id BIGINT,
            source_table VARCHAR(150),
            channel_type VARCHAR(50),
            published_at_berlin TIMESTAMP,
            content VARCHAR,
            day_of_week INTEGER,
            day_name VARCHAR(20),
            hour_of_day INTEGER,
            hour_bucket VARCHAR(20),
            is_weekend BOOLEAN,
            is_business_hour BOOLEAN,
            is_holiday_US BOOLEAN,
            is_holiday_DE BOOLEAN,
            likes DOUBLE,
            comments DOUBLE,
            shares DOUBLE,
            reposts DOUBLE,
            clicks DOUBLE,
            saves DOUBLE,
            sends DOUBLE,
            impressions DOUBLE,
            total_interactions DOUBLE,
            engagement_rate DOUBLE,
            has_cta BOOLEAN,
            has_question BOOLEAN,
            sentiment_score DOUBLE,
            sentiment_label VARCHAR(20),
            topic_id INTEGER,
            topic_label VARCHAR(200),
            feature_created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    # Create prediction recommendations table
    conn.execute("DROP TABLE IF EXISTS ds_prediction.timeslot_recommendations;")
    conn.execute("""
        CREATE TABLE ds_prediction.timeslot_recommendations (
            channel_type VARCHAR(50),
            day_of_week INTEGER,
            hour_of_day INTEGER,
            is_holiday_US BOOLEAN,
            is_holiday_DE BOOLEAN,
            predicted_impressions DOUBLE,
            predicted_total_interactions DOUBLE,
            predicted_engagement_rate DOUBLE,
            recommendation_rank INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (channel_type, day_of_week, hour_of_day, is_holiday_US, is_holiday_DE)
        );
    """)
    
    # Create model metadata table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ds_prediction.model_metadata (
            model_name VARCHAR(100),
            channel_type VARCHAR(50),
            trained_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            r2_score DOUBLE,
            val_mae DOUBLE,
            sample_size INTEGER,
            hyperparameters VARCHAR(255)
        );
    """)
    
    # Create validation results table to store actual vs predicted for audit/monitoring
    conn.execute("DROP TABLE IF EXISTS ds_training.validation_results;")
    conn.execute("""
        CREATE TABLE ds_training.validation_results (
            channel_type VARCHAR(50),
            published_at_berlin TIMESTAMP,
            day_of_week INTEGER,
            hour_of_day INTEGER,
            actual_impressions DOUBLE,
            predicted_impressions DOUBLE,
            actual_total_interactions DOUBLE,
            predicted_total_interactions DOUBLE,
            actual_engagement_rate DOUBLE,
            predicted_engagement_rate DOUBLE,
            evaluated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
