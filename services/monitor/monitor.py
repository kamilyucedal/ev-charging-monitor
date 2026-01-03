import psycopg2
import time
from kafka import KafkaConsumer
from elasticsearch import Elasticsearch

class PerformanceMonitor:
    def __init__(self):
        self.metrics = {
            'events_processed': 0,
            'events_per_second': 0,
            'kafka_lag': 0,
            'db_query_time_ms': 0
        }
    
    def monitor_kafka_lag(self):
        """Check Kafka consumer lag"""
        # Implementation
        pass
    
    def monitor_db_performance(self):
        """Check PostgreSQL query performance"""
        conn = psycopg2.connect(...)
        cursor = conn.cursor()
        
        start = time.time()
        cursor.execute("SELECT COUNT(*) FROM charging_sessions")
        duration = (time.time() - start) * 1000
        
        self.metrics['db_query_time_ms'] = duration
        logger.info(f"📊 DB query time: {duration:.2f}ms")
    
    def run(self):
        while True:
            self.monitor_kafka_lag()
            self.monitor_db_performance()
            
            # Log metrics to Elasticsearch
            # ...
            
            time.sleep(30)
