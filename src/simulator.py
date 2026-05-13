import os, time, json, random, datetime
import redis

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from model import RiskPredictor

NUM_PATIENTS = 50
REDIS_CHANNEL = 'icu_vitals'

class Patient:
    def __init__(self, pid):
        self.id = f"Patient #{pid:03d}"
        self.state = 'stable'
        self.steps_in_state = 0
        self.hr   = random.uniform(65, 85)
        self.spo2 = random.uniform(95, 99)
        self.sys  = random.uniform(110, 130)
        self.dia  = random.uniform(65, 80)

    def update(self):
        self.steps_in_state += 1

        # Every 30 steps, maybe change state
        if self.steps_in_state > 30:
            self.steps_in_state = 0
            if self.state == 'stable':
                self.state = random.choices(
                    ['stable', 'deteriorating'],
                    weights=[0.85, 0.15])[0]
            elif self.state == 'deteriorating':
                self.state = random.choices(
                    ['deteriorating', 'critical', 'stable'],
                    weights=[0.5, 0.3, 0.2])[0]
            elif self.state == 'critical':
                self.state = random.choices(
                    ['critical', 'recovering'],
                    weights=[0.7, 0.3])[0]
            elif self.state == 'recovering':
                self.state = random.choices(
                    ['recovering', 'stable'],
                    weights=[0.6, 0.4])[0]

        # Smooth vital drift based on state
        if self.state == 'stable':
            self.hr   += random.uniform(-1, 1)
            self.spo2 += random.uniform(-0.2, 0.2)
            self.sys  += random.uniform(-1, 1)
            self.dia  += random.uniform(-0.5, 0.5)

        elif self.state == 'deteriorating':
            self.hr   += random.uniform(0.5, 2.0)
            self.spo2 -= random.uniform(0.1, 0.5)
            self.sys  -= random.uniform(0.5, 1.5)
            self.dia  -= random.uniform(0.3, 1.0)

        elif self.state == 'critical':
            self.hr   = min(160, self.hr + random.uniform(0, 1))
            self.spo2 = max(70,  self.spo2 - random.uniform(0, 0.3))
            self.sys  = max(70,  self.sys  - random.uniform(0, 1))
            self.dia  = max(40,  self.dia  - random.uniform(0, 0.5))

        elif self.state == 'recovering':
            self.hr   += (75  - self.hr)   * 0.05
            self.spo2 += (97  - self.spo2) * 0.05
            self.sys  += (120 - self.sys)  * 0.05
            self.dia  += (75  - self.dia)  * 0.05

        # Hard clamp — never go outside physically possible values
        self.hr   = max(30,  min(180, self.hr))
        self.spo2 = max(70,  min(100, self.spo2))
        self.sys  = max(60,  min(200, self.sys))
        self.dia  = max(30,  min(130, self.dia))

    def to_record(self):
        map_bp = (self.sys + 2 * self.dia) / 3.0
        warning = 1 if (
            self.hr > 100 or self.hr < 50 or
            self.spo2 < 90 or
            self.sys < 90 or self.sys > 160 or
            self.dia < 60 or self.dia > 100
        ) else 0
        return {
            "subject_id":   self.id,
            "timestamp":    datetime.datetime.now().isoformat(),
            "heart_rate":   round(self.hr,   1),
            "spo2":         round(self.spo2, 1),
            "systolic_bp":  round(self.sys,  1),
            "diastolic_bp": round(self.dia,  1),
            "mean_bp":      round(map_bp,    1),
            "state":        self.state,
            "warning":      warning
        }


def run():
    redis_host = os.getenv('REDIS_HOST', 'localhost')
    redis_port = int(os.getenv('REDIS_PORT', 6379))
    r = redis.Redis(host=redis_host, port=redis_port,
                    decode_responses=True)

    patients = [Patient(i + 1) for i in range(NUM_PATIENTS)]
    print(f"Streaming {NUM_PATIENTS} patients → Redis "
          f"[{redis_host}:{redis_port}] channel '{REDIS_CHANNEL}'")

    predictor = RiskPredictor(
        model_path=os.path.join(os.path.dirname(__file__), '../data/icu_risk_model.pkl')
    )

    while True:
        for p in patients:
            p.update()
            record = p.to_record()
            record['risk_score'] = predictor.predict_risk(
                heart_rate=record['heart_rate'],
                spo2=record['spo2'],
                systolic_bp=record['systolic_bp'],
                mean_bp=record['mean_bp']
            )
            r.publish(REDIS_CHANNEL, json.dumps(record))
            print(f"  {record['subject_id']} | "
              f"HR={record['heart_rate']} "
              f"SpO2={record['spo2']} "
              f"Risk={record['risk_score']} "
              f"State={record['state']}")
        time.sleep(1.0)


if __name__ == "__main__":
    run()