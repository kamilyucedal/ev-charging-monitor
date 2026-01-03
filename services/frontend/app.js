const API_URL = 'http://localhost:8000/api';
let map;
let markers = {};
let autoRefreshInterval;
let tempMarker = null; // Global variable

let isAddingStation = false; // Flag for adding mode

// Initialize map
// Initialize map
function initMap() {
    map = L.map('map').setView([57.7089, 11.9746], 13);
    
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
        maxZoom: 19
    }).addTo(map);
    
    // Map click handler for adding stations
    map.on('click', (e) => {
        console.log('🗺️ Map clicked at:', e.latlng.lat, e.latlng.lng);
        
        const sidebar = document.getElementById('add-station-sidebar');
        
        // NULL CHECK - önemli!
        if (!sidebar) {
            console.warn('⚠️ add-station-sidebar element not found in DOM');
            return;
        }
        
        if (!sidebar.classList.contains('hidden')) {
            console.log('✅ Sidebar is open, setting location...');
            
            const lat = e.latlng.lat.toFixed(6);
            const lng = e.latlng.lng.toFixed(6);
            
            const latInput = document.getElementById('station-lat');
            const lngInput = document.getElementById('station-lng');
            
            if (latInput && lngInput) {
                latInput.value = lat;
                lngInput.value = lng;
                
                console.log('📍 Set coordinates:', lat, lng);
                
                // Remove previous temp marker
                if (tempMarker) {
                    map.removeLayer(tempMarker);
                }
                
                // Add temporary marker
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
                
                console.log('✅ Temp marker added');
                
                // Update coordinate display
                const coordDisplay = document.getElementById('coord-display');
                if (coordDisplay) {
                    coordDisplay.textContent = `✅ Selected: ${lat}, ${lng}`;
                    coordDisplay.style.color = '#2ecc71';
                    coordDisplay.style.fontWeight = 'bold';
                }
                
                // Flash the map
                const mapContainer = document.getElementById('map');
                if (mapContainer) {
                    mapContainer.style.border = '3px solid #2ecc71';
                    setTimeout(() => {
                        mapContainer.style.border = 'none';
                    }, 500);
                }
            } else {
                console.error('❌ Coordinate input fields not found');
            }
        } else {
            console.log('ℹ️ Sidebar is closed, ignoring click');
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

// Show toast notification
function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s';
        setTimeout(() => toast.remove(), 300);
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

// Load stats AND health
async function loadStats() {
    try {
        // Existing stats
        const response = await fetch(`${API_URL}/stats`);
        const data = await response.json();
        
        document.getElementById('total-stations').textContent = data.total_stations;
        document.getElementById('active-sessions').textContent = data.active_sessions;
        document.getElementById('today-energy').textContent = `${data.today.energy_kwh.toFixed(1)} kWh`;
        document.getElementById('today-revenue').textContent = `€${data.today.revenue_eur.toFixed(2)}`;
        
        // NEW: Health stats
        const healthResponse = await fetch(`${API_URL}/stations/health`);
        const healthData = await healthResponse.json();
        
        if (healthData.status === 'ok') {
            // Update health panel (we'll add this to HTML)
            updateHealthPanel(healthData);
        }
        
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

function updateHealthPanel(healthData) {
    // Show health counts
    const healthPanel = document.getElementById('health-panel');
    if (healthPanel) {
        healthPanel.innerHTML = `
            <div class="health-stat online">
                <span class="health-icon">🟢</span>
                <span class="health-count">${healthData.health_counts.online}</span>
                <span class="health-label">Online</span>
            </div>
            <div class="health-stat degraded">
                <span class="health-icon">🟡</span>
                <span class="health-count">${healthData.health_counts.degraded}</span>
                <span class="health-label">Degraded</span>
            </div>
            <div class="health-stat offline">
                <span class="health-icon">🔴</span>
                <span class="health-count">${healthData.health_counts.offline}</span>
                <span class="health-label">Offline</span>
            </div>
        `;
    }
    
    // Show offline stations alert if any
    if (healthData.offline_stations.length > 0) {
        console.warn(`⚠️ ${healthData.offline_stations.length} stations offline!`);
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
// Add station - Simple version with page reload
async function addStation(stationData) {
    const submitBtn = document.querySelector('#add-station-form button[type="submit"]');
    const originalText = submitBtn.textContent;
    
    try {
        // Show loading
        submitBtn.disabled = true;
        submitBtn.textContent = '⏳ Adding...';
        
        const response = await fetch(`${API_URL}/stations`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(stationData)
        });
        
        if (response.ok) {
            submitBtn.textContent = '✅ Success!';
            setTimeout(() => location.reload(), 1000);
        } else {
            submitBtn.textContent = '❌ Failed';
            submitBtn.disabled = false;
            setTimeout(() => {
                submitBtn.textContent = originalText;
            }, 2000);
        }
    } catch (error) {
        console.error('Error adding station:', error);
        submitBtn.textContent = originalText;
        submitBtn.disabled = false;
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
    const sidebar = document.getElementById('add-station-sidebar');
    sidebar.classList.remove('hidden');
    
    // Add visual feedback to map
    const mapContainer = document.getElementById('map');
    mapContainer.style.cursor = 'crosshair';
    mapContainer.style.border = '3px dashed #667eea';
    
    console.log('🎯 Add station mode activated - click on map!');
    showMapInstruction();
});


// Form submit handler'a ekle
document.getElementById('add-station-form').addEventListener('submit', (e) => {
    e.preventDefault();
    
    const lat = document.getElementById('station-lat').value;
    const lng = document.getElementById('station-lng').value;
    
    if (!lat || !lng) {
        // Highlight the location display
        const coordDisplay = document.getElementById('coord-display');
        coordDisplay.textContent = '⚠️ Please select a location first!';
        coordDisplay.style.color = '#e74c3c';
        coordDisplay.style.fontSize = '1.1rem';
        coordDisplay.style.fontWeight = 'bold';
        
        // Shake animation
        const locationBox = document.querySelector('.location-display');
        locationBox.style.animation = 'shake 0.5s';
        setTimeout(() => {
            locationBox.style.animation = '';
        }, 500);
        
        return;
    }
    
    // Continue with submission
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

document.getElementById('close-add-sidebar').addEventListener('click', () => {
    const sidebar = document.getElementById('add-station-sidebar');
    sidebar.classList.add('hidden');
    
    // Reset everything (same as before)
    if (tempMarker) {
        map.removeLayer(tempMarker);
        tempMarker = null;
    }
    
    const mapContainer = document.getElementById('map');
    mapContainer.style.cursor = 'grab';
    mapContainer.style.border = 'none';
    
    document.getElementById('add-station-form').reset();
    document.getElementById('station-lat').value = '';
    document.getElementById('station-lng').value = '';
    
    const coordDisplay = document.getElementById('coord-display');
    if (coordDisplay) {
        coordDisplay.textContent = 'No location selected yet';
        coordDisplay.style.color = '#e74c3c';
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