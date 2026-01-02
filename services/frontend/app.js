const API_URL = 'http://localhost:8000/api';
let map;
let markers = {};
let autoRefreshInterval;
let tempMarker = null; // Global variable

let isAddingStation = false; // Flag for adding mode

// Initialize map
function initMap() {
    // Center on Göteborg
    map = L.map('map').setView([57.7089, 11.9746], 13);
    
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
        maxZoom: 19
    }).addTo(map);
    
    // Map click handler for adding stations
    map.on('click', (e) => {
        console.log('🗺️ Map clicked at:', e.latlng.lat, e.latlng.lng); // DEBUG LOG
        
        const modal = document.getElementById('add-station-modal');
        
        // Check if modal is open
        if (!modal.classList.contains('hidden')) {
            console.log('✅ Modal is open, setting location...'); // DEBUG LOG
            
            // Set coordinates
            const lat = e.latlng.lat.toFixed(6);
            const lng = e.latlng.lng.toFixed(6);
            
            document.getElementById('station-lat').value = lat;
            document.getElementById('station-lng').value = lng;
            
            console.log('📍 Set coordinates:', lat, lng); // DEBUG LOG
            
            // Remove previous temp marker
            if (tempMarker) {
                map.removeLayer(tempMarker);
            }
            
            // Add temporary marker at clicked location
            tempMarker = L.marker([e.latlng.lat, e.latlng.lng], {
                icon: L.divIcon({
                    className: 'temp-marker',
                    html: `
                        <div style="
                            background: #e74c3c;
                            width: 40px;
                            height: 40px;
                            border-radius: 50%;
                            border: 4px solid white;
                            box-shadow: 0 4px 12px rgba(231, 76, 60, 0.5);
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            font-size: 20px;
                        ">
                            📍
                        </div>
                    `,
                    iconSize: [40, 40],
                    iconAnchor: [20, 40]
                })
            }).addTo(map);
            
            console.log('✅ Temp marker added'); // DEBUG LOG
            
            // Show success message
            const coordDisplay = document.getElementById('coord-display');
            if (coordDisplay) {
                coordDisplay.textContent = `✅ Selected: ${lat}, ${lng}`;
                coordDisplay.style.color = '#2ecc71';
                coordDisplay.style.fontWeight = 'bold';
            }
            
            // Flash the map to show it worked
            const mapContainer = document.getElementById('map');
            mapContainer.style.border = '3px solid #2ecc71';
            setTimeout(() => {
                mapContainer.style.border = 'none';
            }, 500);
            
        } else {
            console.log('ℹ️ Modal is closed, ignoring click'); // DEBUG LOG
        }
    });
}


// Show instruction overlay on map
function showMapInstruction() {
    // Remove existing overlay if any
    const existing = document.getElementById('map-instruction');
    if (existing) existing.remove();
    
    // Create instruction overlay
    const overlay = document.createElement('div');
    overlay.id = 'map-instruction';
    overlay.innerHTML = `
        <div style="
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: rgba(102, 126, 234, 0.95);
            color: white;
            padding: 20px 30px;
            border-radius: 12px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.3);
            z-index: 1000;
            text-align: center;
            font-size: 18px;
            font-weight: 600;
            pointer-events: none;
            animation: fadeIn 0.3s;
        ">
            📍 Click anywhere on the map to set station location
        </div>
    `;
    
    document.getElementById('map').appendChild(overlay);
    
    // Remove after 3 seconds
    setTimeout(() => {
        overlay.style.animation = 'fadeOut 0.3s';
        setTimeout(() => overlay.remove(), 300);
    }, 3000);
}

