import streamlit as st
import pandas as pd
import json
import time

st.set_page_config(layout="wide", page_title="ICU Simulator Dashboard")

st.title("🏥 Real-Time ICU Data Simulator")
st.markdown("Live monitoring of patients and predictive alerts for early deterioration.")

# Create an empty container to hold the live-updating table
placeholder = st.empty()

while True:
    try:
        with open('data/current_state.json', 'r') as f:
            data = json.load(f)
            
        if not data:
            with placeholder.container():
                st.info("Waiting for data stream... Run `python src/main.py` first.")
        else:
            with placeholder.container():
                # Present summary metrics
                active = len(data)
                critical = sum(1 for s in data.values() if s.get('current_risk', 0) > 0.6)
                
                col1, col2, col3 = st.columns(3)
                col1.metric("Active Patients", active)
                col2.metric("Critical Alerts", critical)
                col3.metric("Highest Risk", f"{max((s.get('current_risk', 0) for s in data.values()), default=0.0):.2f}")
                
                st.markdown("---")
                
                # Display metrics as a dataframe
                df_data = []
                for stay_id, s in data.items():
                    r = s.get('current_risk', 0.0)
                    v = s.get('vitals', {})
                    
                    # Highlight critical risk
                    alert_status = "🚨 CRITICAL" if r >= 0.6 else ("⚠️ WARNING" if r >= 0.3 else "✅ OK")
                    
                    df_data.append({
                        '🚨 Status': alert_status,
                        'Risk Score': r,
                        'Patient ID': s['subject_id'],
                        'Last Update': s['last_update'],
                        'HR': v.get('hr'),
                        'SpO2': v.get('spo2'),
                        'BP (Sys/Dia)': f"{v.get('sysbp')}/{v.get('diabp')}",
                        'MAP': v.get('meanbp')
                    })
                
                df = pd.DataFrame(df_data)
                
                if not df.empty:
                    # Sort by highest risk first
                    df.sort_values(by='Risk Score', ascending=False, inplace=True)
                    
                    # Format float columns
                    df['Risk Score'] = df['Risk Score'].apply(lambda x: f"{x:.2f}")
                    st.dataframe(df, use_container_width=True, hide_index=True)
    
    except (FileNotFoundError, json.JSONDecodeError):
        with placeholder.container():
            st.info("System offline. Start the simulator: `python src/main.py`")
            
    # Use a tiny sleep to yield execution but update nearly instantly
    time.sleep(0.05)
