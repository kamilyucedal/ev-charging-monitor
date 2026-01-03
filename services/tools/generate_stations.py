import psycopg2
import random
from faker import Faker

fake = Faker()

# Göteborg, Stockholm, Malmö coordinates
CITIES = {
    'Göteborg': {'center': (57.7089, 11.9746), 'radius': 0.1, 'count': 400},
    'Stockholm': {'center': (59.3293, 18.0686), 'radius': 0.15, 'count': 500},
    'Malmö': {'center': (55.6050, 13.0038), 'radius': 0.08, 'count': 100}
}

POWER_LEVELS = [22, 50, 100, 150, 250, 350]  # kW
CONNECTOR_TYPES = ['Type2', 'CCS', 'CHAdeMO']

def generate_station(city, lat_center, lng_center, radius):
    """Generate realistic station data"""
    lat = lat_center + random.uniform(-radius, radius)
    lng = lng_center + random.uniform(-radius, radius)
    
    return {
        'name': f"{city} {fake.street_name()} Charging",
        'lat': lat,
        'lng': lng,
        'city': city,
        'country': 'Sweden',
        'power_kw': random.choice(POWER_LEVELS),
        'connector_type': random.choice(CONNECTOR_TYPES),
        'status': 'available'
    }

def insert_stations(stations):
    """Bulk insert stations to PostgreSQL"""
    conn = psycopg2.connect(
        host='localhost',
        user='evuser',
        password='evpass',
        database='evcharging'
    )
    cursor = conn.cursor()
    
    for station in stations:
        cursor.execute("""
            INSERT INTO charging_stations 
            (name, location_lat, location_lng, city, country, power_kw, connector_type, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            station['name'], station['lat'], station['lng'], 
            station['city'], station['country'], station['power_kw'],
            station['connector_type'], station['status']
        ))
    
    conn.commit()
    print(f"✅ Inserted {len(stations)} stations")
    cursor.close()
    conn.close()

if __name__ == "__main__":
    all_stations = []
    
    for city, config in CITIES.items():
        print(f"Generating {config['count']} stations for {city}...")
        for _ in range(config['count']):
            station = generate_station(
                city, 
                config['center'][0], 
                config['center'][1], 
                config['radius']
            )
            all_stations.append(station)
    
    print(f"Total stations generated: {len(all_stations)}")
    print("Inserting to database...")
    insert_stations(all_stations)
    print("✅ Done!")
