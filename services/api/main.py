from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
import os
from datetime import datetime
from typing import List, Dict

app = FastAPI(title="EV Charging Monitor API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database connection
POSTGRES_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'user': os.getenv('POSTGRES_USER', 'evuser'),
    'password': os.getenv('POSTGRES_PASSWORD', 'evpass'),
    'database': os.getenv('POSTGRES_DB', 'evcharging')
}

def get_db_connection():
    return psycopg2.connect(**POSTGRES_CONFIG)

@app.get("/")
def root():
    return {"message": "EV Charging Monitor API", "version": "1.0.0"}

# ========================================
# HEALTH ENDPOINTS (SPESIFIK ROUTES ÖNCE!)
# ========================================

@app.get("/api/stations/health")
def get_station_health():
    """Get health status summary"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT COUNT(*) FROM station_heartbeats 
            WHERE timestamp > NOW() - INTERVAL '10 minutes'
        """)
        recent_count = cursor.fetchone()[0]
        
        if recent_count == 0:
            return {
                'status': 'no_data',
                'message': 'Waiting for heartbeat data...',
                'health_counts': {'online': 0, 'degraded': 0, 'offline': 0},
                'offline_stations': []
            }
        
        # Latest status for each station
        cursor.execute("""
            SELECT 
                status,
                COUNT(DISTINCT station_id) as count
            FROM (
                SELECT DISTINCT ON (station_id)
                    station_id,
                    status
                FROM station_heartbeats
                ORDER BY station_id, timestamp DESC
            ) latest
            GROUP BY status
        """)
        
        health_counts = {'online': 0, 'degraded': 0, 'offline': 0}
        for row in cursor.fetchall():
            health_counts[row[0]] = row[1]
        
        # Offline station details
        cursor.execute("""
            SELECT 
                s.id,
                s.name,
                s.city,
                latest.timestamp,
                latest.voltage_v,
                latest.temperature_c
            FROM (
                SELECT DISTINCT ON (station_id)
                    station_id,
                    timestamp,
                    voltage_v,
                    temperature_c,
                    status
                FROM station_heartbeats
                ORDER BY station_id, timestamp DESC
            ) latest
            JOIN charging_stations s ON latest.station_id = s.id
            WHERE latest.status = 'offline'
            ORDER BY latest.timestamp DESC
            LIMIT 10
        """)
        
        offline_stations = [{
            'id': str(row[0]),
            'name': row[1],
            'city': row[2],
            'last_seen': row[3].isoformat() if row[3] else None,
            'voltage_v': float(row[4]) if row[4] else 0,
            'temperature_c': float(row[5]) if row[5] else 0
        } for row in cursor.fetchall()]
        
        return {
            'status': 'ok',
            'health_counts': health_counts,
            'offline_stations': offline_stations
        }
        
    except Exception as e:
        import traceback
        print(f"Error in /health endpoint: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()

# ========================================
# GENERAL STATION ENDPOINTS
# ========================================

@app.get("/api/stations")
def get_stations():
    """Get all charging stations with current status"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = """
        SELECT 
            s.id,
            s.name,
            s.location_lat,
            s.location_lng,
            s.city,
            s.power_kw,
            s.connector_type,
            s.status,
            COUNT(cs.id) FILTER (WHERE cs.status = 'in_progress') as active_sessions
        FROM charging_stations s
        LEFT JOIN charging_sessions cs ON s.id = cs.station_id
        GROUP BY s.id
    """
    
    cursor.execute(query)
    stations = []
    
    for row in cursor.fetchall():
        stations.append({
            'id': str(row[0]),
            'name': row[1],
            'lat': float(row[2]),
            'lng': float(row[3]),
            'city': row[4],
            'power_kw': row[5],
            'connector_type': row[6],
            'status': 'charging' if row[8] > 0 else 'available',
            'active_sessions': row[8]
        })
    
    cursor.close()
    conn.close()
    
    return {"stations": stations}

@app.get("/api/stations/{station_id}")
def get_station_detail(station_id: str):
    """Get detailed info for a specific station"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Station info
    cursor.execute("""
        SELECT id, name, location_lat, location_lng, city, 
               power_kw, connector_type, status
        FROM charging_stations 
        WHERE id = %s
    """, (station_id,))
    
    station_row = cursor.fetchone()
    if not station_row:
        raise HTTPException(status_code=404, detail="Station not found")
    
    # Active sessions
    cursor.execute("""
        SELECT id, start_time, energy_delivered_kwh
        FROM charging_sessions
        WHERE station_id = %s AND status = 'in_progress'
        ORDER BY start_time DESC
    """, (station_id,))
    
    active_sessions = []
    for row in cursor.fetchall():
        active_sessions.append({
            'id': str(row[0]),
            'start_time': row[1].isoformat(),
            'energy_kwh': float(row[2]) if row[2] else 0
        })
    
    # Recent completed sessions
    cursor.execute("""
        SELECT COUNT(*), SUM(energy_delivered_kwh)
        FROM charging_sessions
        WHERE station_id = %s 
          AND status = 'completed'
          AND start_time > NOW() - INTERVAL '24 hours'
    """, (station_id,))
    
    stats = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    return {
        'id': str(station_row[0]),
        'name': station_row[1],
        'lat': float(station_row[2]),
        'lng': float(station_row[3]),
        'city': station_row[4],
        'power_kw': station_row[5],
        'connector_type': station_row[6],
        'status': station_row[7],
        'active_sessions': active_sessions,
        'stats_24h': {
            'total_sessions': stats[0],
            'total_energy_kwh': float(stats[1]) if stats[1] else 0
        }
    }

@app.get("/api/stats")
def get_stats():
    """Get overall statistics"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM charging_stations")
    total_stations = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM charging_sessions WHERE status = 'in_progress'")
    active_sessions = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT 
            COUNT(*) as sessions,
            COALESCE(SUM(energy_delivered_kwh), 0) as energy,
            COALESCE(SUM(cost_eur), 0) as revenue
        FROM charging_sessions
        WHERE DATE(start_time) = CURRENT_DATE
    """)
    today = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    return {
        'total_stations': total_stations,
        'active_sessions': active_sessions,
        'today': {
            'sessions': today[0],
            'energy_kwh': float(today[1]),
            'revenue_eur': float(today[2])
        }
    }

@app.post("/api/stations")
def add_station(station: dict):
    """Add a new charging station"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO charging_stations 
        (name, location_lat, location_lng, city, country, power_kw, connector_type, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (
        station['name'],
        station['lat'],
        station['lng'],
        station['city'],
        station.get('country', 'Sweden'),
        station['power_kw'],
        station.get('connector_type', 'CCS'),
        'available'
    ))
    
    new_id = cursor.fetchone()[0]
    conn.commit()
    cursor.close()
    conn.close()
    
    return {"id": str(new_id), "message": "Station added successfully"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)