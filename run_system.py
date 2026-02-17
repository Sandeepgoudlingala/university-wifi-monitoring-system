#!/usr/bin/env python3
"""
University WiFi Quality Monitoring and Smart Location Recommendation System
Main Entry Point
"""

import os
import sys
import threading
import time
import subprocess
import webbrowser
from datetime import datetime

def run_backend():
    """Run the Flask backend server"""
    from src.backend.app import app
    print("Starting backend server...")
    app.run(debug=False, host='0.0.0.0', port=5000)

def run_collector_simulation():
    """Run the data collector in simulation mode"""
    from src.data_collection.collector import WiFiDataCollector
    
    collector = WiFiDataCollector()
    
    # Simulate collecting data for various access points with realistic coordinates
    access_points = [
        # Central Block
        {"name": "CENTRAL_BLOCK_01", "building": "Central Block", "floor": 1, "room": "Main Lobby", "lat": 40.7125, "lng": -74.0070},
        {"name": "CENTRAL_BLOCK_02", "building": "Central Block", "floor": 2, "room": "Meeting Room", "lat": 40.7126, "lng": -74.0071},
        {"name": "CENTRAL_BLOCK_03", "building": "Central Block", "floor": 3, "room": "Conference Hall", "lat": 40.7127, "lng": -74.0072},
        
        # Administration Blocks
        {"name": "ADMIN_BLOCK_01", "building": "Administration Block 2", "floor": 1, "room": "Reception", "lat": 40.7115, "lng": -74.0060},
        {"name": "ADMIN_BLOCK_02", "building": "Administration Block 2", "floor": 2, "room": "Office Wing", "lat": 40.7116, "lng": -74.0061},
        
        # Food Street
        {"name": "FOOD_STREET_01", "building": "Food Street", "floor": 1, "room": "Main Area", "lat": 40.7140, "lng": -74.0090},
        {"name": "FOOD_STREET_02", "building": "Food Street", "floor": 1, "room": "North Side", "lat": 40.7141, "lng": -74.0089},
        {"name": "FOOD_STREET_03", "building": "Food Street", "floor": 1, "room": "South Side", "lat": 40.7139, "lng": -74.0091},
        
        # Rock Plaza
        {"name": "ROCK_PLAZA_01", "building": "Rock Plaza", "floor": 1, "room": "Main Plaza", "lat": 40.7150, "lng": -74.0075},
        {"name": "ROCK_PLAZA_02", "building": "Rock Plaza", "floor": 1, "room": "Event Space", "lat": 40.7151, "lng": -74.0076},
        
        # Hostels (MH1 to MH6)
        {"name": "HOSTEL_MH1_01", "building": "Hostel MH1", "floor": 1, "room": "Common Area", "lat": 40.7090, "lng": -74.0080},
        {"name": "HOSTEL_MH1_02", "building": "Hostel MH1", "floor": 2, "room": "Study Lounge", "lat": 40.7091, "lng": -74.0081},
        {"name": "HOSTEL_MH2_01", "building": "Hostel MH2", "floor": 1, "room": "Common Area", "lat": 40.7095, "lng": -74.0080},
        {"name": "HOSTEL_MH3_01", "building": "Hostel MH3", "floor": 1, "room": "Common Area", "lat": 40.7100, "lng": -74.0080},
        {"name": "HOSTEL_MH4_01", "building": "Hostel MH4", "floor": 1, "room": "Common Area", "lat": 40.7105, "lng": -74.0080},
        {"name": "HOSTEL_MH5_01", "building": "Hostel MH5", "floor": 1, "room": "Common Area", "lat": 40.7110, "lng": -74.0080},
        {"name": "HOSTEL_MH6_01", "building": "Hostel MH6", "floor": 1, "room": "Common Area", "lat": 40.7115, "lng": -74.0080},
        
        # Ladies Hostels (LH1 to LH4)
        {"name": "LH1_01", "building": "Ladies Hostel 1", "floor": 1, "room": "Common Area", "lat": 40.7130, "lng": -74.0060},
        {"name": "LH2_01", "building": "Ladies Hostel 2", "floor": 1, "room": "Common Area", "lat": 40.7135, "lng": -74.0060},
        {"name": "LH3_01", "building": "Ladies Hostel 3", "floor": 1, "room": "Common Area", "lat": 40.7140, "lng": -74.0060},
        {"name": "LH4_01", "building": "Ladies Hostel 4", "floor": 1, "room": "Common Area", "lat": 40.7145, "lng": -74.0060},
        
        # Original locations for continuity
        {"name": "LIBRARY_AP_01", "building": "Library", "floor": 1, "room": "Main Hall", "lat": 40.7120, "lng": -74.0080},
        {"name": "LIBRARY_AP_02", "building": "Library", "floor": 2, "room": "Study Room", "lat": 40.7122, "lng": -74.0082},
        {"name": "ENGINEERING_AP_01", "building": "Engineering", "floor": 1, "room": "Lab A", "lat": 40.7130, "lng": -74.0070},
        {"name": "ENGINEERING_AP_02", "building": "Engineering", "floor": 2, "room": "Lab B", "lat": 40.7132, "lng": -74.0072},
        {"name": "CAFETERIA_AP_01", "building": "Cafeteria", "floor": 1, "room": "Main Area", "lat": 40.7140, "lng": -74.0090},
    ]
    
    print("Starting data collection simulation...")
    while True:
        for ap_info in access_points:
            try:
                # Collect metrics
                # Set the access point name for this specific AP
                collector.access_point_name = ap_info["name"]
                
                # Get network stats and update with location info
                metrics = collector.get_network_stats()
                # Override with specific location data from our access point list
                metrics.update({
                    'ap_name': ap_info["name"],
                    'building': ap_info["building"],
                    'floor': ap_info["floor"],
                    'room_number': ap_info["room"],
                    'latitude': ap_info["lat"],
                    'longitude': ap_info["lng"]
                })
                
                # Submit to server
                success = collector.submit_metrics(metrics)
                if success:
                    print(f"Sent metrics for {ap_info['name']}")
                
                # Wait a bit between APs
                time.sleep(2)
                
            except KeyboardInterrupt:
                print("\nData collection stopped by user.")
                break
            except Exception as e:
                print(f"Error collecting data for {ap_info['name']}: {e}")
                time.sleep(5)  # Wait before retrying

