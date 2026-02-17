from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import json
import os
from datetime import datetime
import sqlite3
import traceback
from werkzeug.middleware.proxy_fix import ProxyFix
import threading

# Import data collection module
try:
    from ..data_collection.collector import WiFiDataCollector
except ImportError:
    # If the collector module doesn't exist, create a mock version
    class WiFiDataCollector:
        def __init__(self, api_base_url=""):
            pass
        def start_collection(self, interval=60):
            print("Mock collector: Would start collecting data")
        def stop_collection(self):
            print("Mock collector: Would stop collection")

# Determine the correct path based on environment
current_dir = os.path.dirname(os.path.abspath(__file__))
dashboard_path = os.path.join(current_dir, '../dashboard')

if os.environ.get('PRODUCTION', '').lower() == 'true':
    # In production, dashboard files are in the same directory structure
    app = Flask(__name__, static_folder=dashboard_path, static_url_path='')
else:
    # In development, use local path
    app = Flask(__name__, static_folder=dashboard_path, static_url_path='')
CORS(app)

# Proxy fix for production deployment
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

import tempfile
import os

# Database setup - use temp directory for production environments
if os.environ.get('PRODUCTION', '').lower() == 'true':
    # In production, use a temporary database (data will be lost on each deployment)
    DATABASE = os.path.join(tempfile.gettempdir(), 'wifi_data.db')
else:
    # In development, use local file
    DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../wifi_data.db')

