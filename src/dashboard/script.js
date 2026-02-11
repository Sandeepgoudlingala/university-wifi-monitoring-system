// Enhanced Campus WiFi Quality Dashboard Script with Real-time Location Tracking

class WiFiDashboard {
    constructor() {
        this.apiBaseUrl = '/api';
        this.map = null;
        this.markers = [];
        this.accessPointMarkers = []; // Separate markers for access points
        this.userLocationMarker = null; // Marker for user's current location
        this.accessPoints = [];
        this.filteredAps = [];
        this.userLocation = null;
        this.locationWatchId = null;
        
        this.init();
    }
    
    async init() {
        await this.loadData();
        this.setupEventListeners();
        this.initializeMap();
        this.startLocationTracking(); // Start tracking user's location
        this.updateDashboard();
        
        // Set up auto-refresh every 30 seconds
        setInterval(() => {
            this.refreshData();
        }, 30000);
    }
    
    startLocationTracking() {
        if (!navigator.geolocation) {
            console.warn('Geolocation is not supported by this browser.');
            return;
        }
        
        // Watch for changes in position with better settings
        this.locationWatchId = navigator.geolocation.watchPosition(
            (position) => {
                this.userLocation = {
                    lat: position.coords.latitude,
                    lng: position.coords.longitude
                };
                
                this.updateUserLocationMarker();
                this.updateRecommendations(); // Update recommendations based on user location
            },
            (error) => {
                console.warn('Unable to retrieve location:', error.message);
                // Handle different types of errors
                switch(error.code) {
                    case error.PERMISSION_DENIED:
                        console.warn("Location access denied by user");
                        break;
                    case error.POSITION_UNAVAILABLE:
                        console.warn("Location information is unavailable");
                        break;
                    case error.TIMEOUT:
                        console.warn("Location request timed out - continuing with default location");
                        break;
                    default:
                        console.warn("An unknown error occurred");
                        break;
                }
                
                // Still initialize map with default location if needed
                if (!this.map.hasLayer(L.tileLayer()) && !this.map.hasLayer(L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png'))) {
                    this.map.setView([40.7128, -74.0060], 15); // Default to NYC coordinates
                }
            },
            {
                enableHighAccuracy: false, // Changed to false to reduce timeout issues
                maximumAge: 60000, // Accept cached positions up to 60 seconds old
                timeout: 20000     // Wait 20 seconds for location
            }
        );
    }
    
    updateUserLocationMarker() {
        if (!this.userLocation) return;
        
        // Remove existing user location marker if present
        if (this.userLocationMarker) {
            this.map.removeLayer(this.userLocationMarker);
        }
        
        // Create new user location marker
        this.userLocationMarker = L.marker([this.userLocation.lat, this.userLocation.lng], {
            icon: L.divIcon({
                className: 'user-location-marker',
                html: '<div style="background: #3b82f6; width: 24px; height: 24px; border: 3px solid white; border-radius: 50%; box-shadow: 0 0 10px rgba(0,0,0,0.5);"></div>',
                iconSize: [24, 24],
                iconAnchor: [12, 12]
            })
        }).addTo(this.map);
        
        // Add popup to user location marker
        this.userLocationMarker.bindPopup(`
            <div>
                <h3>Your Location</h3>
                <p>Lat: ${this.userLocation.lat.toFixed(6)}</p>
                <p>Lng: ${this.userLocation.lng.toFixed(6)}</p>
                <p><small>Real-time location tracking</small></p>
            </div>
        `);
        
        // Center map on user location (but not too aggressively)
        if (!this.map.getBounds().contains([this.userLocation.lat, this.userLocation.lng])) {
            this.map.setView([this.userLocation.lat, this.userLocation.lng], 15);
        }
    }
    
    async loadData() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/access-points`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            this.accessPoints = await response.json();
            this.filteredAps = [...this.accessPoints]; // Initially show all
            console.log('Loaded access points:', this.accessPoints.length);
        } catch (error) {
            console.error('Error loading data:', error);
            // Show error message to user
            document.getElementById('apTableBody').innerHTML = `
                <tr>
                    <td colspan="7" style="text-align: center; color: #ef4444; padding: 2rem;">
                        <i class="fas fa-exclamation-triangle" style="font-size: 2rem; margin-bottom: 0.5rem;"></i><br>
                        Error loading data. Make sure the backend server is running.<br>
                        <small>Please check your connection and refresh the page.</small>
                    </td>
                </tr>
            `;
        }
    }
    
    setupEventListeners() {
        document.getElementById('refreshBtn').addEventListener('click', () => {
            this.refreshData();
        });
        
        document.getElementById('locateBtn').addEventListener('click', () => {
            this.locateUser();
        });
        
        document.getElementById('buildingFilter').addEventListener('change', (e) => {
            this.applyFilters();
        });
        
        document.getElementById('statusFilter').addEventListener('change', (e) => {
            this.applyFilters();
        });
    }
    
    locateUser() {
        if (!navigator.geolocation) {
            alert('Geolocation is not supported by your browser.');
            return;
        }
        
        // Show loading indicator
        const locateBtn = document.getElementById('locateBtn');
        const originalText = locateBtn.innerHTML;
        locateBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Locating...';
        locateBtn.disabled = true;
        
        // Check if on mobile device to adjust settings
        const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
        
        // Request one-time location
        navigator.geolocation.getCurrentPosition(
            (position) => {
                this.userLocation = {
                    lat: position.coords.latitude,
                    lng: position.coords.longitude
                };
                
                this.updateUserLocationMarker();
                
                // Center map on user location
                this.map.setView([this.userLocation.lat, this.userLocation.lng], 15);
                
                // Update recommendations based on new location
                this.updateRecommendations();
                
                // Reset button
                locateBtn.innerHTML = '<i class="fas fa-check"></i> Located!';
                setTimeout(() => {
                    locateBtn.innerHTML = originalText;
                    locateBtn.disabled = false;
                }, 1000);
            },
            (error) => {
                console.warn('Unable to retrieve location:', error.message);
                
                // Reset button
                locateBtn.innerHTML = originalText;
                locateBtn.disabled = false;
                
                // Handle different types of errors
                let errorMessage = "Unable to retrieve location";
                switch(error.code) {
                    case error.PERMISSION_DENIED:
                        errorMessage = "Location access denied. Please enable location services in your browser settings.";
                        break;
                    case error.POSITION_UNAVAILABLE:
                        errorMessage = "Location information unavailable.";
                        break;
                    case error.TIMEOUT:
                        errorMessage = "Location request timed out. Please ensure you have good GPS reception and try again.";
                        break;
                    default:
                        errorMessage = "An unknown error occurred.";
                        break;
                }
                
                // Show error to user
                locateBtn.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Error!';
                setTimeout(() => {
                    locateBtn.innerHTML = originalText;
                    locateBtn.disabled = false;
                    alert(errorMessage);
                }, 1000);
            },
            {
                enableHighAccuracy: isMobile ? false : true, // On mobile, avoid high accuracy to save battery
                maximumAge: isMobile ? 120000 : 60000, // Accept older cached positions on mobile (2 mins vs 1 min)
                timeout: isMobile ? 30000 : 20000     // Longer timeout on mobile for better GPS acquisition
            }
        );
    }
    
    initializeMap() {
        // Initialize the map centered on a typical university location
        this.map = L.map('map').setView([40.7128, -74.0060], 15); // Using NYC coordinates as placeholder
        
        // Add OpenStreetMap tiles
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        }).addTo(this.map);
        
        // Add markers for access points
        this.updateMapMarkers();
    }
    
    updateMapMarkers() {
        // Clear existing access point markers
        this.accessPointMarkers.forEach(marker => this.map.removeLayer(marker));
        this.accessPointMarkers = [];
        
        // Add new markers based on access points with location data
        this.filteredAps.forEach(ap => {
            if (ap.latitude && ap.longitude) {
                let markerColor = '#64748b'; // default gray
                
                if (ap.quality_score >= 80) {
                    markerColor = '#10b981'; // green
                } else if (ap.quality_score >= 60) {
                    markerColor = '#f59e0b'; // yellow
                } else if (ap.quality_score >= 40) {
                    markerColor = '#f97316'; // orange
                } else {
                    markerColor = '#ef4444'; // red
                }
                
                const marker = L.circleMarker([ap.latitude, ap.longitude], {
                    radius: 10,
                    fillColor: markerColor,
                    color: '#ffffff',
                    weight: 2,
                    opacity: 1,
                    fillOpacity: 0.8
                }).addTo(this.map);
                
                // Add popup with details
                marker.bindPopup(`
                    <div style="min-width: 200px;">
                        <h3 style="margin: 0 0 0.5rem 0; color: #1e293b;">${ap.ap_name}</h3>
                        <div style="display: grid; grid-template-columns: auto auto; gap: 0.25rem 0.5rem; font-size: 0.9rem;">
                            <div>Building:</div><div><strong>${ap.building || 'N/A'}</strong></div>
                            <div>Floor:</div><div><strong>${ap.floor || 'N/A'}</strong></div>
                            <div>Status:</div><div><span style="color: ${markerColor}; font-weight: bold;">${ap.status}</span></div>
                            <div>Quality:</div><div><strong>${ap.quality_score || 0}/100</strong></div>
                            <div>Speed:</div><div><strong>${(ap.download_speed || 0).toFixed(1)}↓ ${(ap.upload_speed || 0).toFixed(1)}↑ Mbps</strong></div>
                            <div>Users:</div><div><strong>${ap.connected_users || 0}</strong></div>
                        </div>
                    </div>
                `);
                
                this.accessPointMarkers.push(marker);
            }
        });
    }
    
    updateDashboard() {
        // Update statistics
        this.updateStats();
        
        // Update quick stats
        this.updateQuickStats();
        
        // Update alerts
        this.updateAlerts();
        
        // Populate access points table
        this.populateApTable();
        
        // Populate filters
        this.populateFilters();
        
        // Update recommendations
        this.updateRecommendations();
    }
    
    updateStats() {
        const totalAps = this.accessPoints.length;
        const activeAps = this.accessPoints.filter(ap => ap.quality_score > 0).length;
        const congestedAps = this.accessPoints.filter(ap => 
            (ap.connected_users || 0) > 30 || (ap.quality_score || 0) < 40
        ).length;
        
        const avgQuality = totalAps > 0 
            ? (this.accessPoints.reduce((sum, ap) => sum + (ap.quality_score || 0), 0) / totalAps).toFixed(1)
            : 0;
        
        // Update main stats
        this.animateValue('totalAps', parseInt(document.getElementById('totalAps').textContent || 0), totalAps, 1000);
        this.animateValue('activeAps', parseInt(document.getElementById('activeAps').textContent || 0), activeAps, 1000);
        this.animateValue('congestedAps', parseInt(document.getElementById('congestedAps').textContent || 0), congestedAps, 1000);
        this.animateValue('avgQuality', parseFloat(document.getElementById('avgQuality').textContent?.replace('/100', '') || 0), parseFloat(avgQuality), 1000);
        
        // Update hero stats with animation
        this.animateValue('totalAps', parseInt(document.querySelector('.hero-stat:nth-child(1) .stat-value-large').textContent || 0), totalAps, 1000);
        this.animateValue('activeAps', parseInt(document.querySelector('.hero-stat:nth-child(2) .stat-value-large').textContent || 0), activeAps, 1000);
        this.animateValue('avgQuality', parseFloat(document.querySelector('.hero-stat:nth-child(3) .stat-value-large').textContent || 0), parseFloat(avgQuality), 1000);
    }
    
    animateValue(elementId, start, end, duration) {
        let startEl = document.getElementById(elementId);
        if (!startEl) {
            // Check for hero stats
            if (elementId === 'totalAps') {
                startEl = document.querySelector('.hero-stat:nth-child(1) .stat-value-large');
            } else if (elementId === 'activeAps') {
                startEl = document.querySelector('.hero-stat:nth-child(2) .stat-value-large');
            } else if (elementId === 'avgQuality') {
                startEl = document.querySelector('.hero-stat:nth-child(3) .stat-value-large');
            }
        }
        
        if (!startEl) return;
        
        let startTime = null;
        const step = (timestamp) => {
            if (!startTime) startTime = timestamp;
            const progress = Math.min((timestamp - startTime) / duration, 1);
            const currentValue = Math.floor(start + (end - start) * progress);
            
            if (elementId === 'avgQuality') {
                const decimalValue = start + (end - start) * progress;
                if (startEl.id) {
                    startEl.textContent = `${decimalValue.toFixed(1)}/100`;
                } else {
                    startEl.textContent = decimalValue.toFixed(1);
                }
            } else {
                startEl.textContent = currentValue;
            }
            
            if (progress < 1) {
                window.requestAnimationFrame(step);
            }
        };
        window.requestAnimationFrame(step);
    }
    
    updateQuickStats() {
        const avgDownload = this.accessPoints.length > 0 
            ? (this.accessPoints.reduce((sum, ap) => sum + (ap.download_speed || 0), 0) / this.accessPoints.length).toFixed(1)
            : 0;
            
        const avgUpload = this.accessPoints.length > 0 
            ? (this.accessPoints.reduce((sum, ap) => sum + (ap.upload_speed || 0), 0) / this.accessPoints.length).toFixed(1)
            : 0;
            
        const avgLatency = this.accessPoints.length > 0 
            ? (this.accessPoints.reduce((sum, ap) => sum + (ap.latency || 0), 0) / this.accessPoints.length).toFixed(1)
            : 0;
        
        document.getElementById('avgDownload').textContent = `${avgDownload} Mbps`;
        document.getElementById('avgUpload').textContent = `${avgUpload} Mbps`;
        document.getElementById('avgLatency').textContent = `${avgLatency} ms`;
    }
    
    updateAlerts() {
        const alertsContainer = document.getElementById('alertsContainer');
        const congestedAps = this.accessPoints.filter(ap => (ap.connected_users || 0) > 30);
        
        if (congestedAps.length > 0) {
            alertsContainer.innerHTML = '';
            
            congestedAps.slice(0, 3).forEach(ap => {
                const alertDiv = document.createElement('div');
                alertDiv.className = 'alert alert-warning';
                alertDiv.innerHTML = `
                    <i class="fas fa-exclamation-triangle"></i>
                    <span><strong>${ap.ap_name}</strong> is congested (${ap.connected_users || 0} users)</span>
                `;
                alertsContainer.appendChild(alertDiv);
            });
            
            if (congestedAps.length > 3) {
                const moreAlert = document.createElement('div');
                moreAlert.className = 'alert alert-info';
                moreAlert.innerHTML = `
                    <i class="fas fa-info-circle"></i>
                    <span>and ${congestedAps.length - 3} more congested access points</span>
                `;
                alertsContainer.appendChild(moreAlert);
            }
        } else {
            alertsContainer.innerHTML = `
                <div class="alert alert-success">
                    <i class="fas fa-check-circle"></i>
                    <span>All access points are operating normally</span>
                </div>
            `;
        }
    }
    
    populateApTable() {
        const tbody = document.getElementById('apTableBody');
        tbody.innerHTML = '';
        
        // Sort by quality score descending
        const sortedAps = [...this.filteredAps].sort((a, b) => (b.quality_score || 0) - (a.quality_score || 0));
        
        if (sortedAps.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="7" style="text-align: center; padding: 2rem; color: #94a3b8;">
                        <i class="fas fa-search" style="font-size: 2rem; margin-bottom: 0.5rem;"></i><br>
                        No access points match your current filters
                    </td>
                </tr>
            `;
            return;
        }
        
