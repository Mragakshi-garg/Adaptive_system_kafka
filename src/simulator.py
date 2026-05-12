import pandas as pd
import time
import json
import argparse
from datetime import datetime

class ICUSimulator:
    def __init__(self, data_path='data/subset_events.csv', speed_factor=60.0, queue_client=None):
        """
        speed_factor: How many times faster than real-time.
                      e.g., 60.0 means 1 hour simulated in 1 minute real-time.
                      1.0 means real-time.
        queue_client: A function or object with a push() or send() method to send events to.
        """
        self.data_path = data_path
        self.speed_factor = speed_factor
        self.queue_client = queue_client
        self.events_df = None
        # used for time syncronization
        self.start_physical_time = None
        self.start_sim_time = None

    def load_data(self):
        print(f"Loading data from {self.data_path}...")
        self.events_df = pd.read_csv(self.data_path)
        self.events_df['charttime'] = pd.to_datetime(self.events_df['charttime'])
        # Converts charttime column to datetime format.
        
        # --- ALIGN TIMELINES ---
        # MIMIC-IV dates are shifted randomly per patient. If we don't align them,
        # patient A might be in 2110 and patient B in 2115, causing the simulator
        # to wait simulation "years" before patient B appears.
        print("Aligning patient timelines to start simultaneously...")
        min_times = self.events_df.groupby('stay_id')['charttime'].transform('min')
        global_min_time = self.events_df['charttime'].min()
        self.events_df['charttime'] = global_min_time + (self.events_df['charttime'] - min_times)
        
        # Sort just in case it wasn't sorted perfectly
        self.events_df.sort_values(by='charttime', inplace=True)
        print(f"Loaded {len(self.events_df)} chronological events.")
        
    def emit_event(self, event):
        payload = {
            'subject_id': int(event['subject_id']),
            'hadm_id': int(event['hadm_id']) if pd.notnull(event['hadm_id']) else None,
            'stay_id': int(event['stay_id']) if pd.notnull(event['stay_id']) else None,
            'charttime': event['charttime'].isoformat(),
            'itemid': int(event['itemid']),
            'valuenum': float(event['valuenum']),
            'send_time': time.time()
        }
        
        if self.queue_client:
            if hasattr(self.queue_client, 'send'): # Kafka Producer
                # Convert the payload to JSON string, then encode to bytes
                self.queue_client.send('vitals-stream', json.dumps(payload).encode('utf-8'))
            elif hasattr(self.queue_client, 'push'): # Simple multiprocess queue
                self.queue_client.push(payload)
        else:
            # For phase 2 testing, just print the event
            print(f"EMIT [{payload['charttime']}] Patient {payload['subject_id']} -> Item {payload['itemid']}: {payload['valuenum']}")

    def run(self, max_events=None):
        if self.events_df is None:
            self.load_data()
            
        if self.events_df.empty:
            print("No events to simulate.")
            return
            
        print(f"Starting simulation at {self.speed_factor}x speed...")
        print("Press Ctrl+C to abort.")
        
        # The first event's time becomes our "epoch" for the simulation
        first_event_time = self.events_df.iloc[0]['charttime']
        self.start_physical_time = time.time()
        self.start_sim_time = first_event_time
        
        events_emitted = 0
        
        try:
            for idx, row in self.events_df.iterrows():
                if max_events is not None and events_emitted >= max_events:
                    break
                    
                event_time = row['charttime']
                
                # Calculate how much simulation time has elapsed since the first event
                sim_elapsed_seconds = (event_time - self.start_sim_time).total_seconds()
                
                # At speed_factor=1, physical_elapsed = sim_elapsed.
                # At speed_factor=10, physical_elapsed = sim_elapsed / 10.
                target_physical_elapsed = sim_elapsed_seconds / self.speed_factor
                
                # Wait until current physical elapsed time matches target physical elapsed time
                while True:
                    current_physical_elapsed = time.time() - self.start_physical_time
                    wait_time = target_physical_elapsed - current_physical_elapsed
                    
                    if wait_time <= 0:
                        break # Time to emit!
                    elif wait_time > 0.1:
                        time.sleep(0.1) # Sleep in small increments to be responsive to KeyboardInterrupt
                    else:
                        time.sleep(wait_time)
                        
                # Emit the event
                self.emit_event(row)
                events_emitted += 1
                
        except KeyboardInterrupt:
            print("\nSimulation aborted by user.")
            
        print(f"Simulation ended. Emitted {events_emitted} events.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run ICU Data Simulator')
    parser.add_argument('--speed', type=float, default=3600.0, help='Simulation speed (e.g. 3600 for 1 hr sim / 1 sec real)')
    parser.add_argument('--events', type=int, default=100, help='Max events to emit for test (0 for all)')
    
    args = parser.parse_args()
    max_ev = args.events if args.events > 0 else None
    
    sim = ICUSimulator(speed_factor=args.speed)
    sim.run(max_events=max_ev)
