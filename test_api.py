import requests
import json
import time

def test_api():
    base_url = "http://localhost:5000"
    
    print("Testing University WiFi Monitoring API...")
    
    # Test 1: Check if server is running
    try:
        response = requests.get(f"{base_url}/")
        if response.status_code == 200:
            print("✓ Server is running")
            print(f"Response: {response.json()}")
        else:
            print(f"✗ Server returned status code: {response.status_code}")
    except Exception as e:
        print(f"✗ Error connecting to server: {e}")
        print("Make sure the server is running with: python -m src.backend.app")
        return
    
    # Test 2: Submit sample metrics
    sample_metrics = {
        "ap_name": "TEST_AP_01",
        "building": "Test Building",
        "floor": 1,
        "room_number": "Test Room",
        "download_speed": 85.5,
        "upload_speed": 20.3,
        "latency": 15.2,
        "packet_loss": 0.1,
        "connected_users": 12,
        "signal_strength": -45.0,
        "bandwidth_usage": 65.0
    }
    
    try:
        response = requests.post(f"{base_url}/api/performance-metrics", json=sample_metrics)
        if response.status_code == 201:
            print("✓ Successfully submitted performance metrics")
        else:
            print(f"✗ Failed to submit metrics: {response.status_code}")
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"✗ Error submitting metrics: {e}")
    
    # Wait a moment for the data to be processed
    time.sleep(1)
    
    # Test 3: Get access points
    try:
        response = requests.get(f"{base_url}/api/access-points")
        if response.status_code == 200:
            aps = response.json()
            print(f"✓ Retrieved {len(aps)} access points")
            if aps:
                print(f"Sample AP: {aps[0]['ap_name']} - Status: {aps[0]['status']} - Score: {aps[0]['quality_score']}")
        else:
            print(f"✗ Failed to get access points: {response.status_code}")
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"✗ Error getting access points: {e}")
    
    # Test 4: Get recommendations
    try:
        response = requests.get(f"{base_url}/api/recommendations")
        if response.status_code == 200:
            recs = response.json()
            print(f"✓ Retrieved {len(recs)} recommendations")
            if recs:
                print(f"Top recommendation: {recs[0]['ap_name']} - Status: {recs[0]['status']}")
        else:
            print(f"✗ Failed to get recommendations: {response.status_code}")
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"✗ Error getting recommendations: {e}")

if __name__ == "__main__":
    test_api()