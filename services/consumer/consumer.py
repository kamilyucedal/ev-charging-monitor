import os
import json
import logging
from datetime import datetime
from kafka import KafkaConsumer
import psycopg2
from elasticsearch import Elasticsearch
import signal
import sys
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler

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
ELASTICSEARCH_HOST = os.getenv('ELASTICSEARCH_HOST', 'localhost')

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"status": "healthy"}')
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        pass  # Suppress logs

def start_health_server():
    server = HTTPServer(('0.0.0.0', 8080), HealthCheckHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    logger.info("✅ Health check endpoint started on :8080/health")

class ChargingEventConsumer:
    def __init__(self):
        self.consumer = None
        self.pg_conn = None
        self.es_client = None
        self.running = True  # Yeni
        
    def shutdown(self, signum, frame):
        """Graceful shutdown handler"""
        logger.info("🛑 Shutdown signal received, cleaning up...")
        self.running = False
        if self.consumer:
            self.consumer.close()
        if self.pg_conn:
            self.pg_conn.close()
        sys.exit(0)

    def connect_services(self):
        """Connect to Kafka, PostgreSQL, and Elasticsearch"""
        # Kafka
        topics = ['charging.events.charging_started', 
                 'charging.events.charging_progress',
                 'charging.events.charging_completed']
        
        self.consumer = KafkaConsumer(
            *topics,
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='earliest',
            group_id='ev-consumer-group'
        )
        logger.info("✅ Connected to Kafka")
        
        # PostgreSQL
        self.pg_conn = psycopg2.connect(**POSTGRES_CONFIG)
        logger.info("✅ Connected to PostgreSQL")
        
        # Elasticsearch
        self.es_client = Elasticsearch([f'http://{ELASTICSEARCH_HOST}:9200'])
        
        # Create index if not exists
        if not self.es_client.indices.exists(index='charging-events'):
            self.es_client.indices.create(
                index='charging-events',
                body={
                    'mappings': {
                        'properties': {
                            'event_type': {'type': 'keyword'},
                            'session_id': {'type': 'keyword'},
                            'station_id': {'type': 'keyword'},
                            'station_name': {'type': 'text'},
                            'timestamp': {'type': 'date'},
                            'energy_delivered_kwh': {'type': 'float'},
                            'cost_eur': {'type': 'float'},
                            'duration_minutes': {'type': 'float'}
                        }
                    }
                }
            )
        logger.info("✅ Connected to Elasticsearch")
    
    def process_charging_started(self, event):
        """Handle charging_started event"""
        cursor = self.pg_conn.cursor()
        
        # Insert new session
        cursor.execute("""
            INSERT INTO charging_sessions (id, station_id, start_time, status)
            VALUES (%s, %s, %s, %s)
        """, (
            event['session_id'],
            event['station_id'],
            event['timestamp'],
            'in_progress'
        ))
        
        # Log event
        cursor.execute("""
            INSERT INTO charging_events (session_id, event_type, event_data)
            VALUES (%s, %s, %s)
        """, (
            event['session_id'],
            event['event_type'],
            json.dumps(event)
        ))
        
        self.pg_conn.commit()
        cursor.close()
        
        # Index to Elasticsearch
        self.es_client.index(index='charging-events', document=event)
        
        logger.info(f"✅ Processed charging_started: {event['session_id'][:8]}")
    
    def process_charging_progress(self, event):
        """Handle charging_progress event"""
        # Just log to Elasticsearch for monitoring
        self.es_client.index(index='charging-events', document=event)
        
        logger.info(f"📊 Progress update: {event['session_id'][:8]} - {event['energy_delivered_kwh']} kWh")
    
    def process_charging_completed(self, event):
        """Handle charging_completed event"""
        cursor = self.pg_conn.cursor()
        
        # Update session
        cursor.execute("""
            UPDATE charging_sessions
            SET end_time = %s,
                energy_delivered_kwh = %s,
                cost_eur = %s,
                status = 'completed'
            WHERE id = %s
        """, (
            event['timestamp'],
            event['energy_delivered_kwh'],
            event['cost_eur'],
            event['session_id']
        ))
        
        # Log event
        cursor.execute("""
            INSERT INTO charging_events (session_id, event_type, event_data)
            VALUES (%s, %s, %s)
        """, (
            event['session_id'],
            event['event_type'],
            json.dumps(event)
        ))
        
        self.pg_conn.commit()
        cursor.close()
        
        # Index to Elasticsearch
        self.es_client.index(index='charging-events', document=event)
        
        logger.info(f"✅ Completed session: {event['session_id'][:8]} - {event['energy_delivered_kwh']} kWh, €{event['cost_eur']}")

    def validate_event(self, event):
        """Validate event structure"""
        required_fields = ['event_type', 'session_id', 'station_id', 'timestamp']
    
        for field in required_fields:
            if field not in event:
                raise ValueError(f"Missing required field: {field}")
    
        return True

    def run(self):
        """Main consumer loop"""
        logger.info("🚀 Starting EV Charging Event Consumer...")
        
        start_health_server() 

        # Register signal handlers
        signal.signal(signal.SIGINT, self.shutdown)
        signal.signal(signal.SIGTERM, self.shutdown)

        import time
        time.sleep(15)  # Wait for all services to be ready
        
        self.connect_services()
        
        logger.info("🔄 Consuming events...")
        
        for message in self.consumer:
            if not self.running:  # Check shutdown flag
                break

            try:
                event = message.value
                if not self.validate_event(event):
                    logger.warning(f"Invalid event skipped: {event}")
                    continue

                event_type = event['event_type']

 
                if event_type == 'charging_started':
                    self.process_charging_started(event)
                elif event_type == 'charging_progress':
                    self.process_charging_progress(event)
                elif event_type == 'charging_completed':
                    self.process_charging_completed(event)
                
            except Exception as e:
                logger.error(f"Error processing event: {e}")
                continue

        logger.info("✅ Consumer shutdown complete")

if __name__ == "__main__":
    consumer = ChargingEventConsumer()
    consumer.run()
