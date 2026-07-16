import datetime
import pickle
import logging
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from utils import get_motherduck_connection, initialize_schemas
from linkedin_publishing_timeslot.nlp_features import extract_text_features, extract_topic_features

logger = logging.getLogger("ml-service.linkedin_timeslot.train")


def utc_now_naive():
    return datetime.datetime.now(datetime.UTC).replace(tzinfo=None)

def fetch_historical_data(conn):
    logger.info("Fetching historical LinkedIn post engagement data from marts...")
    
    # Personal Account posts
    personal_query = """
        SELECT 
            published_at_berlin,
            COALESCE(content, '') as content,
            COALESCE(impressions, 0) as impressions,
            COALESCE(likes, 0) as likes,
            COALESCE(comments, 0) as comments,
            COALESCE(shares, 0) as shares,
            COALESCE(reposts, 0) as reposts,
            COALESCE(clicks, 0) as clicks,
            COALESCE(saves, 0) as saves,
            COALESCE(sends, 0) as sends,
            COALESCE(total_interactions, 0) as total_interactions,
            COALESCE(engagement_rate, 0.0) as engagement_rate
        FROM marts.fct_linkedin_personal_account_post_engagement
        WHERE published_at_berlin IS NOT NULL;
    """
    
    # Company Page posts
    company_query = """
        SELECT 
            published_at_berlin,
            COALESCE(content, '') as content,
            COALESCE(impressions, 0) as impressions,
            COALESCE(likes, 0) as likes,
            COALESCE(comments, 0) as comments,
            COALESCE(shares, 0) as shares,
            0 as reposts,
            COALESCE(clicks, 0) as clicks,
            COALESCE(saves, 0) as saves,
            COALESCE(sends, 0) as sends,
            COALESCE(total_interactions, 0) as total_interactions,
            COALESCE(engagement_rate, 0.0) as engagement_rate
        FROM marts.fct_linkedin_company_page_post_engagement
        WHERE published_at_berlin IS NOT NULL;
    """
    
    try:
        df_personal = conn.execute(personal_query).df()
        df_personal['published_at_berlin'] = pd.to_datetime(df_personal['published_at_berlin'], utc=True).dt.tz_localize(None)
        df_personal['channel_type'] = 'personal'
        df_personal['source_table'] = 'marts.fct_linkedin_personal_account_post_engagement'
    except Exception as e:
        logger.warning(f"Could not read from marts.fct_linkedin_personal_account_post_engagement: {e}")
        df_personal = pd.DataFrame(columns=['published_at_berlin', 'content', 'impressions', 'likes', 'comments', 'shares', 'reposts', 'clicks', 'saves', 'sends', 'total_interactions', 'engagement_rate', 'channel_type', 'source_table'])
        
    try:
        df_company = conn.execute(company_query).df()
        df_company['published_at_berlin'] = pd.to_datetime(df_company['published_at_berlin'], utc=True).dt.tz_localize(None)
        df_company['channel_type'] = 'company'
        df_company['source_table'] = 'marts.fct_linkedin_company_page_post_engagement'
    except Exception as e:
        logger.warning(f"Could not read from marts.fct_linkedin_company_page_post_engagement: {e}")
        df_company = pd.DataFrame(columns=['published_at_berlin', 'content', 'impressions', 'likes', 'comments', 'shares', 'reposts', 'clicks', 'saves', 'sends', 'total_interactions', 'engagement_rate', 'channel_type', 'source_table'])
        
    df = pd.concat([df_personal, df_company], ignore_index=True)
    return df

def fetch_public_holidays(conn):
    logger.info("Fetching public holiday data from marts...")
    query = """
        SELECT 
            holiday_date,
            country_code
        FROM marts.dim_public_holidays
        WHERE country_code IN ('US', 'DE');
    """
    try:
        df_holidays = conn.execute(query).df()
        return df_holidays
    except Exception as e:
        logger.warning(f"Could not read from marts.dim_public_holidays: {e}")
        return pd.DataFrame(columns=['holiday_date', 'country_code'])

def _hour_bucket(hour):
    if 5 <= hour < 12:
        return 'morning'
    if 12 <= hour < 17:
        return 'afternoon'
    if 17 <= hour < 22:
        return 'evening'
    return 'overnight'

