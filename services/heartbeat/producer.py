import os
import json
import time
import random
import logging
from datetime import datetime
from kafka import KafkaProducer
import psycopg2

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HeartbeatProducer:
    def __init__(self):
        self.producer = None
        self.stations = []
        self.heartbeat_interval = int(os.getenv('HEARTBEAT_INTERVAL', 60))  # seconds
    
    def connect_kafka(self):
        """Connect to Kafka"""
        max_retries = 10
        for i in range(max_retries):
            try:
                self.producer = KafkaProducer(
                    bootstrap_servers=os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:29092'),
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
        """Load all stations from database"""
        try:
            conn = psycopg2.connect(
                host=os.getenv('POSTGRES_HOST', 'postgres'),
                user='evuser',
                password='evpass',
                database='evcharging'
            )
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM charging_stations")
            self.stations = [str(row[0]) for row in cursor.fetchall()]
            cursor.close()
            conn.close()
            logger.info(f"✅ Loaded {len(self.stations)} stations for heartbeat monitoring")
        except Exception as e:
            logger.error(f"Failed to load stations: {e}")
            time.sleep(5)
            self.load_stations()
    
    def generate_heartbeat(self, station_id):
        """Generate realistic heartbeat event"""
        
        # 98% online, 1.5% degraded, 0.5% offline
        status_weights = [0.98, 0.015, 0.005]
        status = random.choices(['online', 'degraded', 'offline'], weights=status_weights)[0]
        
        # Realistic voltage ranges
        if status == 'online':
            voltage = round(random.uniform(230, 240), 2)
            signal = random.randint(80, 100)
            temp = round(random.uniform(20, 30), 1)
        elif status == 'degraded':
            voltage = round(random.uniform(210, 230), 2)
            signal = random.randint(40, 80)
            temp = round(random.uniform(30, 40), 1)
        else:  # offline
            voltage = round(random.uniform(0, 200), 2)
            signal = random.randint(0, 40)
            temp = round(random.uniform(40, 60), 1)
        
        return {
            'event_type': 'station_heartbeat',
            'station_id': station_id,
            'timestamp': datetime.now().isoformat(),
            'status': status,
            'voltage_v': voltage,
            'temperature_c': temp,
            'signal_strength': signal,
            'uptime_hours': random.randint(0, 8760)  # 0-365 days
        }
    
    def send_heartbeat_batch(self):
        """Send heartbeat for all stations"""
        start_time = time.time()
        sent_count = 0
        
        for station_id in self.stations:
            try:
                heartbeat = self.generate_heartbeat(station_id)
                self.producer.send('station.heartbeat', value=heartbeat)
                sent_count += 1
                
                # Log degraded/offline stations
                if heartbeat['status'] != 'online':
                    logger.warning(
                        f"⚠️  Station {station_id[:8]} is {heartbeat['status']} "
                        f"(voltage: {heartbeat['voltage_v']}V, temp: {heartbeat['temperature_c']}°C)"
                    )
            except Exception as e:
                logger.error(f"Failed to send heartbeat for {station_id[:8]}: {e}")
        
        self.producer.flush()
        
        elapsed = time.time() - start_time
        logger.info(f"💓 Sent {sent_count}/{len(self.stations)} heartbeats in {elapsed:.2f}s")
        
        return elapsed
    
    def run(self):
        """Run heartbeat producer loop"""
        logger.info("🚀 Starting Heartbeat Producer...")
        logger.info(f"💓 Heartbeat interval: {self.heartbeat_interval} seconds")
        
        # Wait for services
        time.sleep(15)
        
        if not self.connect_kafka():
            logger.error("❌ Could not connect to Kafka. Exiting.")
            return
        
        self.load_stations()
        
        logger.info(f"💓 Starting heartbeat loop for {len(self.stations)} stations...")
        
        while True:
            try:
                elapsed = self.send_heartbeat_batch()
                
                # Wait for next interval
                sleep_time = max(0, self.heartbeat_interval - elapsed)
                if sleep_time > 0:
                    time.sleep(sleep_time)
                else:
                    logger.warning(f"⚠️  Heartbeat took longer than interval! ({elapsed:.2f}s > {self.heartbeat_interval}s)")
                
            except KeyboardInterrupt:
                logger.info("🛑 Shutting down heartbeat producer...")
                break
            except Exception as e:
                logger.error(f"Heartbeat loop error: {e}")
                time.sleep(10)

if __name__ == "__main__":
    producer = HeartbeatProducer()
    producer.run()
