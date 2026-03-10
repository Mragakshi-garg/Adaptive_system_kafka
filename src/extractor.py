import pandas as pd
import os
import time

def extract_simulator_subset(
    chartevents_path='data/chartevents (1).csv.gz',
    output_path='data/subset_events.csv',
    num_patients=50
):
    print(f"Finding first {num_patients} patients with target signs in {chartevents_path}...")
    
    if not os.path.exists(chartevents_path):
        print(f"Error: {chartevents_path} not found.")
        return

    # Target Vital Signs:
    # 220045: Heart Rate
    # 220277: SpO2
    # 220179: Non-invasive Blood Pressure systolic
    # 220180: Non-invasive Blood Pressure diastolic
    # 220181: Non-invasive Blood Pressure mean
    target_item_ids = [220045, 220277, 220179, 220180, 220181]
    cols_to_use = ['subject_id', 'hadm_id', 'stay_id', 'charttime', 'itemid', 'valuenum']
    
    chunksize = 1000000 
    target_subjects = set()
    
    start_time = time.time()
    
    # Pass 1: Find target patients
    try:
        for chunk in pd.read_csv(chartevents_path, compression='gzip', chunksize=chunksize, usecols=cols_to_use):
            filtered_chunk = chunk[chunk['itemid'].isin(target_item_ids)]
            subjects_in_chunk = filtered_chunk['subject_id'].unique()
            
            for s in subjects_in_chunk:
                target_subjects.add(s)
                if len(target_subjects) >= num_patients:
                    break
                    
            if len(target_subjects) >= num_patients:
                break
    except Exception as e:
        print(f"Error reading chartevents for phase 1: {e}")
        return
        
    target_subjects = list(target_subjects)
    print(f"Selected {len(target_subjects)} subject_ids. Searching for their full records...")
    
    extracted_chunks = []
    total_chunks = 0
    total_rows = 0
    
    try:
        for chunk in pd.read_csv(chartevents_path, compression='gzip', chunksize=chunksize, usecols=cols_to_use):
            total_chunks += 1
            
            # Filter by exactly these subjects AND itemid
            filtered_chunk = chunk[
                (chunk['subject_id'].isin(target_subjects)) & 
                (chunk['itemid'].isin(target_item_ids))
            ]
            
            if not filtered_chunk.empty:
                extracted_chunks.append(filtered_chunk)
                total_rows += len(filtered_chunk)
                
            if total_chunks % 5 == 0:
                print(f"Processed {total_chunks} chunks... Found {total_rows} relevant events so far.")
                
            # We want to process some amount of the file to get interesting timelines but maybe not the whole 300+ chunks if developing
            if total_chunks >= 20: 
                print("Reached 20 chunks limit for development. Stopping extraction.")
                break
                
    except Exception as e:
         print(f"Error reading chartevents for phase 2: {e}")
         return
         
    if not extracted_chunks:
        print("No data found for the selected patients and item IDs in the processed chunks.")
        return
        
    print("Concatenating and sorting data...")
    final_df = pd.concat(extracted_chunks, ignore_index=True)
    
    # Drop rows with missing values
    final_df.dropna(subset=['valuenum', 'charttime', 'stay_id'], inplace=True)
    
    # Convert charttime to datetime for sorting
    final_df['charttime'] = pd.to_datetime(final_df['charttime'])
    
    # Sort chronologically
    final_df.sort_values(by='charttime', ascending=True, inplace=True)
    
    # Save to CSV
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    final_df.to_csv(output_path, index=False)
            
    print(f"Finished extraction! Total time: {time.time() - start_time:.2f}s")
    print(f"Output saved to {output_path} with {len(final_df)} chronological events for {final_df['subject_id'].nunique()} unique patients.")

if __name__ == "__main__":
    extract_simulator_subset()
