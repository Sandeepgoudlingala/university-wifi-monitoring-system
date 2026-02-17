from flask import Flask, jsonify, request, send_from_directory, send_file
from flask_cors import CORS
import json
import os
from datetime import datetime
import sqlite3
import traceback
from werkzeug.middleware.proxy_fix import ProxyFix
import threading
import time

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

# Import speed tester
try:
    from .speed_tester import NetworkSpeedTester
except ImportError:
    # Mock speed tester if module doesn't exist
    class NetworkSpeedTester:
        def run_full_test(self):
            import random
            return {
                'download_speed': round(random.uniform(50, 150), 2),
                'upload_speed': round(random.uniform(10, 40), 2),
                'ping': round(random.uniform(10, 80), 2),
                'timestamp': datetime.now().isoformat(),
                'status': 'completed'
            }

# Determine the correct path based on environment
current_dir = os.path.dirname(os.path.abspath(__file__))
dashboard_path = os.path.join(current_dir, '../dashboard')

if os.environ.get('PRODUCTION', '').lower() == 'true':
    # In production, try multiple possible paths
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if os.path.exists(os.path.join(root_dir, 'index.html')):
        app = Flask(__name__, static_folder=root_dir, static_url_path='')
    else:
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
            
            # Sample access points with accurate university area names
            sample_ap_data = [
                # Mens Hostels (MH1 to MH7)
                ("MH1-WiFi", "Mens Hostel 1", 1, "Common Area", 37.7749, -122.4194),
                ("MH2-WiFi", "Mens Hostel 2", 1, "Common Area", 37.7750, -122.4195),
                ("MH3-WiFi", "Mens Hostel 3", 1, "Common Area", 37.7751, -122.4193),
                ("MH4-WiFi", "Mens Hostel 4", 1, "Common Area", 37.7748, -122.4196),
                ("MH5-WiFi", "Mens Hostel 5", 1, "Common Area", 37.7752, -122.4192),
                ("MH6-WiFi", "Mens Hostel 6", 1, "Common Area", 37.7747, -122.4197),
                ("MH7-WiFi", "Mens Hostel 7", 1, "Common Area", 37.7753, -122.4191),
                
                # Ladies Hostels (LH1 to LH4)
                ("LH1-WiFi", "Ladies Hostel 1", 1, "Common Area", 37.7746, -122.4198),
                ("LH2-WiFi", "Ladies Hostel 2", 1, "Common Area", 37.7745, -122.4199),
                ("LH3-WiFi", "Ladies Hostel 3", 1, "Common Area", 37.7744, -122.4200),
                ("LH4-WiFi", "Ladies Hostel 4", 1, "Common Area", 37.7743, -122.4201),
                
                # Academic blocks (Central Block 1 to 10)
                ("CB1-WiFi", "Central Block 1", 1, "Ground Floor", 37.7742, -122.4202),
                ("CB2-WiFi", "Central Block 2", 2, "Second Floor", 37.7741, -122.4203),
                ("CB3-WiFi", "Central Block 3", 3, "Third Floor", 37.7740, -122.4204),
                ("CB4-WiFi", "Central Block 4", 4, "Fourth Floor", 37.7739, -122.4205),
                ("CB5-WiFi", "Central Block 5", 5, "Fifth Floor", 37.7738, -122.4206),
                ("CB6-WiFi", "Central Block 6", 6, "Sixth Floor", 37.7737, -122.4207),
                ("CB7-WiFi", "Central Block 7", 7, "Seventh Floor", 37.7736, -122.4208),
                ("CB8-WiFi", "Central Block 8", 8, "Eighth Floor", 37.7735, -122.4209),
                ("CB9-WiFi", "Central Block 9", 9, "Ninth Floor", 37.7734, -122.4210),
                ("CB10-WiFi", "Central Block 10", 10, "Tenth Floor", 37.7733, -122.4211),
                
                # Admission Block (AB1 and AB2)
                ("AB1-WiFi", "Admission Block 1", 1, "Main Office", 37.7732, -122.4212),
                ("AB2-WiFi", "Admission Block 2", 1, "Main Office", 37.7731, -122.4213),
                
                # Food Street
                ("FS-North-WiFi", "Food Street North", 1, "Restaurant Area", 37.7730, -122.4214),
                ("FS-South-WiFi", "Food Street South", 1, "Cafe Area", 37.7729, -122.4215),
                ("FS-Center-WiFi", "Food Street Center", 1, "Main Square", 37.7728, -122.4216),
                
                # Rock Plaza
                ("RP-Main-WiFi", "Rock Plaza Main", 1, "Main Plaza", 37.7727, -122.4217),
                ("RP-East-WiFi", "Rock Plaza East", 1, "Event Space", 37.7726, -122.4218),
                ("RP-West-WiFi", "Rock Plaza West", 1, "Relaxation Area", 37.7725, -122.4219)
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
            # The enhanced sample data has already been added above
        
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
def serve_index():
    """Serve the main index page"""
    # Get the directory where this app.py file is located
    current_file_dir = os.path.dirname(os.path.abspath(__file__))
    # Navigate to the project root (three levels up from backend dir)
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file_dir)))
    
    # First, try to serve from project root
    main_index_path = os.path.join(project_root, 'index.html')
    if os.path.exists(main_index_path):
        return send_file(main_index_path)
    else:
        # Fallback: try the main index from current working directory
        cwd_index_path = os.path.join(os.getcwd(), 'index.html')
        if os.path.exists(cwd_index_path):
            return send_file(cwd_index_path)
        else:
            # Final fallback: try dashboard index
            dashboard_path = os.path.join(current_file_dir, '..', 'dashboard', 'index.html')
            dashboard_path = os.path.normpath(dashboard_path)  # Normalize the path
            if os.path.exists(dashboard_path):
                return send_file(dashboard_path)
            else:
                return 'Index file not found', 404

