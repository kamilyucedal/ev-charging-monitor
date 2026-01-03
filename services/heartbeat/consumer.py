import os
import json
import logging
from kafka import KafkaConsumer
import psycopg2
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HeartbeatConsumer:
    def __init__(self):
        self.consumer = None
        self.pg_conn = None
        self.offline_alerts = set()  # Track which stations we've alerted about
    
    def connect_services(self):
        """Connect to Kafka and PostgreSQL"""
        # Kafka
        self.consumer = KafkaConsumer(
            'station.heartbeat',
            bootstrap_servers=os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:29092'),
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='earliest',
            group_id='heartbeat-consumer-group'
        )
        logger.info("✅ Connected to Kafka")
        
        # PostgreSQL
        self.pg_conn = psycopg2.connect(
            host=os.getenv('POSTGRES_HOST', 'postgres'),
            user='evuser',
            password='evpass',
            database='evcharging'
        )
        logger.info("✅ Connected to PostgreSQL")
    
    def process_heartbeat(self, heartbeat):
        """Store heartbeat and check for alerts"""
        cursor = self.pg_conn.cursor()
        
        try:
            # Insert heartbeat
            cursor.execute("""
                INSERT INTO station_heartbeats 
                (station_id, timestamp, status, voltage_v, temperature_c, signal_strength, uptime_hours)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                heartbeat['station_id'],
                heartbeat['timestamp'],
                heartbeat['status'],
                heartbeat['voltage_v'],
                heartbeat['temperature_c'],
                heartbeat['signal_strength'],
                heartbeat.get('uptime_hours', 0)
            ))
            
            self.pg_conn.commit()
            
            # Alert logic
            station_id = heartbeat['station_id']
            status = heartbeat['status']
            
            if status == 'offline':
                if station_id not in self.offline_alerts:
                    logger.error(
                        f"🔴 ALERT: Station {station_id[:8]} is OFFLINE! "
                        f"Voltage: {heartbeat['voltage_v']}V, Temp: {heartbeat['temperature_c']}°C"
                    )
                    self.offline_alerts.add(station_id)
                    # Here you could send email/webhook alert
            elif status == 'degraded':
                logger.warning(
                    f"🟡 WARNING: Station {station_id[:8]} is DEGRADED "
                    f"(Signal: {heartbeat['signal_strength']}%, Voltage: {heartbeat['voltage_v']}V)"
                )
            else:  # online
                # Remove from offline alerts if recovered
                if station_id in self.offline_alerts:
                    logger.info(f"🟢 RECOVERED: Station {station_id[:8]} is back online")
                    self.offline_alerts.discard(station_id)
            
        except Exception as e:
            logger.error(f"Error processing heartbeat: {e}")
            self.pg_conn.rollback()
        finally:
            cursor.close()
    
    def run(self):
        """Consume heartbeat events"""
        logger.info("🚀 Starting Heartbeat Consumer...")
        
        # Wait for services
        import time
        time.sleep(20)
        
        self.connect_services()
        
        logger.info("💓 Consuming heartbeat events...")
        
        heartbeat_count = 0
        for message in self.consumer:
            try:
                heartbeat = message.value
                self.process_heartbeat(heartbeat)
                
                heartbeat_count += 1
                if heartbeat_count % 100 == 0:
                    logger.info(f"📊 Processed {heartbeat_count} heartbeats so far...")
                
            except Exception as e:
                logger.error(f"Error in consumer loop: {e}")
                continue

if __name__ == "__main__":
    consumer = HeartbeatConsumer()
    consumer.run()
