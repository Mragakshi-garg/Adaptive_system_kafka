import pandas as pd
import os
import time

def process_mimic_vitals(
    chartevents_path='data/chartevents (1).csv.gz',
    patients_path='data/patients.csv.gz',
    output_path='processed_bp_data.csv',
    max_chunks=50
):
    print("Loading patients data...")
    # Load patients table
    patients_df = pd.read_csv(patients_path, usecols=['subject_id', 'gender', 'anchor_age'])
    patients_df.rename(columns={'anchor_age': 'age'}, inplace=True)
    
    # Target BP Item IDs
    # 220179: Non-invasive Blood Pressure systolic
    # 220180: Non-invasive Blood Pressure diastolic
    # 220181: Non-invasive Blood Pressure mean
    target_item_ids = [220179, 220180, 220181]
    
    # Columns to keep from chartevents
    cols_to_use = ['subject_id', 'hadm_id', 'stay_id', 'charttime', 'itemid', 'valuenum', 'warning']
    
    chunksize = 1000000 # 1 million rows per chunk
    
    # Check if file exists and remove it so we can append fresh data
    try:
        if os.path.exists(output_path):
            os.remove(output_path)
    except PermissionError:
        output_path = 'processed_bp_data_new.csv'
        print(f"Warning: output file is locked. Using fallback path: {output_path}")
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except:
                pass
        
    total_chunks = 0
    max_rows = 10000
    target_warning_rows = 1250
    start_time = time.time()
    
    warning_collected = []
    normal_collected = []
    
    print(f"Processing chartevents until {max_rows} BP records are found (aiming for ~{target_warning_rows} warning rows)...")
    # Read chartevents in chunks
    for chunk in pd.read_csv(chartevents_path, compression='gzip', chunksize=chunksize, usecols=cols_to_use):
        total_chunks += 1
        
        # Filter for our specific BP item IDs
        filtered_chunk = chunk[chunk['itemid'].isin(target_item_ids)]
        
        if filtered_chunk.empty:
            if total_chunks % 1 == 0:
                print(f"Processed {total_chunks} chunks...")
            if total_chunks >= max_chunks:
                break
            continue
            
        # Pivot the data so that itemids become columns for our BP readngs
        # Group by subject, hadm, stay, and timestamp
        pivoted = filtered_chunk.pivot_table(
            index=['subject_id', 'hadm_id', 'stay_id', 'charttime'],
            columns='itemid',
            values=['valuenum', 'warning'],
            aggfunc='first' # In case of exact same timestamp, take the first value
        )
        
        # Flatten MultiIndex columns
        pivoted.columns = [f"{col[0]}_{col[1]}" for col in pivoted.columns]
        pivoted = pivoted.reset_index()
        
        # Rename columns for clarity
        rename_dict = {
            'valuenum_220179': 'BP_sys_220179',
            'valuenum_220180': 'BP_dia_220180',
            'valuenum_220181': 'BP_mean_220181',
            'warning_220179': 'warning_sys_220179',
            'warning_220180': 'warning_dia_220180',
            'warning_220181': 'warning_mean_220181'
        }
        pivoted.rename(columns=rename_dict, inplace=True)
        
        # Merge with patients demographic data
        # 'how=left' ensures we keep vital signs even if demographic mapping fails for some reason
        merged = pd.merge(pivoted, patients_df, on='subject_id', how='left')
        
        # Reorder columns logically
        cols = ['subject_id', 'hadm_id', 'stay_id', 'charttime', 'age', 'gender']
        bp_cols = [col for col in merged.columns if col.startswith('BP_')]
        warning_cols = [col for col in merged.columns if col.startswith('warning_')]
        cols.extend(bp_cols)
        cols.extend(warning_cols)
        
        # Ensure all columns exist before selecting
        final_cols = [c for c in cols if c in merged.columns]
        merged = merged[final_cols]
        
        has_warning = (merged[warning_cols] == 1).any(axis=1) if warning_cols else pd.Series(False, index=merged.index)
        warning_collected.append(merged[has_warning])
        normal_collected.append(merged[~has_warning])
        
        current_warnings = sum(len(df) for df in warning_collected)
        current_normals = sum(len(df) for df in normal_collected)
        
        if total_chunks % 1 == 0:
            print(f"Processed {total_chunks} chunks. Warnings found: {current_warnings}, Normals found: {current_normals}. Time elapsed: {time.time() - start_time:.2f}s")
            
        if current_warnings >= target_warning_rows and (current_warnings + current_normals) >= max_rows:
            print(f"Found enough rows including warnings. Stopping extraction.")
            break
            
        if total_chunks >= max_chunks:
            print(f"Reached maximum requested chunks ({max_chunks}). Stopping extraction.")
            break
            
    # Combine collected chunks
    all_warnings = pd.concat(warning_collected, ignore_index=True) if warning_collected else pd.DataFrame()
    all_normals = pd.concat(normal_collected, ignore_index=True) if normal_collected else pd.DataFrame()
    
    # We want max_rows total, prioritizing up to target_warning_rows from all_warnings
    take_warn = min(len(all_warnings), target_warning_rows)
    # Take the rest from normal records
    take_norm = max_rows - take_warn
    
    if take_norm > len(all_normals):
        take_norm = len(all_normals)
        take_warn = min(len(all_warnings), max_rows - take_norm)
        
    final_df = pd.concat([
        all_warnings.head(take_warn),
        all_normals.head(take_norm)
    ], ignore_index=True)
    
    # Shuffle rows so warnings are mixed throughout
    final_df = final_df.sample(frac=1, random_state=42).reset_index(drop=True)
    
    # Save the final truncated data
    final_df.to_csv(output_path, index=False)
            
    print(f"Finished processing! Total chunks processed: {total_chunks}. Total time: {time.time() - start_time:.2f}s")
    print(f"Output saved to {output_path} with {len(final_df)} rows ({take_warn} warning rows included).")

if __name__ == "__main__":
    process_mimic_vitals()
