import pickle
import logging
import pandas as pd
from utils import get_motherduck_connection, initialize_schemas
from linkedin_publishing_timeslot.train_pipeline import generate_heuristic_for_channel

logger = logging.getLogger("ml-service.linkedin_timeslot.predict")

def generate_predictions():
    conn = get_motherduck_connection()
    try:
        initialize_schemas(conn)
        
        # Check if we have registered models
        tables = [t[0] for t in conn.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'ds_training';").fetchall()]
        has_registry = 'model_registry' in tables
        
        results = {}
        for channel in ['personal', 'company']:
            model = None
            if has_registry:
                res = conn.execute("SELECT model_data FROM ds_training.model_registry WHERE channel_type = ?;", [channel]).fetchone()
                if res:
                    model = pickle.loads(res[0])
            
            if model is None:
                logger.warning(f"No trained model found for channel {channel}. Generating heuristic predictions.")
                generate_heuristic_for_channel(conn, channel)
                results[channel] = {"prediction_type": "heuristic"}
                continue
                
            # Create all 168 candidate slots
            candidate_slots = []
            for dow in range(7):
                for hod in range(24):
                    candidate_slots.append({
                        'day_of_week': dow,
                        'hour_of_day': hod,
                        'is_holiday_US': False,
                        'is_holiday_DE': False,
                        'is_holiday_FR': False,
                        'is_holiday_IN': False
                    })
                    
            df_candidates = pd.DataFrame(candidate_slots)
            feature_cols = ['day_of_week', 'hour_of_day', 'is_holiday_US', 'is_holiday_DE', 'is_holiday_FR', 'is_holiday_IN']
            preds = model.predict(df_candidates[feature_cols].values)
            df_candidates['predicted_engagement_rate'] = preds
            df_candidates['channel_type'] = channel
            
            df_candidates = df_candidates.sort_values(by='predicted_engagement_rate', ascending=False)
            df_candidates['recommendation_rank'] = range(1, len(df_candidates) + 1)
            
            # Save predictions
            conn.execute("DELETE FROM ds_prediction.timeslot_recommendations WHERE channel_type = ?;", [channel])
            conn.execute("INSERT INTO ds_prediction.timeslot_recommendations SELECT channel_type, day_of_week, hour_of_day, predicted_engagement_rate, recommendation_rank, CURRENT_TIMESTAMP FROM df_candidates;")
            
            results[channel] = {
                "prediction_type": "ml_model",
                "top_slots": df_candidates.head(5)[['day_of_week', 'hour_of_day', 'predicted_engagement_rate']].to_dict(orient='records')
            }
            
        return {"status": "success", "results": results}
    finally:
        conn.close()