// Fetch and display stations
async function loadStations() {
    try {
        const response = await fetch(`${API_URL}/stations`);
        const data = await response.json();
        
        console.log('Loaded stations:', data.stations); // Debug log
        
        // Clear existing markers
        Object.values(markers).forEach(marker => map.removeLayer(marker));
        markers = {};
        
        // Add station markers
        data.stations.forEach(station => {
            console.log('Adding marker for:', station.name, station.lat, station.lng); // Debug
            
            // Determine marker color based on status
            const markerColor = station.active_sessions > 0 ? '#2ecc71' : '#667eea';
            const statusText = station.active_sessions > 0 ? '🔌 Charging' : '✅ Available';
            
            // Custom icon with HTML
            const icon = L.divIcon({
                className: 'custom-marker',
                html: `
                    <div style="
                        background: ${markerColor};
                        width: 30px;
                        height: 30px;
                        border-radius: 50%;
                        border: 4px solid white;
                        box-shadow: 0 2px 8px rgba(0,0,0,0.3);
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        font-size: 16px;
                    ">
                        ${station.active_sessions > 0 ? '⚡' : '🔋'}
                    </div>
                `,
                iconSize: [30, 30],
                iconAnchor: [15, 15],
                popupAnchor: [0, -15]
            });
            
            const marker = L.marker([station.lat, station.lng], { icon })
                .addTo(map)
                .bindPopup(`
                    <div style="min-width: 200px;">
                        <h3 style="margin: 0 0 10px 0; color: #667eea;">${station.name}</h3>
                        <p style="margin: 5px 0;"><strong>📍 City:</strong> ${station.city}</p>
                        <p style="margin: 5px 0;"><strong>⚡ Power:</strong> ${station.power_kw} kW</p>
                        <p style="margin: 5px 0;"><strong>🔌 Connector:</strong> ${station.connector_type}</p>
                        <p style="margin: 5px 0;"><strong>Status:</strong> ${statusText}</p>
                        <p style="margin: 5px 0;"><strong>Active Vehicles:</strong> ${station.active_sessions}</p>
                        <button onclick="showStationDetails('${station.id}')" 
                                style="margin-top: 10px; padding: 8px 16px; background: #667eea; 
                                       color: white; border: none; border-radius: 4px; cursor: pointer;">
                            View Details
                        </button>
                    </div>
                `)
                .on('click', () => {
                    console.log('Marker clicked:', station.name);
                });
            
            markers[station.id] = marker;
        });
        
        console.log('Total markers added:', Object.keys(markers).length);
        
    } catch (error) {
        console.error('Error loading stations:', error);
        alert('Failed to load stations. Check console for details.');
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
            alert('✅ Station added successfully!');
            document.getElementById('add-station-modal').classList.add('hidden');
            document.getElementById('add-station-form').reset();
            
            // Remove temp marker
            if (tempMarker) {
                map.removeLayer(tempMarker);
                tempMarker = null;
            }
            
            // Reset map style
            const mapContainer = document.getElementById('map');
            mapContainer.style.cursor = 'grab';
            mapContainer.style.border = 'none';
            
            // Reset coordinate display
            const coordDisplay = document.getElementById('coord-display');
            if (coordDisplay) {
                coordDisplay.textContent = 'No location selected yet';
                coordDisplay.style.color = '#e74c3c';
            }
            
            // Remove instruction overlay
            const instruction = document.getElementById('map-instruction');
            if (instruction) instruction.remove();
            
            loadStations();
            loadStats();
        } else {
            alert('❌ Failed to add station');
        }
    } catch (error) {
        console.error('Error adding station:', error);
        alert('❌ Failed to add station. Check console for details.');
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
    const modal = document.getElementById('add-station-modal');
    modal.classList.remove('hidden');
    
    // Add visual feedback to map
    const mapContainer = document.getElementById('map');
    mapContainer.style.cursor = 'crosshair';
    mapContainer.style.border = '3px dashed #667eea';
    
    console.log('🎯 Add station mode activated - click on map!');
    
    // Show instruction overlay
    showMapInstruction();
});

document.getElementById('cancel-add').addEventListener('click', () => {
    document.getElementById('add-station-modal').classList.add('hidden');
    
    // Remove temp marker
    if (tempMarker) {
        map.removeLayer(tempMarker);
        tempMarker = null;
    }
    
    // Reset map style
    const mapContainer = document.getElementById('map');
    mapContainer.style.cursor = 'grab';
    mapContainer.style.border = 'none';
    
    // Reset form
    document.getElementById('add-station-form').reset();
    document.getElementById('station-lat').value = '';
    document.getElementById('station-lng').value = '';
    const coordDisplay = document.getElementById('coord-display');
    if (coordDisplay) {
        coordDisplay.textContent = 'No location selected yet';
        coordDisplay.style.color = '#e74c3c';
    }
    
    // Remove instruction overlay
    const instruction = document.getElementById('map-instruction');
    if (instruction) instruction.remove();
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