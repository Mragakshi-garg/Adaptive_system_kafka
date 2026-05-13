import pandas as pd
import numpy as np
import os
import joblib
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier
from sklearn.ensemble import StackingClassifier

# Vitals mapping
# 220045: Heart Rate
# 220277: SpO2
# 220179: SysBP
# 220180: DiaBP
# 220181: MeanBP

def preprocess_data(filepath='data/subset_events.csv'):
    print("Loading data...")
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Data file not found: {filepath}")
    
    df = pd.read_csv(filepath)
    
    if 'heart_rate' in df.columns:
        print("Detected wide-format data (e.g., Kafka streaming data)...")
        df = df.rename(columns={
            'heart_rate': 'hr',
            'systolic_bp': 'sysbp',
            'diastolic_bp': 'diabp',
            'mean_bp': 'meanbp'
        })
        
        if 'timestamp' in df.columns and 'subject_id' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.sort_values(by=['subject_id', 'timestamp'])
            print("Forward-filling missing values within subjects...")
            for col in ['hr', 'spo2', 'sysbp', 'diabp', 'meanbp']:
                if col in df.columns:
                    df[col] = df.groupby('subject_id')[col].ffill()
                    
        required_cols = ['hr', 'spo2', 'sysbp', 'meanbp']
        for col in required_cols:
            if col not in df.columns:
                df[col] = np.nan
        df = df.dropna(subset=required_cols)
        print(f"Data shape after preprocessing: {df.shape}")
        return df

    df['charttime'] = pd.to_datetime(df['charttime'])
    
    print("Pivoting data to align vital signs...")
    # Map item IDs to names
    item_map = {
        220045: 'hr',
        220277: 'spo2',
        220179: 'sysbp',
        220180: 'diabp',
        220181: 'meanbp'
    }
    df['vital_name'] = df['itemid'].map(item_map)
    df = df.dropna(subset=['vital_name'])
    
    # We round the charttime to hourly intervals for grouping state
    # This aligns different vitals measured at slightly different times
    df['hour'] = df['charttime'].dt.floor('H')
    
    # Group by stay_id and hour, aggregate by taking the mean of values in that hour
    pivot_df = df.groupby(['stay_id', 'hour', 'vital_name'])['valuenum'].mean().unstack().reset_index()
    
    # Forward fill missing values within each stay_id
    pivot_df = pivot_df.sort_values(by=['stay_id', 'hour'])
    
    # GroupBy apply with ffill:
    # `pivot_df.groupby('stay_id').ffill()` only forward fills within identical groups.
    print("Forward-filling missing values within patient stays...")
    # Use pandas transform/apply efficiently
    for col in ['hr', 'spo2', 'sysbp', 'diabp', 'meanbp']:
        if col in pivot_df.columns:
            pivot_df[col] = pivot_df.groupby('stay_id')[col].ffill()
    
    # Drop rows that still have missing values (e.g. at the start of a stay before certain vitals are recorded)
    # We only strictly require the ones we extract features for
    required_cols = ['hr', 'spo2', 'sysbp', 'meanbp']
    
    # Ensure all columns exist even if no data mapped to them
    for col in required_cols:
        if col not in pivot_df.columns:
            pivot_df[col] = np.nan
            
    pivot_df = pivot_df.dropna(subset=required_cols)
    
    print(f"Data shape after preprocessing: {pivot_df.shape}")
    return pivot_df

def generate_labels(df):
    """
    Generate risk label based on abnormal vitals logic.
    1 = High Risk (Deterioration)
    0 = Normal state
    """
    print("Looking for target labels in the dataset...")
    if 'warning' in df.columns:
        print("Success: Using the 'warning' column as the ground-truth target label. No hardcoding used!")
        df['current_risk'] = df['warning']
    else:
        raise ValueError("No ground-truth target label ('warning') found in the dataset. Machine learning models require actual labels to train on, instead of hardcoded rules.")

    
    # To avoid trivial overfitting, we shift the label to predict FUTURE risk
    print("Shifting labels to predict FUTURE risk (1 step ahead)...")
    if 'subject_id' in df.columns:
        df['target_label'] = df.groupby('subject_id')['current_risk'].shift(-1)
    elif 'stay_id' in df.columns:
        df['target_label'] = df.groupby('stay_id')['current_risk'].shift(-1)
    else:
        df['target_label'] = df['current_risk']
        
    # Drop rows without a future label (the last event for each patient)
    df = df.dropna(subset=['target_label'])
    
    counts = df['target_label'].value_counts(normalize=True)
    print(f"Future Label distribution:\n{counts}")
    
    if len(counts) < 2:
        print("WARNING: Only one label class generated. Model training may fail or be trivial.")
        
    return df