        sortedAps.forEach(ap => {
            const row = document.createElement('tr');
            
            // Determine status class
            let statusClass = 'status-poor';
            if (ap.quality_score >= 80) statusClass = 'status-excellent';
            else if (ap.quality_score >= 60) statusClass = 'status-good';
            else if (ap.quality_score >= 40) statusClass = 'status-medium';
            
            row.innerHTML = `
                <td><i class="fas fa-tag"></i> ${ap.ap_name}</td>
                <td><i class="fas fa-location-dot"></i> ${ap.building || 'N/A'} Floor ${ap.floor || 'N/A'}</td>
                <td class="${statusClass}"><i class="fas fa-circle"></i> ${ap.status}</td>
                <td><i class="fas fa-star"></i> ${ap.quality_score || 0}/100</td>
                <td><i class="fas fa-bolt"></i> ${(ap.download_speed || 0).toFixed(1)}↓ ${(ap.upload_speed || 0).toFixed(1)}↑</td>
                <td><i class="fas fa-users"></i> ${ap.connected_users || 0}</td>
                <td><i class="fas fa-signal"></i> ${ap.signal_strength || 0} dBm</td>
            `;
            
            tbody.appendChild(row);
        });
    }
    
    populateFilters() {
        // Populate building filter
        const buildingFilter = document.getElementById('buildingFilter');
        const buildings = [...new Set(this.accessPoints.map(ap => ap.building).filter(Boolean))];
        
        buildingFilter.innerHTML = '<option value="all">All Buildings</option>';
        buildings.forEach(building => {
            const option = document.createElement('option');
            option.value = building;
            option.textContent = building;
            buildingFilter.appendChild(option);
        });
        
        // Status filter is already populated in HTML
    }
    
    applyFilters() {
        const buildingFilter = document.getElementById('buildingFilter').value;
        const statusFilter = document.getElementById('statusFilter').value;
        
        let filtered = [...this.accessPoints];
        
        if (buildingFilter !== 'all') {
            filtered = filtered.filter(ap => ap.building === buildingFilter);
        }
        
        if (statusFilter !== 'all') {
            filtered = filtered.filter(ap => ap.status === statusFilter);
        }
        
        this.filteredAps = filtered;
        this.populateApTable();
        this.updateMapMarkers();
    }
    
    updateRecommendations() {
        const container = document.getElementById('recommendationsContainer');
        
        // If we have user location, find nearby access points
        if (this.userLocation) {
            // Calculate distances to all access points
            const apsWithDistance = this.accessPoints
                .filter(ap => ap.latitude && ap.longitude && ap.quality_score > 0)
                .map(ap => {
                    const distance = this.calculateDistance(
                        this.userLocation.lat, 
                        this.userLocation.lng, 
                        ap.latitude, 
                        ap.longitude
                    );
                    return { ...ap, distance };
                })
                .sort((a, b) => a.distance - b.distance)  // Sort by distance (nearest first)
                .slice(0, 10);  // Get top 10 nearest access points
            
            // Then sort by quality score within the nearest ones
            const bestNearby = [...apsWithDistance]
                .sort((a, b) => b.quality_score - a.quality_score)
                .slice(0, 3);
            
            if (bestNearby.length > 0) {
                let recommendationHtml = '<div class="recommendations-list">';
                
                bestNearby.forEach((ap, index) => {
                    const distanceText = ap.distance < 1000 
                        ? `${Math.round(ap.distance)}m away` 
                        : `${(ap.distance / 1000).toFixed(1)}km away`;
                    
                    // Calculate signal strength indicator
                    const signalStrength = ap.signal_strength || -70;
                    let signalIndicator = '';
                    if (signalStrength > -50) {
                        signalIndicator = '<i class="fas fa-signal text-green-500"></i> Excellent';
                    } else if (signalStrength > -60) {
                        signalIndicator = '<i class="fas fa-signal text-yellow-500"></i> Good';
                    } else if (signalStrength > -70) {
                        signalIndicator = '<i class="fas fa-signal text-orange-500"></i> Fair';
                    } else {
                        signalIndicator = '<i class="fas fa-signal text-red-500"></i> Weak';
                    }
                    
                    recommendationHtml += `
                        <div class="recommendation-item slide-in-right" style="animation-delay: ${index * 0.1}s;">
                            <div class="recommendation-rank">${index + 1}</div>
                            <div class="recommendation-details">
                                <div class="recommendation-title">${ap.ap_name}</div>
                                <div class="recommendation-location">${ap.building || 'N/A'} Floor ${ap.floor || 'N/A'} • ${distanceText}</div>
                                <div class="recommendation-stats">
                                    <div class="progress-bar">
                                        <div class="progress-fill" style="width: ${ap.quality_score}%"></div>
                                    </div>
                                    <div class="flex justify-between mt-1">
                                        <span class="quality-badge ${this.getStatusClass(ap.quality_score)}">${ap.status}</span>
                                        <span>Quality: ${ap.quality_score || 0}/100</span>
                                        <span>Speed: ${(ap.download_speed || 0).toFixed(1)}↓ Mbps</span>
                                    </div>
                                    <div class="flex items-center gap-2 mt-1">
                                        <span class="text-xs">${signalIndicator}</span>
                                        <span class="text-xs">Users: ${ap.connected_users || 0}</span>
                                    </div>
                                </div>
                                <button class="btn btn-sm btn-outline" onclick="window.open('https://www.google.com/maps/dir/?api=1&destination=${ap.latitude},${ap.longitude}', '_blank')">
                                    <i class="fas fa-directions"></i> Get Directions
                                </button>
                            </div>
                        </div>
                    `;
                });
                
                recommendationHtml += '</div>';
                container.innerHTML = recommendationHtml;
            } else {
                container.innerHTML = `
                    <div class="recommendation-placeholder fade-in-up">
                        <i class="fas fa-wifi recommendation-icon"></i>
                        <p>No nearby access points with quality data available.</p>
                        <small>Your location: ${this.userLocation.lat.toFixed(4)}, ${this.userLocation.lng.toFixed(4)}</small>
                    </div>
                `;
            }
        } else {
            // Fallback to top performing access points globally
            const topAps = [...this.accessPoints]
                .filter(ap => ap.quality_score > 0)
                .sort((a, b) => b.quality_score - a.quality_score)
                .slice(0, 3);
            
            if (topAps.length > 0) {
                let recommendationHtml = '<div class="recommendations-list">';
                
                topAps.forEach((ap, index) => {
                    // Calculate signal strength indicator
                    const signalStrength = ap.signal_strength || -70;
                    let signalIndicator = '';
                    if (signalStrength > -50) {
                        signalIndicator = '<i class="fas fa-signal text-green-500"></i> Excellent';
                    } else if (signalStrength > -60) {
                        signalIndicator = '<i class="fas fa-signal text-yellow-500"></i> Good';
                    } else if (signalStrength > -70) {
                        signalIndicator = '<i class="fas fa-signal text-orange-500"></i> Fair';
                    } else {
                        signalIndicator = '<i class="fas fa-signal text-red-500"></i> Weak';
                    }
                    
                    recommendationHtml += `
                        <div class="recommendation-item slide-in-left" style="animation-delay: ${index * 0.1}s;">
                            <div class="recommendation-rank">${index + 1}</div>
                            <div class="recommendation-details">
                                <div class="recommendation-title">${ap.ap_name}</div>
                                <div class="recommendation-location">${ap.building || 'N/A'} Floor ${ap.floor || 'N/A'}</div>
                                <div class="recommendation-stats">
                                    <div class="progress-bar">
                                        <div class="progress-fill" style="width: ${ap.quality_score}%"></div>
                                    </div>
                                    <div class="flex justify-between mt-1">
                                        <span class="quality-badge ${this.getStatusClass(ap.quality_score)}">${ap.status}</span>
                                        <span>Quality: ${ap.quality_score || 0}/100</span>
                                        <span>Speed: ${(ap.download_speed || 0).toFixed(1)}↓ Mbps</span>
                                    </div>
                                    <div class="flex items-center gap-2 mt-1">
                                        <span class="text-xs">${signalIndicator}</span>
                                        <span class="text-xs">Users: ${ap.connected_users || 0}</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    `;
                });
                
                recommendationHtml += '</div>';
                container.innerHTML = recommendationHtml;
            } else {
                container.innerHTML = `
                    <div class="recommendation-placeholder fade-in-up">
                        <i class="fas fa-wifi recommendation-icon"></i>
                        <p>No access points with quality data available.</p>
                        <small>Data is being collected in real-time</small>
                    </div>
                `;
            }
        }
    }
    
    calculateDistance(lat1, lon1, lat2, lon2) {
        // Haversine formula to calculate distance between two points
        const R = 6371e3; // Earth radius in meters
        const φ1 = lat1 * Math.PI/180;
        const φ2 = lat2 * Math.PI/180;
        const Δφ = (lat2-lat1) * Math.PI/180;
        const Δλ = (lon2-lon1) * Math.PI/180;

        const a = Math.sin(Δφ/2) * Math.sin(Δφ/2) +
                Math.cos(φ1) * Math.cos(φ2) *
                Math.sin(Δλ/2) * Math.sin(Δλ/2);
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));

        return R * c; // Distance in meters
    }
    
    getStatusClass(qualityScore) {
        if (qualityScore >= 80) return 'status-excellent';
        else if (qualityScore >= 60) return 'status-good';
        else if (qualityScore >= 40) return 'status-medium';
        else return 'status-poor';
    }
    
    async refreshData() {
        const refreshBtn = document.getElementById('refreshBtn');
        const originalText = refreshBtn.innerHTML;
        refreshBtn.innerHTML = '<i class="fas fa-sync-alt fa-spin"></i> Refreshing...';
        refreshBtn.disabled = true;
        
        try {
            await this.loadData();
            this.applyFilters(); // Reapply filters after loading new data
            this.updateDashboard();
            console.log('Data refreshed successfully');
            
            // Show success feedback
            refreshBtn.innerHTML = '<i class="fas fa-check"></i> Refreshed!';
            setTimeout(() => {
                refreshBtn.innerHTML = originalText;
                refreshBtn.disabled = false;
            }, 1000);
        } catch (error) {
            console.error('Error refreshing data:', error);
            refreshBtn.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Error!';
            setTimeout(() => {
                refreshBtn.innerHTML = originalText;
                refreshBtn.disabled = false;
            }, 2000);
        }
    }
}

// Initialize the dashboard when the page loads
document.addEventListener('DOMContentLoaded', () => {
    new WiFiDashboard();
});