def init_db():
    """Initialize the database with required tables and sample data"""
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Create table for access point data
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS access_points (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ap_name TEXT UNIQUE NOT NULL,
                building TEXT NOT NULL,
                floor INTEGER,
                room_number TEXT,
                latitude REAL,
                longitude REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Update existing table to ensure it has latitude and longitude columns (in case it was created before)
        try:
            cursor.execute("ALTER TABLE access_points ADD COLUMN latitude REAL;")
        except sqlite3.OperationalError:
            # Column already exists
            pass
        
        try:
            cursor.execute("ALTER TABLE access_points ADD COLUMN longitude REAL;")
        except sqlite3.OperationalError:
            # Column already exists
            pass
        
        # Create table for performance metrics
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS performance_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ap_id INTEGER,
                download_speed REAL,
                upload_speed REAL,
                latency REAL,
                packet_loss REAL,
                connected_users INTEGER,
                signal_strength REAL,
                bandwidth_usage REAL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Check if there are any access points already
        cursor.execute("SELECT COUNT(*) FROM access_points")
        count = cursor.fetchone()[0]
        
        # If no access points exist, add sample data
        if count == 0:
            print("Adding sample access points to database...")
            
            # Sample access points with diverse locations
            sample_ap_data = [
                ("Library-WiFi", "Main Library", 2, "Study Area", 37.7749, -122.4194),
                ("Student-Center-WiFi", "Student Center", 1, "Main Hall", 37.7750, -122.4195),
                ("Engineering-WiFi", "Engineering Building", 3, "Lab Wing", 37.7751, -122.4193),
                ("Dormitory-A-WiFi", "Residence Hall A", 2, "Common Room", 37.7748, -122.4196),
                ("Science-Building-WiFi", "Science Building", 1, "Computer Lab", 37.7752, -122.4192),
                ("Admin-Office-WiFi", "Administration", 1, "Main Office", 37.7747, -122.4197),
                ("Cafe-WiFi", "Campus Cafe", 1, "Seating Area", 37.7753, -122.4191),
                ("Fitness-Center-WiFi", "Fitness Center", 1, "Main Area", 37.7746, -122.4198)
            ]
            
            for ap_data in sample_ap_data:
                cursor.execute("""
                    INSERT INTO access_points (ap_name, building, floor, room_number, latitude, longitude)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, ap_data)
                
                # Get the ID of the inserted access point
                ap_id = cursor.lastrowid
                
                # Add sample performance metrics for each access point
                import random
                # Vary the metrics to make them more realistic
                download_speed = round(random.uniform(30, 120), 1)  # More realistic range
                upload_speed = round(random.uniform(10, 35), 1)
                latency = round(random.uniform(10, 60), 1)
                connected_users = random.randint(10, 80)  # More realistic user counts
                signal_strength = round(random.uniform(-85, -35), 1)
                
                cursor.execute("""
                    INSERT INTO performance_metrics (ap_id, download_speed, upload_speed, latency, 
                    packet_loss, connected_users, signal_strength, bandwidth_usage)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (ap_id, download_speed, upload_speed, latency, 
                      round(random.uniform(0, 1.5), 2), connected_users, signal_strength, 
                      round(random.uniform(25, 85), 1)))
        
        conn.commit()
        conn.close()
        print(f"Database initialized successfully at: {DATABASE}")
        print(f"Total access points in database: {count if count > 0 else len(sample_ap_data)}")
    except Exception as e:
        print(f"Error initializing database: {str(e)}")
        traceback.print_exc()

def get_db_connection():
    """Get a database connection with foreign key support enabled"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # This enables column access by name
    return conn


@app.route('/')
def serve_dashboard():
    # Handle serving the dashboard in both dev and prod environments
    import os
    current_dir = os.path.dirname(os.path.abspath(__file__))
    dashboard_path = os.path.join(current_dir, '../dashboard')
    
    try:
        return send_from_directory(dashboard_path, 'index.html')
    except FileNotFoundError:
        # Fallback for different environments
        return send_from_directory('../dashboard', 'index.html')

# Serve static files (CSS, JS, images) from dashboard directory
@app.route('/styles.css')
def serve_css():
    import os
    current_dir = os.path.dirname(os.path.abspath(__file__))
    dashboard_path = os.path.join(current_dir, '../dashboard')
    
    try:
        return send_from_directory(dashboard_path, 'styles.css')
    except FileNotFoundError:
        return send_from_directory('../dashboard', 'styles.css')

@app.route('/script.js')
def serve_js():
    import os
    current_dir = os.path.dirname(os.path.abspath(__file__))
    dashboard_path = os.path.join(current_dir, '../dashboard')
    
    try:
        return send_from_directory(dashboard_path, 'script.js')
    except FileNotFoundError:
        return send_from_directory('../dashboard', 'script.js')

@app.route('/api/')
def api_home():
    return jsonify({"message": "University WiFi Monitoring System API"})

@app.route('/api/test')
def api_test():
    """Test endpoint to verify API is working"""
    return jsonify({
        "status": "success", 
        "message": "API is working properly",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/sample-data')
def api_sample_data():
    """Generate sample access point data for testing"""
    sample_aps = [
        {
            "id": 1,
            "ap_name": "Library-WiFi",
            "building": "Main Library",
            "floor": 2,
            "room_number": "201",
            "latitude": 40.7128,
            "longitude": -74.0060,
            "download_speed": 85.5,
            "upload_speed": 20.3,
            "latency": 12.4,
            "connected_users": 42,
            "signal_strength": -45,
            "timestamp": datetime.now().isoformat(),
            "quality_score": 88.5,
            "status": "Excellent"
        },
        {
            "id": 2,
            "ap_name": "Student-Center-WiFi",
            "building": "Student Center",
            "floor": 1,
            "room_number": "Main Hall",
            "latitude": 40.7135,
            "longitude": -74.0072,
            "download_speed": 65.2,
            "upload_speed": 15.8,
            "latency": 18.7,
            "connected_users": 87,
            "signal_strength": -52,
            "timestamp": datetime.now().isoformat(),
            "quality_score": 72.3,
            "status": "Good"
        }
    ]
    return jsonify(sample_aps)

@app.route('/api/access-points', methods=['GET'])
def get_access_points():
    """Get all access points with their current status"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT ap.*, pm.download_speed, pm.upload_speed, pm.latency, 
                   pm.connected_users, pm.signal_strength, pm.timestamp
            FROM access_points ap
            LEFT JOIN (
                SELECT ap_id, download_speed, upload_speed, latency, 
                       connected_users, signal_strength, timestamp
                FROM performance_metrics
                WHERE (ap_id, timestamp) IN (
                    SELECT ap_id, MAX(timestamp)
                    FROM performance_metrics
                    GROUP BY ap_id
                )
            ) pm ON ap.id = pm.ap_id
        ''')
        
        rows = cursor.fetchall()
        
        access_points = []
        for row in rows:
            ap_dict = dict(row)
            # Calculate quality score
            ap_dict['quality_score'] = calculate_quality_score(ap_dict)
            ap_dict['status'] = get_status_from_score(ap_dict['quality_score'])
            access_points.append(ap_dict)
        
        conn.close()
        return jsonify(access_points)
    except Exception as e:
        print(f"Error fetching access points: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': 'Failed to fetch access points'}), 500

@app.route('/api/access-points/<int:ap_id>', methods=['GET'])
def get_access_point(ap_id):
    """Get specific access point details"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT ap.*, pm.download_speed, pm.upload_speed, pm.latency, 
                   pm.connected_users, pm.signal_strength, pm.timestamp
            FROM access_points ap
            LEFT JOIN (
                SELECT ap_id, download_speed, upload_speed, latency, 
                       connected_users, signal_strength, timestamp
                FROM performance_metrics
                WHERE ap_id = ?
                ORDER BY timestamp DESC
                LIMIT 1
            ) pm ON ap.id = pm.ap_id
            WHERE ap.id = ?
        ''', (ap_id, ap_id))
        
        row = cursor.fetchone()
        if row:
            ap_dict = dict(row)
            ap_dict['quality_score'] = calculate_quality_score(ap_dict)
            ap_dict['status'] = get_status_from_score(ap_dict['quality_score'])
            conn.close()
            return jsonify(ap_dict)
        else:
            conn.close()
            return jsonify({'error': 'Access point not found'}), 404
    except Exception as e:
        print(f"Error fetching access point: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': 'Failed to fetch access point'}), 500

@app.route('/api/performance-metrics', methods=['POST'])
def submit_performance_metrics():
    """Submit performance metrics from access points or client devices"""
    try:
        data = request.json
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # First, get or create the access point
        cursor.execute('''
            INSERT OR IGNORE INTO access_points (ap_name, building, floor, room_number, latitude, longitude)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            data['ap_name'], 
            data.get('building', ''), 
            data.get('floor', 0), 
            data.get('room_number', ''),
            data.get('latitude'),
            data.get('longitude')
        ))
        
        # Get the access point ID
        cursor.execute('SELECT id FROM access_points WHERE ap_name = ?', (data['ap_name'],))
        result = cursor.fetchone()
        if result is None:
            conn.close()
            return jsonify({'error': 'Failed to get access point ID'}), 500
        ap_id = result[0]
        
        # Insert performance metrics
        cursor.execute('''
            INSERT INTO performance_metrics 
            (ap_id, download_speed, upload_speed, latency, packet_loss, 
             connected_users, signal_strength, bandwidth_usage)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            ap_id,
            data.get('download_speed'),
            data.get('upload_speed'),
            data.get('latency'),
            data.get('packet_loss'),
            data.get('connected_users'),
            data.get('signal_strength'),
            data.get('bandwidth_usage')
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({'message': 'Metrics submitted successfully'}), 201
    except Exception as e:
        print(f"Error submitting performance metrics: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': 'Failed to submit metrics'}), 500

@app.route('/api/recommendations', methods=['GET'])
def get_recommendations():
    """Get recommended access points near user's location"""
    try:
        lat = request.args.get('latitude', type=float)
        lon = request.args.get('longitude', type=float)
        radius = request.args.get('radius', default=1000, type=int)  # in meters
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # For simplicity, we'll return top 5 access points by quality score
        # In a real implementation, we'd calculate distance using lat/lon
        cursor.execute('''
            SELECT ap.*, pm.download_speed, pm.upload_speed, pm.latency, 
                   pm.connected_users, pm.signal_strength, pm.timestamp
            FROM access_points ap
            LEFT JOIN (
                SELECT ap_id, download_speed, upload_speed, latency, 
                       connected_users, signal_strength, timestamp
                FROM performance_metrics
                WHERE (ap_id, timestamp) IN (
                    SELECT ap_id, MAX(timestamp)
                    FROM performance_metrics
                    GROUP BY ap_id
                )
            ) pm ON ap.id = pm.ap_id
            ORDER BY pm.download_speed DESC
            LIMIT 5
        ''')
        
        rows = cursor.fetchall()
        
        recommendations = []
        for row in rows:
            ap_dict = dict(row)
            ap_dict['quality_score'] = calculate_quality_score(ap_dict)
            ap_dict['status'] = get_status_from_score(ap_dict['quality_score'])
            recommendations.append(ap_dict)
        
        conn.close()
        return jsonify(recommendations)
    except Exception as e:
        print(f"Error fetching recommendations: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': 'Failed to fetch recommendations'}), 500

def calculate_quality_score(data):
    """Calculate quality score based on performance metrics with user density adjustment"""
    download_speed = data.get('download_speed') or 0
    upload_speed = data.get('upload_speed') or 0
    latency = data.get('latency') or float('inf')
    connected_users = data.get('connected_users') or 0
    signal_strength = data.get('signal_strength') or -80  # Default signal strength
        
    # Normalize values to 0-100 scale
    norm_download = min(download_speed / 100.0 * 100, 100)  # Assuming 100 Mbps max
    norm_upload = min(upload_speed / 50.0 * 100, 100)      # Assuming 50 Mbps max upload
    norm_latency = max((1000 - min(latency * 1000, 1000)) / 10, 0)  # Convert to ms, invert
        
    # Calculate user density impact (more users = lower quality)
    # Adjusted to be more realistic - moderate impact from users
    norm_users = max(100 - (min(connected_users, 50) * 1.5), 0)  # Max 50 users = 25 point reduction
        
    # Calculate signal strength contribution (stronger signal = better quality)
    # Signal strength range: -30dBm (excellent) to -90dBm (poor)
    norm_signal = max(0, min(100, 130 + signal_strength))  # Convert -30 to -90 range to 100 to 40
        
    # Weighted score calculation with signal strength factor
    quality_score = (
        0.35 * norm_download +
        0.15 * norm_upload +
        0.2 * norm_latency +
        0.2 * norm_users +
        0.1 * norm_signal  # Include signal strength in the calculation
    )
        
    return round(quality_score, 2)

def get_status_from_score(score):
    """Convert quality score to status"""
    if score >= 80:
        return "Excellent"
    elif score >= 60:
        return "Good"
    elif score >= 40:
        return "Medium"
    else:
        return "Poor"

# Initialize data collector
collector = None

@app.route('/api/start-collection', methods=['POST'])
def start_data_collection():
    """Start real-time data collection"""
    global collector
    try:
        if collector is None or not collector.is_collecting:
            # Use the current request URL as the API base
            api_base_url = request.url_root.rstrip('/')
            # Construct the correct API base URL
            # Remove the specific endpoint path to get the base URL
            if '/api/start-collection' in api_base_url:
                api_base_url = api_base_url.replace('/api/start-collection', '')
            elif '/api/' in api_base_url:
                api_base_url = api_base_url.split('/api')[0]
            elif api_base_url.endswith('/api'):
                api_base_url = api_base_url[:-4]
            
            collector = WiFiDataCollector(api_base_url=api_base_url)
            collection_interval = request.json.get('interval', 60)  # Default to 60 seconds
            collector.start_collection(interval=collection_interval)
            return jsonify({
                'message': 'Data collection started successfully',
                'interval': collection_interval
            }), 200
        else:
            return jsonify({'message': 'Data collection is already running'}), 400
    except Exception as e:
        print(f"Error starting data collection: {str(e)}")
        return jsonify({'error': 'Failed to start data collection'}), 500

@app.route('/api/stop-collection', methods=['POST'])
def stop_data_collection():
    """Stop real-time data collection"""
    global collector
    try:
        if collector and collector.is_collecting:
            collector.stop_collection()
            collector = None
            return jsonify({'message': 'Data collection stopped successfully'}), 200
        else:
            return jsonify({'message': 'Data collection is not running'}), 400
    except Exception as e:
        print(f"Error stopping data collection: {str(e)}")
        return jsonify({'error': 'Failed to stop data collection'}), 500

@app.route('/api/collection-status', methods=['GET'])
def get_collection_status():
    """Get current data collection status"""
    global collector
    try:
        is_running = collector is not None and collector.is_collecting
        return jsonify({
            'is_collecting': is_running,
            'message': 'Running' if is_running else 'Not running'
        })
    except Exception as e:
        print(f"Error getting collection status: {str(e)}")
        return jsonify({'error': 'Failed to get collection status'}), 500

# Initialize database when the module is loaded
try:
    init_db()
    print("Database initialized for University WiFi Monitoring System")
    
    # In production, ensure we have some initial data
    if os.environ.get('PRODUCTION', '').lower() == 'true':
        print("Initializing with sample data in production...")
        # Sample data will be added during init_db() if database is empty
    else:
        print("Running in development mode")
        
except Exception as e:
    print(f"Failed to initialize system: {str(e)}")
    traceback.print_exc()

if __name__ == '__main__':
    import os
    # Check if running in production environment
    is_production = os.environ.get('PRODUCTION', '').lower() == 'true'
    
    if is_production:
        print("Starting University WiFi Monitoring System (Production)...")
        # In production, use gunicorn which handles the server
        app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
    else:
        print("Starting University WiFi Monitoring System (Development)...")
        app.run(debug=True, host='0.0.0.0', port=5000)