def run_analyzer():
    """Run periodic analysis"""
    from src.analytics.analyzer import WiFiAnalyzer
    
    # Create database path relative to the backend directory
    import os
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'wifi_data.db')
    analyzer = WiFiAnalyzer(db_path=db_path)
    
    print("Starting periodic analysis...")
    while True:
        try:
            # Generate report every 10 minutes
            report = analyzer.generate_report(days_back=1)
            print(f"Analysis completed at {datetime.now()}")
            
            # Wait 10 minutes
            time.sleep(600)
            
        except KeyboardInterrupt:
            print("\nAnalyzer stopped by user.")
            break
        except Exception as e:
            print(f"Error in analyzer: {e}")
            time.sleep(60)  # Wait before retrying

def open_dashboard():
    """Open the dashboard in the default browser"""
    time.sleep(3)  # Wait a bit for the server to start
    webbrowser.open('http://localhost:5000')

def main():
    # Check if running in production environment
    is_production = os.environ.get('PRODUCTION', '').lower() == 'true'
    
    print("="*60)
    print(" UNIVERSITY WIFI QUALITY MONITORING SYSTEM ")
    print("="*60)
    
    if is_production:
        print("Running in PRODUCTION mode...")
        print("Starting University WiFi Quality Monitoring System (Production)...")
        print("Components to be launched:")
        print("1. Backend API Server (Production)")
        print("-"*60)
        
        # In production, only start the backend server
        run_backend()
    else:
        print("Starting University WiFi Quality Monitoring System (Development)...")
        print("Components to be launched:")
        print("1. Backend API Server (Port 5000)")
        print("2. Data Collection Module")
        print("3. Analytics Engine")
        print("4. Dashboard (will open in browser)")
        print("-"*60)
        
        # Start backend server in a separate thread
        backend_thread = threading.Thread(target=run_backend, daemon=True)
        backend_thread.start()
        
        # Start data collector in a separate thread
        collector_thread = threading.Thread(target=run_collector_simulation, daemon=True)
        collector_thread.start()
        
        # Start analyzer in a separate thread
        analyzer_thread = threading.Thread(target=run_analyzer, daemon=True)
        analyzer_thread.start()
        
        # Open dashboard in browser
        dashboard_thread = threading.Thread(target=open_dashboard, daemon=True)
        dashboard_thread.start()
        
        print("System is running! Access the dashboard at: http://localhost:5000")
        print("Press Ctrl+C to stop the system.")
        
        try:
            # Keep the main thread alive
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down University WiFi Quality Monitoring System...")
            print("Goodbye!")

if __name__ == "__main__":
    # Change to the project directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    main()