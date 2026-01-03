import psycopg2
import time
from datetime import datetime, timedelta
from kafka.admin import KafkaAdminClient, ConfigResource, ConfigResourceType
from elasticsearch import Elasticsearch
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SystemMonitor:
    def __init__(self):
        self.kafka_admin = KafkaAdminClient(
            bootstrap_servers='kafka:29092'
        )
        self.es = Elasticsearch(['http://elasticsearch:9200'])
        self.pg_conn = psycopg2.connect(
            host='postgres',
            user='evuser',
            password='evpass',
            database='evcharging'
        )
    
    def get_kafka_metrics(self):
        """Get Kafka throughput and lag"""
        try:
            # Get event count from last minute
            one_min_ago = datetime.now() - timedelta(minutes=1)
            
            result = self.es.count(
                index='charging-events',
                body={
                    'query': {
                        'range': {
                            'timestamp': {
                                'gte': one_min_ago.isoformat()
                            }
                        }
                    }
                }
            )
            
            events_per_minute = result['count']
            events_per_second = events_per_minute / 60
            
            return {
                'events_per_second': round(events_per_second, 2),
                'events_last_minute': events_per_minute
            }
        except Exception as e:
            logger.error(f"Kafka metrics error: {e}")
            return {'events_per_second': 0, 'events_last_minute': 0}
    
    def get_database_metrics(self):
        """Get PostgreSQL performance"""
        cursor = self.pg_conn.cursor()
        
        # Query performance test
        start = time.time()
        cursor.execute("SELECT COUNT(*) FROM charging_sessions")
        total_sessions = cursor.fetchone()[0]
        query_time_ms = (time.time() - start) * 1000
        
        # Active sessions
        cursor.execute("SELECT COUNT(*) FROM charging_sessions WHERE status = 'in_progress'")
        active_sessions = cursor.fetchone()[0]
        
        # Database size
        cursor.execute("""
            SELECT pg_size_pretty(pg_database_size('evcharging'))
        """)
        db_size = cursor.fetchone()[0]
        
        cursor.close()
        
        return {
            'total_sessions': total_sessions,
            'active_sessions': active_sessions,
            'query_time_ms': round(query_time_ms, 2),
            'db_size': db_size
        }
    
    def get_system_metrics(self):
        """Get overall system health"""
        cursor = self.pg_conn.cursor()
        
        # Total stations
        cursor.execute("SELECT COUNT(*) FROM charging_stations")
        total_stations = cursor.fetchone()[0]
        
        # Events today
        cursor.execute("""
            SELECT COUNT(*) FROM charging_events 
            WHERE timestamp > NOW() - INTERVAL '24 hours'
        """)
        events_today = cursor.fetchone()[0]
        
        # Revenue today
        cursor.execute("""
            SELECT COALESCE(SUM(cost_eur), 0) FROM charging_sessions
            WHERE DATE(start_time) = CURRENT_DATE
        """)
        revenue_today = cursor.fetchone()[0]
        
        cursor.close()
        
        return {
            'total_stations': total_stations,
            'events_last_24h': events_today,
            'revenue_today_eur': float(revenue_today)
        }
    
    def print_dashboard(self):
        """Print real-time metrics dashboard"""
        kafka_metrics = self.get_kafka_metrics()
        db_metrics = self.get_database_metrics()
        system_metrics = self.get_system_metrics()
        
        # Clear screen (works in most terminals)
        print('\033[2J\033[H')
        
        print("=" * 80)
        print("⚡ EV CHARGING MONITOR - SYSTEM DASHBOARD")
        print("=" * 80)
        print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        print("🔥 KAFKA THROUGHPUT")
        print(f"   Events/second:     {kafka_metrics['events_per_second']}")
        print(f"   Events/minute:     {kafka_metrics['events_last_minute']}")
        print()
        
        print("💾 DATABASE PERFORMANCE")
        print(f"   Query time:        {db_metrics['query_time_ms']} ms")
        print(f"   Total sessions:    {db_metrics['total_sessions']:,}")
        print(f"   Active sessions:   {db_metrics['active_sessions']:,}")
        print(f"   Database size:     {db_metrics['db_size']}")
        print()
        
        print("📊 SYSTEM METRICS")
        print(f"   Total stations:    {system_metrics['total_stations']:,}")
        print(f"   Events (24h):      {system_metrics['events_last_24h']:,}")
        print(f"   Revenue today:     €{system_metrics['revenue_today_eur']:.2f}")
        print()
        
        print("=" * 80)
        
        # Health indicators
        health_status = "🟢 HEALTHY"
        
        if kafka_metrics['events_per_second'] < 5:
            health_status = "🟡 LOW THROUGHPUT"
        if db_metrics['query_time_ms'] > 100:
            health_status = "🟡 SLOW DB QUERIES"
        if kafka_metrics['events_per_second'] == 0:
            health_status = "🔴 NO EVENTS"
        
        print(f"System Status: {health_status}")
        print("=" * 80)
    
    def run(self):
        """Run monitoring loop"""
        logger.info("🚀 Starting System Monitor...")
        
        while True:
            try:
                self.print_dashboard()
                time.sleep(5)  # Update every 5 seconds
            except KeyboardInterrupt:
                logger.info("🛑 Shutting down monitor...")
                break
            except Exception as e:
                logger.error(f"Monitor error: {e}")
                time.sleep(10)

if __name__ == "__main__":
    monitor = SystemMonitor()
    monitor.run()