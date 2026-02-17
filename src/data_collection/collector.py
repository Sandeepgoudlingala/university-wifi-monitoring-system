import time
import random
import threading
import requests
from datetime import datetime
import platform
import json


class WiFiDataCollector:
    """
    Real-time WiFi data collector that gathers simulated performance metrics
    Designed to work reliably in cloud environments where system-level access is limited
    """
    
    def __init__(self, api_base_url="http://localhost:5000", ap_name=None):
        self.api_base_url = api_base_url
        self.is_collecting = False
        self.collection_thread = None
        self.access_point_name = ap_name or f"{platform.node()}-WiFi" if platform.node() != 'unknown' else "Cloud-AP-{random.randint(1000, 9999)}"
        
    def get_network_stats(self):
        """
        Generate realistic network statistics for simulation
        In a real implementation, this would interface with actual WiFi monitoring tools
        """
        # Generate realistic WiFi metrics based on time of day and simulated conditions
        hour = datetime.now().hour
        
        # Vary metrics based on time of day (busier during business hours)
        base_users = 10 if 22 <= hour or hour <= 6 else 30  # Fewer users at night
        connected_users = base_users + random.randint(0, 40)
        
        # Simulate realistic download/upload speeds
        download_speed = round(random.uniform(30, 120), 2)  # Mbps
        upload_speed = round(random.uniform(10, 35), 2)     # Mbps
        
        # Latency varies with number of connected users
        base_latency = 15 if connected_users < 20 else (25 if connected_users < 50 else 45)
        latency = round(base_latency + random.uniform(0, 20), 2)
        
        # Signal strength varies
        signal_strength = round(random.uniform(-80, -35), 1)  # dBm
        
        # Packet loss
        packet_loss = round(random.uniform(0, 1.5), 2)       # %
        
        # Bandwidth usage
        bandwidth_usage = round(min(95, 20 + (connected_users * 1.2)), 1)  # %
        
        return {
            'ap_name': self.access_point_name,
            'building': random.choice(['Main Library', 'Student Center', 'Engineering Building', 'Science Building', 'Administration', 'Dormitory A', 'Dormitory B', 'Academic Hall']),
            'floor': random.randint(1, 4),
            'room_number': f"Room {random.randint(100, 499)}",
            'latitude': round(37.7749 + random.uniform(-0.1, 0.1), 6),  # San Francisco area as example
            'longitude': round(-122.4194 + random.uniform(-0.1, 0.1), 6),
            'download_speed': download_speed,
            'upload_speed': upload_speed,
            'latency': latency,
            'packet_loss': packet_loss,
            'connected_users': connected_users,
            'signal_strength': signal_strength,
            'bandwidth_usage': bandwidth_usage,
            'timestamp': datetime.now().isoformat()
        }
    
    def submit_metrics(self, metrics):
        """
        Submit collected metrics to the API
        """
        try:
            # For deployed environment, use the actual deployed URL
            api_endpoint = f"{self.api_base_url}/api/performance-metrics"
            
            # For Vercel deployments, sometimes the URL needs to be constructed differently
            if 'vercel.app' in self.api_base_url or 'localhost' not in self.api_base_url:
                # Ensure we have the proper protocol
                if not self.api_base_url.startswith(('http://', 'https://')):
                    api_endpoint = f"https://{self.api_base_url}/api/performance-metrics"
            
            response = requests.post(
                api_endpoint,
                json=metrics,
                headers={'Content-Type': 'application/json'},
                timeout=15  # Add timeout to prevent hanging requests
            )
            return response.status_code == 201
        except Exception as e:
            print(f"Error submitting metrics: {e}")
            return False
    
    def start_collection(self, interval=60):  # Collect every minute
        """
        Start periodic data collection
        """
        if self.is_collecting:
            print("Data collection is already running")
            return
            
        self.is_collecting = True
        self.collection_thread = threading.Thread(
            target=self._collection_loop,
            args=(interval,),
            daemon=True
        )
        self.collection_thread.start()
        print(f"Started WiFi data collection for {self.access_point_name}")
    
    def _collection_loop(self, interval):
        """
        Internal loop for periodic data collection
        """
        while self.is_collecting:
            try:
                metrics = self.get_network_stats()
                success = self.submit_metrics(metrics)
                
                if success:
                    print(f"Submitted metrics at {datetime.now()}: {metrics['download_speed']}Mbps ↓, {metrics['upload_speed']}Mbps ↑, {metrics['connected_users']} users")
                else:
                    print(f"Failed to submit metrics at {datetime.now()}")
                    
                time.sleep(interval)
            except Exception as e:
                print(f"Error in collection loop: {e}")
                time.sleep(interval)
    
    def stop_collection(self):
        """
        Stop data collection
        """
        self.is_collecting = False
        if self.collection_thread:
            self.collection_thread.join(timeout=2)
        print("Stopped WiFi data collection")


# For testing purposes
if __name__ == "__main__":
    collector = WiFiDataCollector(api_base_url="http://localhost:5000")
    
    print("Testing WiFi data collection...")
    test_data = collector.get_network_stats()
    print(json.dumps(test_data, indent=2))