def build_linkedin_post_engagement_features(df, df_holidays=None):
    features = df.copy()
    features['published_at_berlin'] = pd.to_datetime(features['published_at_berlin'])
    features['day_of_week'] = features['published_at_berlin'].dt.dayofweek.astype(int)
    features['day_name'] = features['published_at_berlin'].dt.day_name()
    features['hour_of_day'] = features['published_at_berlin'].dt.hour.astype(int)
    features['hour_bucket'] = features['hour_of_day'].apply(_hour_bucket)
    features['is_weekend'] = features['day_of_week'].isin([5, 6])
    features['is_business_hour'] = features['hour_of_day'].between(9, 17)
    
    # Process holiday features
    features['publish_date'] = features['published_at_berlin'].dt.date
    for country in ['US', 'DE']:
        features[f'is_holiday_{country}'] = False
        
    if df_holidays is not None and not df_holidays.empty:
        df_holidays_normalized = df_holidays.copy()
        df_holidays_normalized['holiday_date'] = pd.to_datetime(df_holidays_normalized['holiday_date']).dt.date
        for country in ['US', 'DE']:
            country_holidays = set(df_holidays_normalized[df_holidays_normalized['country_code'] == country]['holiday_date'])
            features[f'is_holiday_{country}'] = features['publish_date'].apply(lambda d: d in country_holidays)
            
    features = features.drop(columns=['publish_date'])

    # NLP content features
    features = extract_text_features(features)
    features = extract_topic_features(features)

    features['feature_row_id'] = range(1, len(features) + 1)
    features['feature_created_at'] = utc_now_naive()

    feature_columns = [
        'feature_row_id',
        'source_table',
        'channel_type',
        'published_at_berlin',
        'day_of_week',
        'day_name',
        'hour_of_day',
        'hour_bucket',
        'is_weekend',
        'is_business_hour',
        'is_holiday_US',
        'is_holiday_DE',
        'likes',
        'comments',
        'shares',
        'reposts',
        'clicks',
        'saves',
        'sends',
        'impressions',
        'total_interactions',
        'engagement_rate',
        'has_cta',
        'has_question',
        'sentiment_score',
        'sentiment_label',
        'topic_id',
        'topic_label',
        'feature_created_at'
    ]
    return features[feature_columns]

