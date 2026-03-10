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

def run_simulator(args, mp_queue):
    print("Simulator process starting...")
    q_client = MultiprocessQueueClient(mp_queue)
    sim = ICUSimulator(speed_factor=args.speed, queue_client=q_client)
    sim.run(max_events=args.events if args.events > 0 else None)
    
    # Send poison pill to stop consumer
    mp_queue.put(None)

def run_consumer(mp_queue):
    print("Consumer process starting...")
    consumer = ICUConsumer(queue_server=mp_queue)
    consumer.run()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run Full ICU Simulation Pipeline')
    parser.add_argument('--speed', type=float, default=3600.0, help='Simulation speed multiplier')
    parser.add_argument('--events', type=int, default=0, help='Max events to process (0 for all)')
    args = parser.parse_args()
    
    # The Queue acts as the boundary
    # For Phase 3, standard Python multiprocessing Queue proves the architecture 
    # cleanly without requiring Redis installation. It's perfectly order-preserving.
    mp_queue = multiprocessing.Queue()
    
    # Start consumer in a separate process
    consumer_process = multiprocessing.Process(target=run_consumer, args=(mp_queue,))
    consumer_process.start()
    
    # Run simulator in main process
    try:
        run_simulator(args, mp_queue)
    except KeyboardInterrupt:
        print("Shutting down pipeline...")
    finally:
        consumer_process.join()
        print("Pipeline shutdown complete.")
