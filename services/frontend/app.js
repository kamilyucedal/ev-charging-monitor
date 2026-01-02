const API_URL = 'http://localhost:8000/api';
let map;
let markers = {};
let autoRefreshInterval;

// Initialize map
function initMap() {
    // Center on Göteborg
    map = L.map('map').setView([57.7089, 11.9746], 13);
    
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors'
    }).addTo(map);
    
    // Map click handler for adding stations
    map.on('click', (e) => {
        if (!document.getElementById('add-station-modal').classList.contains('hidden')) {
            document.getElementById('station-lat').value = e.latlng.lat;
            document.getElementById('station-lng').value = e.latlng.lng;
            alert(`Location set: ${e.latlng.lat.toFixed(4)}, ${e.latlng.lng.toFixed(4)}`);
        }
    });
}

// Fetch and display stations
async function loadStations() {
    try {
        const response = await fetch(`${API_URL}/stations`);
        const data = await response.json();
        
        // Clear existing markers
        Object.values(markers).forEach(marker => map.removeLayer(marker));
        markers = {};
        
        // Add station markers
        data.stations.forEach(station => {
            const icon = L.divIcon({
                className: `station-marker ${station.status}`,
                html: `<div style="background: ${station.active_sessions > 0 ? '#2ecc71' : '#667eea'}; width: 20px; height: 20px; border-radius: 50%; border: 3px solid white;"></div>`,
                iconSize: [20, 20]
            });
            
            const marker = L.marker([station.lat, station.lng], { icon })
                .addTo(map)
                .bindPopup(`
                    <b>${station.name}</b><br>
                    ${station.city}<br>
                    Power: ${station.power_kw} kW<br>
                    Status: ${station.active_sessions > 0 ? '🔌 Charging' : '✅ Available'}<br>
                    Active: ${station.active_sessions} vehicle(s)
                `)
                .on('click', () => showStationDetails(station.id));
            
            markers[station.id] = marker;
        });
        
    } catch (error) {
        console.error('Error loading stations:', error);
    }
}

// Load stats
async function loadStats() {
    try {
        const response = await fetch(`${API_URL}/stats`);
        const data = await response.json();
        
        document.getElementById('total-stations').textContent = data.total_stations;
        document.getElementById('active-sessions').textContent = data.active_sessions;
        document.getElementById('today-energy').textContent = `${data.today.energy_kwh.toFixed(1)} kWh`;
        document.getElementById('today-revenue').textContent = `€${data.today.revenue_eur.toFixed(2)}`;
        
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

// Show station details
async function showStationDetails(stationId) {
    try {
        const response = await fetch(`${API_URL}/stations/${stationId}`);
        const station = await response.json();
        
        const sidebar = document.getElementById('station-details');
        const info = document.getElementById('station-info');
        
        info.innerHTML = `
            <h2>${station.name}</h2>
            <p><strong>City:</strong> ${station.city}</p>
            <p><strong>Power:</strong> ${station.power_kw} kW</p>
            <p><strong>Connector:</strong> ${station.connector_type}</p>
            <p><strong>Status:</strong> ${station.status}</p>
            
            <h3>Active Sessions (${station.active_sessions.length})</h3>
            ${station.active_sessions.length > 0 ? `
                <ul>
                    ${station.active_sessions.map(s => `
                        <li>
                            Started: ${new Date(s.start_time).toLocaleTimeString()}<br>
                            Energy: ${s.energy_kwh.toFixed(2)} kWh
                        </li>
                    `).join('')}
                </ul>
            ` : '<p>No active sessions</p>'}
            
            <h3>Last 24 Hours</h3>
            <p><strong>Total Sessions:</strong> ${station.stats_24h.total_sessions}</p>
            <p><strong>Total Energy:</strong> ${station.stats_24h.total_energy_kwh.toFixed(1)} kWh</p>
        `;
        
        sidebar.classList.remove('hidden');
        
    } catch (error) {
        console.error('Error loading station details:', error);
    }
}

// Add station
async function addStation(stationData) {
    try {
        const response = await fetch(`${API_URL}/stations`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(stationData)
        });
        
        if (response.ok) {
            alert('Station added successfully!');
            document.getElementById('add-station-modal').classList.add('hidden');
            document.getElementById('add-station-form').reset();
            loadStations();
            loadStats();
        }
    } catch (error) {
        console.error('Error adding station:', error);
        alert('Failed to add station');
    }
}

// Event listeners
document.getElementById('refresh-btn').addEventListener('click', () => {
    loadStations();
    loadStats();
});

document.getElementById('close-sidebar').addEventListener('click', () => {
    document.getElementById('station-details').classList.add('hidden');
});

document.getElementById('add-station-btn').addEventListener('click', () => {
    document.getElementById('add-station-modal').classList.remove('hidden');
});

document.getElementById('cancel-add').addEventListener('click', () => {
    document.getElementById('add-station-modal').classList.add('hidden');
});

document.getElementById('add-station-form').addEventListener('submit', (e) => {
    e.preventDefault();
    
    const lat = document.getElementById('station-lat').value;
    const lng = document.getElementById('station-lng').value;
    
    if (!lat || !lng) {
        alert('Please click on the map to set location!');
        return;
    }
    
    const stationData = {
        name: document.getElementById('station-name').value,
        city: document.getElementById('station-city').value,
        power_kw: parseInt(document.getElementById('station-power').value),
        connector_type: document.getElementById('station-connector').value,
        lat: parseFloat(lat),
        lng: parseFloat(lng)
    };
    
    addStation(stationData);
});

// Auto-refresh
document.getElementById('auto-refresh').addEventListener('change', (e) => {
    if (e.target.checked) {
        autoRefreshInterval = setInterval(() => {
            loadStations();
            loadStats();
        }, 5000);
    } else {
        clearInterval(autoRefreshInterval);
    }
});

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initMap();
    loadStations();
    loadStats();
    
    // Start auto-refresh
    autoRefreshInterval = setInterval(() => {
        loadStations();
        loadStats();
    }, 5000);
});