def save_feature_catalog(conn):
    conn.execute("DELETE FROM ds_features.feature_catalog WHERE feature_table = 'linkedin_post_engagement_features';")
    catalog_rows = [
        {
            'feature_name': 'day_of_week',
            'feature_table': 'linkedin_post_engagement_features',
            'entity_type': 'linkedin_post',
            'data_type': 'INTEGER',
            'description': 'Day of week extracted from published_at_berlin, with Monday as 0 and Sunday as 6.',
            'owner': 'ml-service',
            'is_active': True
        },
        {
            'feature_name': 'hour_of_day',
            'feature_table': 'linkedin_post_engagement_features',
            'entity_type': 'linkedin_post',
            'data_type': 'INTEGER',
            'description': 'Hour of day extracted from published_at_berlin in Europe/Berlin time.',
            'owner': 'ml-service',
            'is_active': True
        },
        {
            'feature_name': 'is_weekend',
            'feature_table': 'linkedin_post_engagement_features',
            'entity_type': 'linkedin_post',
            'data_type': 'BOOLEAN',
            'description': 'True when published_at_berlin falls on Saturday or Sunday.',
            'owner': 'ml-service',
            'is_active': True
        },
        {
            'feature_name': 'is_business_hour',
            'feature_table': 'linkedin_post_engagement_features',
            'entity_type': 'linkedin_post',
            'data_type': 'BOOLEAN',
            'description': 'True when hour_of_day falls between 9 and 17 inclusive.',
            'owner': 'ml-service',
            'is_active': True
        },
        {
            'feature_name': 'hour_bucket',
            'feature_table': 'linkedin_post_engagement_features',
            'entity_type': 'linkedin_post',
            'data_type': 'VARCHAR',
            'description': 'Coarse publishing-time bucket: morning, afternoon, evening, or overnight.',
            'owner': 'ml-service',
            'is_active': True
        },
        {
            'feature_name': 'is_holiday_US',
            'feature_table': 'linkedin_post_engagement_features',
            'entity_type': 'linkedin_post',
            'data_type': 'BOOLEAN',
            'description': 'True when publishing date falls on a public holiday in the US.',
            'owner': 'ml-service',
            'is_active': True
        },
        {
            'feature_name': 'is_holiday_DE',
            'feature_table': 'linkedin_post_engagement_features',
            'entity_type': 'linkedin_post',
            'data_type': 'BOOLEAN',
            'description': 'True when publishing date falls on a public holiday in Germany.',
            'owner': 'ml-service',
            'is_active': True
        },
        {
            'feature_name': 'likes',
            'feature_table': 'linkedin_post_engagement_features',
            'entity_type': 'linkedin_post',
            'data_type': 'DOUBLE',
            'description': 'Number of likes received by the post.',
            'owner': 'ml-service',
            'is_active': True
        },
        {
            'feature_name': 'comments',
            'feature_table': 'linkedin_post_engagement_features',
            'entity_type': 'linkedin_post',
            'data_type': 'DOUBLE',
            'description': 'Number of comments received by the post.',
            'owner': 'ml-service',
            'is_active': True
        },
        {
            'feature_name': 'shares',
            'feature_table': 'linkedin_post_engagement_features',
            'entity_type': 'linkedin_post',
            'data_type': 'DOUBLE',
            'description': 'Number of shares received by the post.',
            'owner': 'ml-service',
            'is_active': True
        },
        {
            'feature_name': 'reposts',
            'feature_table': 'linkedin_post_engagement_features',
            'entity_type': 'linkedin_post',
            'data_type': 'DOUBLE',
            'description': 'Number of reposts received by the post.',
            'owner': 'ml-service',
            'is_active': True
        },
        {
            'feature_name': 'clicks',
            'feature_table': 'linkedin_post_engagement_features',
            'entity_type': 'linkedin_post',
            'data_type': 'DOUBLE',
            'description': 'Number of clicks received by the post.',
            'owner': 'ml-service',
            'is_active': True
        },
        {
            'feature_name': 'saves',
            'feature_table': 'linkedin_post_engagement_features',
            'entity_type': 'linkedin_post',
            'data_type': 'DOUBLE',
            'description': 'Number of saves received by the post.',
            'owner': 'ml-service',
            'is_active': True
        },
        {
            'feature_name': 'sends',
            'feature_table': 'linkedin_post_engagement_features',
            'entity_type': 'linkedin_post',
            'data_type': 'DOUBLE',
            'description': 'Number of sends received by the post.',
            'owner': 'ml-service',
            'is_active': True
        },
        {
            'feature_name': 'has_cta',
            'feature_table': 'linkedin_post_engagement_features',
            'entity_type': 'linkedin_post',
            'data_type': 'BOOLEAN',
            'description': 'True when post content contains a call-to-action phrase (e.g. let me know, comment below, share this).',
            'owner': 'ml-service',
            'is_active': True
        },
        {
            'feature_name': 'has_question',
            'feature_table': 'linkedin_post_engagement_features',
            'entity_type': 'linkedin_post',
            'data_type': 'BOOLEAN',
            'description': 'True when post content contains a question mark or starts with a question word.',
            'owner': 'ml-service',
            'is_active': True
        },
        {
            'feature_name': 'sentiment_score',
            'feature_table': 'linkedin_post_engagement_features',
            'entity_type': 'linkedin_post',
            'data_type': 'DOUBLE',
            'description': 'VADER compound sentiment score from -1.0 (very negative) to 1.0 (very positive).',
            'owner': 'ml-service',
            'is_active': True
        },
        {
            'feature_name': 'sentiment_label',
            'feature_table': 'linkedin_post_engagement_features',
            'entity_type': 'linkedin_post',
            'data_type': 'VARCHAR',
            'description': 'Sentiment label derived from VADER compound score: positive (>=0.05), negative (<=-0.05), neutral.',
            'owner': 'ml-service',
            'is_active': True
        },
        {
            'feature_name': 'topic_id',
            'feature_table': 'linkedin_post_engagement_features',
            'entity_type': 'linkedin_post',
            'data_type': 'INTEGER',
            'description': 'BERTopic cluster ID assigned to the post. -1 indicates outlier or insufficient data for modeling.',
            'owner': 'ml-service',
            'is_active': True
        },
        {
            'feature_name': 'topic_label',
            'feature_table': 'linkedin_post_engagement_features',
            'entity_type': 'linkedin_post',
            'data_type': 'VARCHAR',
            'description': 'Top 3 keywords representing the BERTopic cluster assigned to the post.',
            'owner': 'ml-service',
            'is_active': True
        }
    ]
    df_catalog = pd.DataFrame(catalog_rows)
    conn.register("df_catalog", df_catalog)
    conn.execute("""
        INSERT INTO ds_features.feature_catalog (
            feature_name, feature_table, entity_type, data_type, description, owner, is_active
        )
        SELECT feature_name, feature_table, entity_type, data_type, description, owner, is_active
        FROM df_catalog;
    """)

