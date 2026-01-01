-- Charging Stations
CREATE TABLE charging_stations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    location_lat DECIMAL(9,6),
    location_lng DECIMAL(9,6),
    city VARCHAR(50),
    country VARCHAR(50),
    power_kw INTEGER NOT NULL,
    connector_type VARCHAR(20),
    status VARCHAR(20) DEFAULT 'available',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Charging Sessions
CREATE TABLE charging_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    station_id UUID REFERENCES charging_stations(id),
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    energy_delivered_kwh DECIMAL(10,2),
    cost_eur DECIMAL(10,2),
    status VARCHAR(20) DEFAULT 'in_progress',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Events Log (for analytics)
CREATE TABLE charging_events (
    id SERIAL PRIMARY KEY,
    session_id UUID REFERENCES charging_sessions(id),
    event_type VARCHAR(50) NOT NULL,
    event_data JSONB,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_sessions_station ON charging_sessions(station_id);
CREATE INDEX idx_sessions_start ON charging_sessions(start_time);
CREATE INDEX idx_events_session ON charging_events(session_id);
CREATE INDEX idx_events_timestamp ON charging_events(timestamp);

-- Sample seed data
INSERT INTO charging_stations (name, location_lat, location_lng, city, country, power_kw, connector_type, status) VALUES
('Göteborg Central Station', 57.7089, 11.9746, 'Göteborg', 'Sweden', 150, 'CCS', 'available'),
('Nordstan Mall', 57.7070, 11.9688, 'Göteborg', 'Sweden', 50, 'Type2', 'available'),
('Lindholmen Science Park', 57.7070, 11.9391, 'Göteborg', 'Sweden', 250, 'CCS', 'available'),
('Hisingen Ferry Terminal', 57.7226, 11.9391, 'Göteborg', 'Sweden', 100, 'CCS', 'available'),
('Slottsskogen Park', 57.6832, 11.9434, 'Göteborg', 'Sweden', 22, 'Type2', 'available');

---