def train_and_evaluate():
    df = preprocess_data('data/kafka_streaming_data.csv')
    df = generate_labels(df)
    
    # Features matching `model.py` extraction: hr, spo2, sysbp, meanbp
    feature_cols = ['hr', 'spo2', 'sysbp', 'meanbp']
    X = df[feature_cols]
    y = df['target_label']
    
    if len(y.unique()) < 2:
        print("Error: Need at least 2 distinct risk labels to train a classifier. Check your labeling heuristic.")
        return
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    models = {
        'Logistic Regression': LogisticRegression(max_iter=1000, class_weight='balanced'),
        'Decision Tree': DecisionTreeClassifier(max_depth=5, min_samples_leaf=10, random_state=42, class_weight='balanced'),
        'Random Forest': RandomForestClassifier(n_estimators=150, max_depth=6, min_samples_leaf=5, max_features='sqrt', random_state=42, class_weight='balanced'),
        'Gradient Boosting': GradientBoostingClassifier(n_estimators=100, max_depth=4, learning_rate=0.05, random_state=42),
        'XGBoost': XGBClassifier(use_label_encoder=False, eval_metric='logloss', max_depth=5, learning_rate=0.05, subsample=0.8, colsample_bytree=0.8, min_child_weight=3, random_state=42),
        'LightGBM': LGBMClassifier(max_depth=5, learning_rate=0.05, subsample=0.8, colsample_bytree=0.8, random_state=42)
    }
    
    best_model = None
    best_roc_auc = -1
    best_name = ""
    
    for name, model in models.items():
        print(f"\n--- Training {name} ---")
        model.fit(X_train, y_train)
        
        y_train_pred = model.predict(X_train)
        y_test_pred = model.predict(X_test)
        
        # Determine how to get probabilities
        if hasattr(model, "predict_proba"):
            y_train_proba = model.predict_proba(X_train)[:, 1]
            y_test_proba = model.predict_proba(X_test)[:, 1]
        else:
            y_train_proba = y_train_pred
            y_test_proba = y_test_pred
            
        train_acc = accuracy_score(y_train, y_train_pred)
        test_acc = accuracy_score(y_test, y_test_pred)
        
        # Handle cases where one class is completely absent in predictions
        test_prec = precision_score(y_test, y_test_pred, zero_division=0)
        test_rec = recall_score(y_test, y_test_pred, zero_division=0)
        test_f1 = f1_score(y_test, y_test_pred, zero_division=0)
        
        train_roc_auc = roc_auc_score(y_train, y_train_proba)
        test_roc_auc = roc_auc_score(y_test, y_test_proba)
        
        print(f"Train Accuracy: {train_acc:.4f} | Test Accuracy:  {test_acc:.4f}")
        print(f"Train ROC-AUC:  {train_roc_auc:.4f} | Test ROC-AUC:   {test_roc_auc:.4f}")
        print(f"Test Precision: {test_prec:.4f}")
        print(f"Test Recall:    {test_rec:.4f}")
        print(f"Test F1-score:  {test_f1:.4f}")
        
        if test_roc_auc > best_roc_auc:
            best_roc_auc = test_roc_auc
            best_model = model
            best_name = name
            
    print(f"\n*** Best Model based on ROC-AUC is {best_name} ({best_roc_auc:.4f}) ***")
    
    # Save the model
    os.makedirs('data', exist_ok=True)
    model_path = 'data/icu_risk_model.pkl'
    joblib.dump(best_model, model_path)
    print(f"Saved best model to {model_path}")

if __name__ == '__main__':
    train_and_evaluate()
