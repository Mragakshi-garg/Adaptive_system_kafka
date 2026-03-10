import random

class RiskPredictor:
    def __init__(self, model_path=None):
        """
        Initialize the ML model.
        In a real scenario, this would load a trained XGBoost or LightGBM model:
        import xgboost as xgb
        self.model = xgb.Booster()
        self.model.load_model(model_path)
        """
        self.model_path = model_path

    def extract_features(self, state):
        """
        Convert patient state into a feature vector.
        """
        vitals = state.get('vitals', {})
        
        # We fill missing values with normal ranges for the model
        hr = vitals.get('hr') or 80.0
        spo2 = vitals.get('spo2') or 98.0
        sysbp = vitals.get('sysbp') or 120.0
        meanbp = vitals.get('meanbp') or 85.0
        
        return [hr, spo2, sysbp, meanbp]

    def predict_risk(self, state):
        """
        Given the current state, returns a risk probability (0.0 to 1.0) for Sepsis / Decompensation.
        
        NOTE: This is a BASELINE heuristic model to prove the pipeline. 
        You should replace `risk_score` with `self.model.predict(features)`.
        """
        features = self.extract_features(state)
        hr, spo2, sysbp, meanbp = features
        
        # Simple heuristic risk calculation
        risk_score = 0.05  # Base risk
        
        if hr > 110: risk_score += 0.2
        if hr > 130: risk_score += 0.2
        
        if sysbp < 100: risk_score += 0.2
        if sysbp < 90: risk_score += 0.3
        
        if meanbp < 65: risk_score += 0.2
        
        if spo2 < 92: risk_score += 0.2
        
        # Cap at 0.99
        risk_score = min(0.99, risk_score)
        
        return risk_score
