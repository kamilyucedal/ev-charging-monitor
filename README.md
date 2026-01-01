# EV Charging Station Monitor

A real-time data pipeline for monitoring electric vehicle charging stations. Built to explore data engineering patterns for sustainable technology applications.

![Architecture](docs/architecture.png)
*Architecture diagram coming soon*

## 🎯 Motivation

As electric vehicles become mainstream, charging infrastructure requires robust data systems for:
- **Real-time monitoring** of charging station availability and performance
- **Predictive maintenance** to minimize downtime
- **Usage analytics** for capacity planning and optimization
- **Operational insights** for charging network operators

This project explores these challenges using modern data engineering tools and practices.

## 🏗️ Architecture

The system implements an event-driven architecture for processing charging station data:

1. **Event Generation**: Simulated charging events (start, progress, complete)
2. **Event Streaming**: Kafka topics for different event types
3. **Data Processing**: Consumer service processes events and stores data
4. **Data Storage**: 
   - PostgreSQL for transactional data (sessions, stations)
   - Elasticsearch for event logs and search
5. **Visualization**: Kibana dashboards for real-time monitoring

### Event Flow
```
[Charging Stations] 
    ↓ (events: start, progress, complete)
[Kafka Topics]
    ↓ (streaming)
[Consumer Service]
    ├─→ [PostgreSQL] (structured data: sessions, stations)
    └─→ [Elasticsearch] (event logs, search, analytics)
         ↓
    [Kibana] (dashboards, visualization)
```

## 🛠️ Tech Stack

- **PostgreSQL 15**: Relational database for charging sessions and station data
- **Apache Kafka**: Event streaming platform for real-time data pipelines
- **Elasticsearch 8.11**: Search and analytics engine for event data
- **Kibana 8.11**: Data visualization and dashboarding
- **Python 3.11**: Service implementation
- **Docker & Docker Compose**: Containerization and orchestration

### Key Python Libraries
- `kafka-python`: Kafka client
- `psycopg2`: PostgreSQL adapter
- `elasticsearch`: Elasticsearch client
- `faker`: Test data generation

## 🚀 Getting Started

### Prerequisites

- Docker Desktop (or Docker Engine + Docker Compose)
- Git
- 8GB RAM minimum (for running all services)

### Installation

1. **Clone the repository**
```bash
   git clone https://github.com/YOUR_USERNAME/ev-charging-monitor.git
   cd ev-charging-monitor
```

2. **Start all services**
```bash
   docker-compose up -d
```

3. **Check service health**
```bash
   docker-compose ps
```

   All services should show as "healthy" or "running" after 30-60 seconds.

4. **View logs**
```bash
   # All services
   docker-compose logs -f

   # Specific service
   docker-compose logs -f producer
   docker-compose logs -f consumer
```

### Accessing Services

- **Kibana Dashboard**: http://localhost:5601
- **Elasticsearch**: http://localhost:9200
- **PostgreSQL**: `localhost:5432` (user: `evuser`, password: `evpass`, db: `evcharging`)

## 📊 Exploring the Data

### PostgreSQL Queries

Connect to PostgreSQL:
```bash
docker exec -it ev-postgres psql -U evuser -d evcharging
```

Example queries:
```sql
-- View all charging stations
SELECT * FROM charging_stations;

-- View recent charging sessions
SELECT * FROM charging_sessions ORDER BY start_time DESC LIMIT 10;

-- Calculate total energy delivered today
SELECT 
    DATE(start_time) as date,
    COUNT(*) as sessions,
    SUM(energy_delivered_kwh) as total_energy_kwh,
    SUM(cost_eur) as total_revenue_eur
FROM charging_sessions
WHERE DATE(start_time) = CURRENT_DATE
GROUP BY DATE(start_time);

-- Station utilization
SELECT 
    s.name,
    COUNT(cs.id) as total_sessions,
    AVG(cs.energy_delivered_kwh) as avg_energy_kwh
FROM charging_stations s
LEFT JOIN charging_sessions cs ON s.id = cs.station_id
GROUP BY s.name;
```

### Elasticsearch Queries
```bash
# Check index health
curl http://localhost:9200/charging-events/_search?pretty

# Count events by type
curl -X GET "localhost:9200/charging-events/_search?pretty" -H 'Content-Type: application/json' -d'
{
  "size": 0,
  "aggs": {
    "event_types": {
      "terms": { "field": "event_type" }
    }
  }
}
'
```

### Kibana Dashboard

1. Open Kibana: http://localhost:5601
2. Go to **Management** → **Stack Management** → **Index Patterns**
3. Create index pattern: `charging-events*`
4. Set time field: `timestamp`
5. Go to **Analytics** → **Discover** to explore data
6. Go to **Analytics** → **Dashboard** to create visualizations

*(Dashboard templates coming soon)*

## 🧪 Development

### Project Structure
```
ev-charging-monitor/
├── services/
│   ├── producer/       # Event generation service
│   ├── consumer/       # Event processing service
│   └── api/            # (Future) REST API
├── sql/                # Database schemas
├── kibana/             # Dashboard configurations
├── data/               # Sample data
└── docs/               # Documentation
```

### Stopping Services
```bash
# Stop all services
docker-compose down

# Stop and remove volumes (clean slate)
docker-compose down -v
```

### Rebuilding After Code Changes
```bash
# Rebuild specific service
docker-compose up -d --build producer

# Rebuild all services
docker-compose up -d --build
```

## 🎓 Learning Outcomes

This project demonstrates:

- **Event-driven architecture** for real-time data processing
- **Stream processing** with Apache Kafka
- **Polyglot persistence** (PostgreSQL + Elasticsearch)
- **Containerization** with Docker
- **Data modeling** for time-series and transactional data
- **Observability** through logging and monitoring

## 🔮 Future Enhancements

Potential extensions to explore:

- [ ] **Machine Learning**: Predict charging demand, optimize pricing
- [ ] **REST API**: Query interface for external applications
- [ ] **Authentication**: Secure access to services
- [ ] **Monitoring**: Add Prometheus + Grafana for system metrics
- [ ] **Load Testing**: Simulate high-throughput scenarios
- [ ] **Data Quality**: Add validation and error handling
- [ ] **Real Data Integration**: Connect to actual EV charging APIs
- [ ] **Multi-region**: Simulate distributed charging networks

## 📝 License

MIT License - feel free to use this project for learning and experimentation.

## 🤝 Contributing

This is a personal learning project, but suggestions and feedback are welcome! Feel free to:
- Open issues for bugs or questions
- Suggest improvements
- Share your own implementations

## 📧 Contact

Kamil Yucedal - [My LinkedIn](https://linkedin.com/in/kamil-yucedal-dba)

Project built as part of exploring data engineering opportunities in cleantech.

---

*Built with ⚡ for a sustainable future*
