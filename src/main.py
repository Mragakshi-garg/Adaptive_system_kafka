import multiprocessing
import time
import argparse
from simulator import ICUSimulator
from consumer import ICUConsumer

class MultiprocessQueueClient:
    def __init__(self, mp_queue):
        self.q = mp_queue
    def push(self, event):
        self.q.put(event)

def run_simulator(args, mp_queue=None, kafka_client=None):
    print("Simulator process starting...")
    q_client = kafka_client if kafka_client else MultiprocessQueueClient(mp_queue)
    sim = ICUSimulator(speed_factor=args.speed, queue_client=q_client)
    sim.run(max_events=args.events if args.events > 0 else None)
    
    # Send poison pill to stop consumer
    if mp_queue:
        mp_queue.put(None)
    elif kafka_client:
        kafka_client.send('vitals-stream', json.dumps({'type': 'POISON_PILL'}).encode('utf-8'))

def run_consumer(mp_queue=None, use_kafka=False):
    print("Consumer process starting...")
    if use_kafka:
        import json
        from kafka import KafkaConsumer
        print("Connecting Consumer to Kafka...")
        k_consumer = KafkaConsumer(
            'vitals-stream',
            bootstrap_servers=['localhost:9092'],
            auto_offset_reset='earliest',
            enable_auto_commit=True,
            group_id='icu-group-1'
        )
        consumer = ICUConsumer(kafka_consumer=k_consumer)
    else:
        consumer = ICUConsumer(queue_server=mp_queue)
        
    consumer.run()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run Full ICU Simulation Pipeline')
    parser.add_argument('--speed', type=float, default=3600.0, help='Simulation speed multiplier')
    parser.add_argument('--events', type=int, default=0, help='Max events to process (0 for all)')
    parser.add_argument('--kafka', action='store_true', help='Use Kafka instead of Multiprocessing Queue')
    args = parser.parse_args()
    
    if args.kafka:
        print("--- USING KAFKA BROKER ---")
        import json
        from kafka import KafkaProducer
        
        # We don't need multiprocessing for the producer/consumer since Kafka separates them,
        # but to keep the 1-script ease of use, we'll still spin up the consumer process.
        consumer_process = multiprocessing.Process(target=run_consumer, kwargs={'use_kafka': True})
        consumer_process.start()
        
        # Start producer
        producer = KafkaProducer(bootstrap_servers=['localhost:9092'])
        try:
            run_simulator(args, kafka_client=producer)
            # Flush before exit
            producer.flush()
        except KeyboardInterrupt:
            print("Shutting down pipeline...")
        finally:
            # Note: Kafka consumer might hang if it doesn't get the poison pill fast enough, 
            # so we give it a moment then terminate if needed.
            consumer_process.join(timeout=2)
            if consumer_process.is_alive():
                consumer_process.terminate()
            print("Pipeline shutdown complete.")
            
    else:
        print("--- USING MULTIPROCESSING QUEUE ---")
        mp_queue = multiprocessing.Queue()
        
        # Start consumer in a separate process
        consumer_process = multiprocessing.Process(target=run_consumer, args=(mp_queue,))
        consumer_process.start()
        
        # Run simulator in main process
        try:
            run_simulator(args, mp_queue=mp_queue)
        except KeyboardInterrupt:
            print("Shutting down pipeline...")
        finally:
            consumer_process.join()
            print("Pipeline shutdown complete.")