def save_linkedin_feature_store(conn, df, df_holidays=None):
    logger.info("Saving LinkedIn post engagement features to ds_features.linkedin_post_engagement_features...")
    df_features = build_linkedin_post_engagement_features(df, df_holidays)
    conn.execute("""
        CREATE OR REPLACE TABLE ds_features.linkedin_post_engagement_features AS
        SELECT
            feature_row_id,
            source_table,
            channel_type,
            published_at_berlin,
            day_of_week,
            day_name,
            hour_of_day,
            hour_bucket,
            is_weekend,
            is_business_hour,
            is_holiday_US,
            is_holiday_DE,
            likes,
            comments,
            shares,
            reposts,
            clicks,
            saves,
            sends,
            impressions,
            total_interactions,
            engagement_rate,
            has_cta,
            has_question,
            sentiment_score,
            sentiment_label,
            topic_id,
            topic_label,
            feature_created_at
        FROM df_features;
    """)
    save_feature_catalog(conn)
    return df_features

def train_and_validate():
    conn = get_motherduck_connection()
    try:
        initialize_schemas(conn)
        df = fetch_historical_data(conn)
        df_holidays = fetch_public_holidays(conn)
        
        if df.empty or len(df) < 5:
            logger.warning(f"Insufficient historical data to train model. Got {len(df)} records.")
            return {"status": "error", "message": f"Insufficient historical data to train model ({len(df)} records)."}
            
        df_features = save_linkedin_feature_store(conn, df, df_holidays)
        
        # Save training data to ds_training schema
        logger.info("Saving LinkedIn timeslot training set to ds_training.linkedin_post_history...")
        conn.execute("CREATE OR REPLACE TABLE ds_training.linkedin_post_history AS SELECT * FROM df_features;")
        
        # Truncate old validation results
        conn.execute("TRUNCATE TABLE ds_training.validation_results;")
        
        results = {}
        
        for channel in ['personal', 'company']:
            df_chan = df_features[df_features['channel_type'] == channel].copy()
            if len(df_chan) < 5:
                logger.warning(f"Insufficient data for channel {channel} to train/validate. Using fallback heuristic.")
                generate_heuristic_for_channel(conn, channel)
                results[channel] = {"status": "heuristic_fallback", "sample_size": len(df_chan)}
                continue
                
            # Time-based split: sort and hold out the last 20% for validation
            df_chan = df_chan.sort_values(by='published_at_berlin').reset_index(drop=True)
            split_idx = int(len(df_chan) * 0.8)
            df_train = df_chan.iloc[:split_idx].copy()
            df_val = df_chan.iloc[split_idx:].copy()
            
            # Train model
            feature_cols = [
                'day_of_week', 'hour_of_day',
                'is_holiday_US', 'is_holiday_DE',
                'has_cta', 'has_question',
                'sentiment_score', 'topic_id'
            ]
            X_train = df_train[feature_cols].values
            X_val = df_val[feature_cols].values
            
            models = {}
            r2_scores = {}
            maes = {}
            preds_val = {}
            
            targets = ['impressions', 'total_interactions', 'engagement_rate']
            for target in targets:
                y_train = df_train[target].values
                y_val = df_val[target].values
                
                model = RandomForestRegressor(n_estimators=50, random_state=42)
                model.fit(X_train, y_train)
                r2 = float(model.score(X_train, y_train))
                r2_scores[target] = r2
                
                pred_v = model.predict(X_val)
                mae = float(np.mean(np.abs(pred_v - y_val)))
                maes[target] = mae
                
                models[target] = model
                preds_val[target] = pred_v
            
            # Prepare dataframe matching validation_results table structure
            df_val_insert = pd.DataFrame({
                'channel_type': df_val['channel_type'],
                'published_at_berlin': df_val['published_at_berlin'],
                'day_of_week': df_val['day_of_week'].astype(int),
                'hour_of_day': df_val['hour_of_day'].astype(int),
                'actual_impressions': df_val['impressions'].astype(float),
                'predicted_impressions': preds_val['impressions'].astype(float),
                'actual_total_interactions': df_val['total_interactions'].astype(float),
                'predicted_total_interactions': preds_val['total_interactions'].astype(float),
                'actual_engagement_rate': df_val['engagement_rate'].astype(float),
                'predicted_engagement_rate': preds_val['engagement_rate'].astype(float)
            })
            
            # Insert using DuckDB registered dataframe query
            conn.execute("""
                INSERT INTO ds_training.validation_results (
                    channel_type, published_at_berlin, day_of_week, hour_of_day, 
                    actual_impressions, predicted_impressions, 
                    actual_total_interactions, predicted_total_interactions, 
                    actual_engagement_rate, predicted_engagement_rate
                ) 
                SELECT 
                    channel_type, published_at_berlin, day_of_week, hour_of_day, 
                    actual_impressions, predicted_impressions, 
                    actual_total_interactions, predicted_total_interactions, 
                    actual_engagement_rate, predicted_engagement_rate 
                FROM df_val_insert;
            """)
            
            # Serialize model and save in ds_training model registry
            model_bytes = pickle.dumps(models)
            conn.execute("CREATE TABLE IF NOT EXISTS ds_training.model_registry (channel_type VARCHAR(50) PRIMARY KEY, model_data BYTEA, trained_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);")
            
            trained_at_val = utc_now_naive()
            conn.execute("""
                INSERT INTO ds_training.model_registry (channel_type, model_data, trained_at)
                VALUES (?, ?, ?)
                ON CONFLICT (channel_type) 
                DO UPDATE SET 
                    model_data = EXCLUDED.model_data, 
                    trained_at = EXCLUDED.trained_at;
            """, [channel, model_bytes, trained_at_val])
            
            # Save metadata
            for target in targets:
                conn.execute("""
                    INSERT INTO ds_prediction.model_metadata (model_name, channel_type, trained_at, r2_score, val_mae, sample_size, hyperparameters)
                    VALUES (?, ?, CURRENT_TIMESTAMP, ?, ?, ?, ?);
                """, [f"rf_{target}", channel, r2_scores[target], maes[target], len(df_chan), "n_estimators=50"])
            
            results[channel] = {
                "status": "trained",
                "sample_size": len(df_chan),
                "r2_scores": r2_scores,
                "val_maes": maes
            }
            
        return {"status": "success", "results": results}
    finally:
        conn.close()

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
                
            for hol_us in [False, True]:
                for hol_de in [False, True]:
                    candidate_slots.append({
                        'channel_type': channel,
                        'day_of_week': dow,
                        'hour_of_day': hod,
                        'is_holiday_US': hol_us,
                        'is_holiday_DE': hol_de,
                        'predicted_impressions': 100.0,
                        'predicted_total_interactions': rate * 100.0,
                        'predicted_engagement_rate': rate
                    })
            
    df_heuristics = pd.DataFrame(candidate_slots)
    df_heuristics['recommendation_rank'] = df_heuristics.groupby(
        ['is_holiday_US', 'is_holiday_DE']
    )['predicted_total_interactions'].rank(
        ascending=False, method='first'
    ).astype(int)
    
    conn.execute("""
        INSERT INTO ds_prediction.timeslot_recommendations (
            channel_type, day_of_week, hour_of_day, 
            is_holiday_US, is_holiday_DE,
            predicted_impressions, predicted_total_interactions, predicted_engagement_rate, 
            recommendation_rank, created_at
        )
        SELECT 
            channel_type, day_of_week, hour_of_day, 
            is_holiday_US, is_holiday_DE,
            predicted_impressions, predicted_total_interactions, predicted_engagement_rate, 
            recommendation_rank, CURRENT_TIMESTAMP 
        FROM df_heuristics;
    """)
    
    conn.execute("""
        INSERT INTO ds_prediction.model_metadata (model_name, channel_type, trained_at, r2_score, val_mae, sample_size, hyperparameters)
        VALUES (?, ?, CURRENT_TIMESTAMP, 0.0, 0.0, 0, ?);
    """, ["heuristic_fallback", channel, "heuristic_rules_v1"])
