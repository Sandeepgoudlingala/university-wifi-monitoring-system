from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import json
import os
from datetime import datetime
import sqlite3
import traceback
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__, static_folder='../../src/dashboard', static_url_path='/static')
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
    DATABASE = 'wifi_data.db'

def init_db():
    """Initialize the database with required tables"""
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
        
        conn.commit()
        conn.close()
        print(f"Database initialized successfully at: {DATABASE}")
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
    return send_from_directory('../../src/dashboard', 'index.html')

# Serve static files (CSS, JS, images) from dashboard directory
@app.route('/styles.css')
def serve_css():
    return send_from_directory('../../src/dashboard', 'styles.css')

@app.route('/script.js')
def serve_js():
    return send_from_directory('../../src/dashboard', 'script.js')

@app.route('/api/')
def api_home():
    return jsonify({"message": "University WiFi Monitoring System API"})

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

# Initialize database when the module is loaded
try:
    init_db()
    print("Database initialized for University WiFi Monitoring System")
except Exception as e:
    print(f"Failed to initialize database: {str(e)}")
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