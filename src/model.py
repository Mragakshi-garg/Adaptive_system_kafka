import pandas as pd
import joblib
import os

class RiskPredictor:
    def __init__(self, model_path='data/icu_risk_model.pkl'):
        """
        Initialize the ML model.
        Loads a trained model using joblib. Falls back to None if not found,
        triggering heuristic fallback in predict_risk.
        """
        self.model_path = model_path
        self.model = None
        
        if os.path.exists(self.model_path):
            try:
                self.model = joblib.load(self.model_path)
                print(f"✅ Successfully loaded ML model from {self.model_path}")
            except Exception as e:
                print(f"⚠️ Failed to load ML model from {self.model_path}: {e}")
        else:
            print(f"⚠️ Warning: Model file {self.model_path} not found. Falling back to heuristic baseline.")

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
        """
        features = self.extract_features(state)
        
        if self.model is not None:
            # We format features as a DataFrame to avoid feature name mismatch warnings
            # from XGBoost/Scikit-Learn which looks for 'hr', 'spo2', 'sysbp', 'meanbp'
            feature_cols = ['hr', 'spo2', 'sysbp', 'meanbp']
            df = pd.DataFrame([features], columns=feature_cols)
            
            # predict_proba returns array shape (1, 2). Class index 1 is high risk.
            if hasattr(self.model, "predict_proba"):
                prob = float(self.model.predict_proba(df)[0][1])
            else:
                prob = float(self.model.predict(df)[0])
                
            return prob
            
        else:
            # Fallback heuristic
            hr, spo2, sysbp, meanbp = features
            
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
