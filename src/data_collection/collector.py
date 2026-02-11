import subprocess
import speedtest
import requests
import time
import json
import platform
from datetime import datetime
import psutil
import socket

class WiFiPerformanceCollector:
    def __init__(self, server_url="http://localhost:5000/api/performance-metrics"):
        self.server_url = server_url
        
    def run_speed_test(self):
        """Run a speed test to measure download/upload speeds and ping"""
        try:
            st = speedtest.Speedtest()
            
            # Get best server
            st.get_best_server()
            
            # Perform download test
            download_speed = st.download() / 1_000_000  # Convert to Mbps
            
            # Perform upload test
            upload_speed = st.upload() / 1_000_000  # Convert to Mbps
            
            # Ping
            ping_result = st.results.ping
            
            return {
                'download_speed': round(download_speed, 2),
                'upload_speed': round(upload_speed, 2),
                'latency': round(ping_result, 2)
            }
        except Exception as e:
            print(f"Error running speed test: {e}")
            return {
                'download_speed': 0,
                'upload_speed': 0,
                'latency': 0
            }

    def get_wifi_signal_strength(self):
        """Get WiFi signal strength (RSSI)"""
        try:
            if platform.system() == "Windows":
                # Windows command to get WiFi signal
                cmd = ['netsh', 'wlan', 'show', 'interfaces']
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                
                # Parse the output to find signal strength
                for line in result.stdout.split('\n'):
                    if 'Signal' in line:
                        signal_str = line.split(':')[1].strip().replace('%', '').strip()
                        try:
                            signal_strength = int(signal_str)
                            # Convert percentage to dBm (rough conversion)
                            rssi = (signal_strength / 2) - 100
                            return rssi
                        except ValueError:
                            continue
                        
            elif platform.system() == "Linux":
                # Linux command to get WiFi signal
                cmd = ['iwconfig', 'wlan0']
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                
                for line in result.stdout.split('\n'):
                    if 'Signal level' in line:
                        # Extract signal level from iwconfig output
                        parts = line.split('Signal level=')
                        if len(parts) > 1:
                            signal_str = parts[1].split(' ')[0]
                            try:
                                return int(signal_str)
                            except ValueError:
                                continue
            
            elif platform.system() == "Darwin":  # macOS
                # macOS command to get WiFi signal
                cmd = ['/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport', '-I']
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                
                for line in result.stdout.split('\n'):
                    if 'agrCtlRSSI' in line:
                        rssi_str = line.split(':')[1].strip()
                        try:
                            return int(rssi_str)
                        except ValueError:
                            continue
                            
        except Exception as e:
            print(f"Error getting WiFi signal strength: {e}")
        
        return -60  # Default value if unable to determine

    def count_connected_devices(self):
        """Estimate number of connected devices (this is a simplified version)"""
        try:
            # Get network connections
            connections = psutil.net_connections(kind='inet')
            
            # Count unique IPs connected to common ports (HTTP, HTTPS, etc.)
            unique_ips = set()
            for conn in connections:
                if conn.raddr and conn.raddr.ip != '127.0.0.1':
                    unique_ips.add(conn.raddr.ip)
                    
            return len(unique_ips)
        except Exception as e:
            print(f"Error counting connected devices: {e}")
            return 1  # Default to 1 device

    def get_bandwidth_usage(self):
        """Get current bandwidth usage percentage"""
        try:
            # Get network IO statistics
            net_io = psutil.net_io_counters()
            
            # For demonstration purposes, we'll return a simulated value
            # In a real implementation, this would calculate actual bandwidth usage
            return 50.0  # Placeholder percentage
        except Exception as e:
            print(f"Error getting bandwidth usage: {e}")
            return 0.0

    def simulate_packet_loss(self):
        """Simulate packet loss by pinging a server multiple times"""
        try:
            # This is a simplified simulation
            # In a real implementation, we would ping multiple times and calculate loss rate
            return 0.0  # Placeholder percentage
        except Exception as e:
            print(f"Error calculating packet loss: {e}")
            return 0.0

    def collect_all_metrics(self, ap_name, building="", floor=0, room_number="", latitude=None, longitude=None):
        """Collect all performance metrics"""
        print("Collecting WiFi performance metrics...")
        
        # Run speed test
        speed_data = self.run_speed_test()
        
        # Get WiFi signal strength
        signal_strength = self.get_wifi_signal_strength()
        
        # Estimate connected devices
        connected_devices = self.count_connected_devices()
        
        # Get bandwidth usage
        bandwidth_usage = self.get_bandwidth_usage()
        
        # Simulate packet loss
        packet_loss = self.simulate_packet_loss()
        
        # Create metrics payload
        metrics = {
            'ap_name': ap_name,
            'building': building,
            'floor': floor,
            'room_number': room_number,
            'latitude': latitude,
            'longitude': longitude,
            'download_speed': speed_data['download_speed'],
            'upload_speed': speed_data['upload_speed'],
            'latency': speed_data['latency'],
            'signal_strength': signal_strength,
            'connected_users': connected_devices,
            'bandwidth_usage': bandwidth_usage,
            'packet_loss': packet_loss,
            'timestamp': datetime.now().isoformat()
        }
        
        print(f"Collected metrics: {metrics}")
        return metrics

    def send_metrics(self, metrics):
        """Send collected metrics to the server"""
        try:
            response = requests.post(
                self.server_url,
                json=metrics,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 201:
                print("Metrics sent successfully!")
                return True
            else:
                print(f"Failed to send metrics: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"Error sending metrics: {e}")
            return False

    def continuous_monitoring(self, ap_name, interval=60, building="", floor=0, room_number=""):
        """Continuously monitor and send metrics at specified intervals"""
        print(f"Starting continuous monitoring for AP: {ap_name}")
        print(f"Interval: {interval} seconds")
        
        while True:
            try:
                # Collect metrics
                metrics = self.collect_all_metrics(ap_name, building, floor, room_number)
                
                # Send metrics to server
                self.send_metrics(metrics)
                
                # Wait for specified interval
                time.sleep(interval)
                
            except KeyboardInterrupt:
                print("\nMonitoring stopped by user.")
                break
            except Exception as e:
                print(f"Error in monitoring loop: {e}")
                time.sleep(interval)

# Example usage
if __name__ == "__main__":
    collector = WiFiPerformanceCollector()
    
    # Example: Collect metrics for a specific access point
    metrics = collector.collect_all_metrics(
        ap_name="LIBRARY_AP_01",
        building="Library",
        floor=1,
        room_number="Main Hall"
    )
    
    print(json.dumps(metrics, indent=2))