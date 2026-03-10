import time
import json
from collections import defaultdict
from datetime import datetime
from model import RiskPredictor

class ICUConsumer:
    def __init__(self, queue_server):
        """
        queue_server: An object providing a .get() method (blocking or non-blocking).
        """
        self.queue_server = queue_server
        
        # State management: dict mapping stay_id -> patient properties
        # properties: { 'last_update': timestamp, 'vital_name': [list of recent values/times], ... }
        self.patient_state = defaultdict(lambda: {
            'subject_id': None,
            'stay_id': None,
            'last_update': None,
            'vitals': {
                'hr': None,
                'spo2': None,
                'sysbp': None,
                'diabp': None,
                'meanbp': None
            }
        })
        
        # Mapping for our Item IDs to human-readable names
        self.item_map = {
            220045: 'hr',
            220277: 'spo2',
            220179: 'sysbp',
            220180: 'diabp',
            220181: 'meanbp'
        }

        # Initialize ML prediction model
        self.predictor = RiskPredictor()

    def process_event(self, event):
        """Update state based on a new event."""
        stay_id = event['stay_id']
        if stay_id is None:
            # Fallback to subject_id if stay_id is missing
            stay_id = event['subject_id']
            
        state = self.patient_state[stay_id]
        
        # Lazy initialization
        if state['subject_id'] is None:
            state['subject_id'] = event['subject_id']
            state['stay_id'] = stay_id
            
        event_time = datetime.fromisoformat(event['charttime'])
        
        # Order validation (simple check: if new event is older than last update, issue a warning)
        if state['last_update'] and event_time < state['last_update']:
             # In a real system, we'd buffer or handle out-of-order. For this phase, just log.
             pass 
             # print(f"WARNING: Out of order event for {stay_id}! {event_time} < {state['last_update']}")
        else:
             state['last_update'] = event_time
             
        # Update vital signs
        item_id = event['itemid']
        val = event['valuenum']
        
        if item_id in self.item_map:
            vital_name = self.item_map[item_id]
            state['vitals'][vital_name] = val
            
        # Emit updated state for prediction / dashboard
        self._on_state_updated(state)
        
    def _on_state_updated(self, state):
        """Hook for sending state to next layer (dashboard/ml model)."""
        # Run prediction on latest state
        current_risk = self.predictor.predict_risk(state)
        state['current_risk'] = current_risk
        
        v = state['vitals']
        
        # Format the timestamp down to seconds for clean logging
        dt_str = state['last_update'].strftime('%Y-%m-%d %H:%M:%S')
        
        print(f"[{dt_str}] Patient {state['subject_id']} | "
              f"HR:{v['hr']} SpO2:{v['spo2']} "
              f"BP:{v['sysbp']}/{v['diabp']} | "
              f"RISK: {current_risk:.2f}")
              
        # Dump state to JSON for Dashboard to read (poor man's Redis)
        self._write_state_to_file()
        
    def _write_state_to_file(self):
        # We write atomic dumps so streamlit can read them safely
        dump_data = {}
        for stay_id, s in self.patient_state.items():
            if s['subject_id'] is not None:
                # Convert datetime to string for JSON serialization
                dump_dict = dict(s)
                if dump_dict['last_update']:
                    dump_dict['last_update'] = dump_dict['last_update'].isoformat()
                dump_data[stay_id] = dump_dict
                
        with open('data/current_state.json', 'w') as f:
            json.dump(dump_data, f)

    def run(self):
        print("Consumer started. Waiting for events...")
        events_processed = 0
        while True:
            # Wait for event
            event = self.queue_server.get()
            
            # Poison pill to stop
            if event is None:
                print(f"Consumer shutting down. Processed {events_processed} events.")
                break
                
            self.process_event(event)
            events_processed += 1
