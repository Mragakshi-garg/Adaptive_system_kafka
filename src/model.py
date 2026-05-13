import pandas as pd
import joblib
import os

FEATURE_COLS = ['hr', 'spo2', 'sysbp', 'meanbp']

class RiskPredictor:
    def __init__(self, model_path='data/icu_risk_model.pkl'):
        self.model_path = model_path
        self.model = None

        if os.path.exists(self.model_path):
            try:
                self.model = joblib.load(self.model_path)
                print(f"ML model loaded from {self.model_path}")
            except Exception as e:
                print(f"Failed to load model: {e}. Using heuristic fallback.")
        else:
            print(f"Model not found at {self.model_path}. Using heuristic fallback.")

    def predict_risk(self, heart_rate, spo2, systolic_bp, mean_bp):
        """
        Takes 4 flat vital values.
        Returns risk probability from 0.0 to 1.0.
        """
        df = pd.DataFrame(
            [[heart_rate, spo2, systolic_bp, mean_bp]],
            columns=FEATURE_COLS
        )

        if self.model is not None:
            try:
                if hasattr(self.model, "predict_proba"):
                    prob = float(self.model.predict_proba(df)[0][1])
                else:
                    prob = float(self.model.predict(df)[0])
                return round(prob, 3)
            except Exception as e:
                print(f"Model prediction failed: {e}. Using heuristic.")

        # Heuristic fallback — used if model missing or crashes
        risk = 0.05

        if heart_rate > 110: risk += 0.20
        if heart_rate > 130: risk += 0.20
        if heart_rate < 50:  risk += 0.30

        if systolic_bp < 100: risk += 0.20
        if systolic_bp < 90:  risk += 0.30

        if mean_bp < 65: risk += 0.20

        if spo2 < 92: risk += 0.20
        if spo2 < 85: risk += 0.20

        return round(min(0.99, risk), 3)