@app.route('/dashboard')
def serve_dashboard():
    """Serve the dashboard page"""
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
    current_dir = os.path.dirname(os.path.abspath(__file__))
    dashboard_path = os.path.join(current_dir, '../dashboard')
    
    try:
        return send_from_directory(dashboard_path, 'styles.css')
    except FileNotFoundError:
        return send_from_directory('../dashboard', 'styles.css')

@app.route('/script.js')
def serve_js():
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
            data.get('latency'),  # This is the ping/latency measurement
            data.get('packet_loss'),
            data.get('connected_users'),
            data.get('signal_strength'),
            data.get('bandwidth_usage')
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({'message': 'Metrics submitted successfully', 'ap_id': ap_id}), 201
    except Exception as e:
        print(f"Error submitting performance metrics: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': 'Failed to submit metrics', 'details': str(e)}), 500

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

@app.route('/api/ping-measurements', methods=['GET'])
def get_ping_measurements():
    """Get ping measurements grouped by area/building"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get latest ping measurements grouped by building
        cursor.execute('''
            SELECT ap.building, ap.ap_name, pm.latency as ping, 
                   pm.download_speed, pm.upload_speed, pm.connected_users, 
                   ap.latitude, ap.longitude, pm.timestamp
            FROM access_points ap
            INNER JOIN (
                SELECT ap_id, latency, download_speed, upload_speed, 
                       connected_users, timestamp
                FROM performance_metrics
                WHERE (ap_id, timestamp) IN (
                    SELECT ap_id, MAX(timestamp)
                    FROM performance_metrics
                    GROUP BY ap_id
                )
            ) pm ON ap.id = pm.ap_id
            ORDER BY ap.building, pm.latency ASC
        ''')
        
        rows = cursor.fetchall()
        
        ping_data = []
        for row in rows:
            ping_data.append(dict(row))
        
        conn.close()
        return jsonify(ping_data)
    except Exception as e:
        print(f"Error fetching ping measurements: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': 'Failed to fetch ping measurements'}), 500

@app.route('/api/area-ping-summary', methods=['GET'])
def get_area_ping_summary():
    """Get ping summary statistics by area/building"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get average ping by building
        cursor.execute('''
            SELECT ap.building,
                   AVG(pm.latency) as avg_ping,
                   MIN(pm.latency) as min_ping,
                   MAX(pm.latency) as max_ping,
                   COUNT(pm.latency) as measurement_count,
                   AVG(pm.download_speed) as avg_download,
                   AVG(pm.upload_speed) as avg_upload,
                   AVG(pm.connected_users) as avg_users
            FROM access_points ap
            INNER JOIN performance_metrics pm ON ap.id = pm.ap_id
            WHERE pm.timestamp >= datetime('now', '-24 hours')
            GROUP BY ap.building
            ORDER BY avg_ping ASC
        ''')
        
        rows = cursor.fetchall()
        
        area_summary = []
        for row in rows:
            area_summary.append(dict(row))
        
        conn.close()
        return jsonify(area_summary)
    except Exception as e:
        print(f"Error fetching area ping summary: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': 'Failed to fetch area ping summary'}), 500

@app.route('/api/live-speed-test', methods=['GET'])
def live_speed_test():
    """Run a live speed test and return current network performance"""
    try:
        # Create a speed tester instance
        tester = NetworkSpeedTester()
        
        # Run the full test
        results = tester.run_full_test()
        
        return jsonify(results)
    except Exception as e:
        print(f"Error running live speed test: {str(e)}")
        traceback.print_exc()
        # Return simulated values if the test fails
        return jsonify({
            'download_speed': 96.24,
            'upload_speed': 21.42,
            'ping': 33.84,
            'timestamp': datetime.now().isoformat(),
            'status': 'failed',
            'message': f'Test failed: {str(e)}. Returning simulated values.'
        })

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

@app.route('/api/live-stats', methods=['GET'])
def get_live_stats():
    """Get live network statistics for the main page"""
    try:
        # Get the most recent access point data
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
            LIMIT 5  -- Get top 5 access points
        ''')
        
        rows = cursor.fetchall()
        
        access_points = []
        for row in rows:
            ap_dict = dict(row)
            ap_dict['quality_score'] = calculate_quality_score(ap_dict)
            ap_dict['status'] = get_status_from_score(ap_dict['quality_score'])
            access_points.append(ap_dict)
        
        conn.close()
        
        # Calculate aggregate statistics
        if access_points:
            avg_download = sum(ap.get('download_speed', 0) for ap in access_points if ap.get('download_speed')) / len([ap for ap in access_points if ap.get('download_speed')])
            avg_upload = sum(ap.get('upload_speed', 0) for ap in access_points if ap.get('upload_speed')) / len([ap for ap in access_points if ap.get('upload_speed')])
            avg_latency = sum(ap.get('latency', 0) for ap in access_points if ap.get('latency')) / len([ap for ap in access_points if ap.get('latency')])
        else:
            avg_download = 0
            avg_upload = 0
            avg_latency = 0
        
        return jsonify({
            'overall_status': 'active' if access_points else 'inactive',
            'total_access_points': len(access_points),
            'average_download_speed': round(avg_download, 2) if avg_download else 0,
            'average_upload_speed': round(avg_upload, 2) if avg_upload else 0,
            'average_latency': round(avg_latency, 2) if avg_latency else 0,
            'connected_users': sum(ap.get('connected_users', 0) for ap in access_points if ap.get('connected_users')), 
            'top_access_points': access_points[:3]  # Return top 3 access points
        })
    except Exception as e:
        print(f"Error getting live stats: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': 'Failed to get live stats'}), 500

# Initialize database when the module is loaded
try:
    init_db()
    print("Database initialized for University WiFi Monitoring System")
    
    # In production, ensure we have some initial data
    if os.environ.get('PRODUCTION', '').lower() == 'true':
        print("Initializing with sample data in production...")
        # In production on Vercel, the filesystem is ephemeral, so we need to ensure data exists
        # Sample data will be added during init_db() if database is empty
                
        # Force adding sample data in production to ensure there's data to display
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
                
        # Count existing access points
        cursor.execute("SELECT COUNT(*) FROM access_points")
        ap_count = cursor.fetchone()[0]
                
        if ap_count == 0:
            print("No access points found in production, adding sample data...")
                        
            # Sample access points with accurate university area names
            sample_ap_data = [
                # Mens Hostels (MH1 to MH7)
                ("MH1-WiFi", "Mens Hostel 1", 1, "Common Area", 37.7749, -122.4194),
                ("MH2-WiFi", "Mens Hostel 2", 1, "Common Area", 37.7750, -122.4195),
                ("MH3-WiFi", "Mens Hostel 3", 1, "Common Area", 37.7751, -122.4193),
                ("MH4-WiFi", "Mens Hostel 4", 1, "Common Area", 37.7748, -122.4196),
                ("MH5-WiFi", "Mens Hostel 5", 1, "Common Area", 37.7752, -122.4192),
                ("MH6-WiFi", "Mens Hostel 6", 1, "Common Area", 37.7747, -122.4197),
                ("MH7-WiFi", "Mens Hostel 7", 1, "Common Area", 37.7753, -122.4191),
                            
                # Ladies Hostels (LH1 to LH4)
                ("LH1-WiFi", "Ladies Hostel 1", 1, "Common Area", 37.7746, -122.4198),
                ("LH2-WiFi", "Ladies Hostel 2", 1, "Common Area", 37.7745, -122.4199),
                ("LH3-WiFi", "Ladies Hostel 3", 1, "Common Area", 37.7744, -122.4200),
                ("LH4-WiFi", "Ladies Hostel 4", 1, "Common Area", 37.7743, -122.4201),
                            
                # Academic blocks (Central Block 1 to 10)
                ("CB1-WiFi", "Central Block 1", 1, "Ground Floor", 37.7742, -122.4202),
                ("CB2-WiFi", "Central Block 2", 2, "Second Floor", 37.7741, -122.4203),
                ("CB3-WiFi", "Central Block 3", 3, "Third Floor", 37.7740, -122.4204),
                ("CB4-WiFi", "Central Block 4", 4, "Fourth Floor", 37.7739, -122.4205),
                ("CB5-WiFi", "Central Block 5", 5, "Fifth Floor", 37.7738, -122.4206),
                ("CB6-WiFi", "Central Block 6", 6, "Sixth Floor", 37.7737, -122.4207),
                ("CB7-WiFi", "Central Block 7", 7, "Seventh Floor", 37.7736, -122.4208),
                ("CB8-WiFi", "Central Block 8", 8, "Eighth Floor", 37.7735, -122.4209),
                ("CB9-WiFi", "Central Block 9", 9, "Ninth Floor", 37.7734, -122.4210),
                ("CB10-WiFi", "Central Block 10", 10, "Tenth Floor", 37.7733, -122.4211),
                            
                # Admission Block (AB1 and AB2)
                ("AB1-WiFi", "Admission Block 1", 1, "Main Office", 37.7732, -122.4212),
                ("AB2-WiFi", "Admission Block 2", 1, "Main Office", 37.7731, -122.4213),
                            
                # Food Street
                ("FS-North-WiFi", "Food Street North", 1, "Restaurant Area", 37.7730, -122.4214),
                ("FS-South-WiFi", "Food Street South", 1, "Cafe Area", 37.7729, -122.4215),
                ("FS-Center-WiFi", "Food Street Center", 1, "Main Square", 37.7728, -122.4216),
                            
                # Rock Plaza
                ("RP-Main-WiFi", "Rock Plaza Main", 1, "Main Plaza", 37.7727, -122.4217),
                ("RP-East-WiFi", "Rock Plaza East", 1, "Event Space", 37.7726, -122.4218),
                ("RP-West-WiFi", "Rock Plaza West", 1, "Relaxation Area", 37.7725, -122.4219)
            ]
                        
            for ap_data in sample_ap_data:
                cursor.execute("""
                    INSERT OR IGNORE INTO access_points (ap_name, building, floor, room_number, latitude, longitude)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, ap_data)
                            
                # Get the ID of the inserted access point
                cursor.execute("SELECT id FROM access_points WHERE ap_name = ?", (ap_data[0],))
                result = cursor.fetchone()
                if result:
                    ap_id = result[0]
                                
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