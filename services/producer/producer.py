import os
import json
import time
import random
import logging
from datetime import datetime, timedelta
from kafka import KafkaProducer
import psycopg2
from faker import Faker

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
POSTGRES_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'user': os.getenv('POSTGRES_USER', 'evuser'),
    'password': os.getenv('POSTGRES_PASSWORD', 'evpass'),
    'database': os.getenv('POSTGRES_DB', 'evcharging')
}

fake = Faker()

class ChargingEventProducer:
    def __init__(self):
        self.producer = None
        self.stations = []
        self.active_sessions = {}
        
    def connect_kafka(self):
        """Connect to Kafka with retry logic"""
        max_retries = 10
        for i in range(max_retries):
            try:
                self.producer = KafkaProducer(
                    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                    acks='all'
                )
                logger.info("✅ Connected to Kafka")
                return True
            except Exception as e:
                logger.warning(f"Kafka connection attempt {i+1}/{max_retries} failed: {e}")
                time.sleep(5)
        return False
    
    def load_stations(self):
        """Load charging stations from PostgreSQL"""
        try:
            conn = psycopg2.connect(**POSTGRES_CONFIG)
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, power_kw FROM charging_stations")
            self.stations = [
                {'id': str(row[0]), 'name': row[1], 'power_kw': row[2]} 
                for row in cursor.fetchall()
            ]
            cursor.close()
            conn.close()
            logger.info(f"✅ Loaded {len(self.stations)} charging stations")
        except Exception as e:
            logger.error(f"Failed to load stations: {e}")
            time.sleep(5)
            self.load_stations()
    
    def generate_charging_started_event(self):
        """Simulate a charging session starting"""
        station = random.choice(self.stations)
        session_id = fake.uuid4()
        
        event = {
            'event_type': 'charging_started',
            'session_id': session_id,
            'station_id': station['id'],
            'station_name': station['name'],
            'timestamp': datetime.now().isoformat(),
            'power_kw': station['power_kw'],
            'user_id': fake.uuid4()
        }
        
        # Track active session
        self.active_sessions[session_id] = {
            'station': station,
            'start_time': datetime.now(),
            'power_kw': station['power_kw']
        }
        
        return event
    
    def generate_charging_progress_event(self, session_id):
        """Simulate charging progress update"""
        session = self.active_sessions[session_id]
        elapsed_minutes = (datetime.now() - session['start_time']).total_seconds() / 60
        energy_delivered = (session['power_kw'] / 60) * elapsed_minutes
        
        event = {
            'event_type': 'charging_progress',
            'session_id': session_id,
            'station_id': session['station']['id'],
            'timestamp': datetime.now().isoformat(),
            'energy_delivered_kwh': round(energy_delivered, 2),
            'current_power_kw': session['power_kw'] * random.uniform(0.9, 1.0)
        }
        
        return event
    
    def generate_charging_completed_event(self, session_id):
        """Simulate charging session completion"""
        session = self.active_sessions[session_id]
        duration_minutes = (datetime.now() - session['start_time']).total_seconds() / 60
        energy_delivered = (session['power_kw'] / 60) * duration_minutes
        cost = energy_delivered * 0.35  # €0.35 per kWh
        
        event = {
            'event_type': 'charging_completed',
            'session_id': session_id,
            'station_id': session['station']['id'],
            'timestamp': datetime.now().isoformat(),
            'energy_delivered_kwh': round(energy_delivered, 2),
            'duration_minutes': round(duration_minutes, 1),
            'cost_eur': round(cost, 2)
        }
        
        # Remove from active sessions
        del self.active_sessions[session_id]
        
        return event
    
    def send_event(self, event):
        """Send event to Kafka topic"""
        topic = f"charging.events.{event['event_type']}"
        try:
            self.producer.send(topic, value=event)
            self.producer.flush()
            logger.info(f"📤 Sent {event['event_type']} event for session {event['session_id'][:8]}")
        except Exception as e:
            logger.error(f"Failed to send event: {e}")
    
    def run(self):
        """Main producer loop"""
        logger.info("🚀 Starting EV Charging Event Producer...")
        
        # Wait for Kafka
        time.sleep(10)
        
        if not self.connect_kafka():
            logger.error("❌ Could not connect to Kafka. Exiting.")
            return
        
        # Wait for PostgreSQL
        time.sleep(5)
        self.load_stations()
        
        logger.info("🔄 Generating events...")
        
        while True:
            try:
                # Randomly decide what to do
                action = random.choices(
                    ['start', 'progress', 'complete', 'wait'],
                    weights=[0.3, 0.4, 0.2, 0.1]
                )[0]
                
                if action == 'start' and len(self.active_sessions) < 10:
                    event = self.generate_charging_started_event()
                    self.send_event(event)
                
                elif action == 'progress' and self.active_sessions:
                    session_id = random.choice(list(self.active_sessions.keys()))
                    event = self.generate_charging_progress_event(session_id)
                    self.send_event(event)
                
                elif action == 'complete' and self.active_sessions:
                    session_id = random.choice(list(self.active_sessions.keys()))
                    event = self.generate_charging_completed_event(session_id)
                    self.send_event(event)
                
                # Random delay between events (2-8 seconds)
                time.sleep(random.uniform(2, 8))
                
            except KeyboardInterrupt:
                logger.info("🛑 Shutting down producer...")
                break
            except Exception as e:
                logger.error(f"Error in producer loop: {e}")
                time.sleep(5)

if __name__ == "__main__":
    producer = ChargingEventProducer()
    producer.run()
