import sqlite3
import math
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
import json

class RecommendationEngine:
    def __init__(self, db_path='wifi_data.db'):
        self.db_path = db_path

    def haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate the great circle distance between two points 
        on the earth (specified in decimal degrees)
        Returns distance in meters
        """
        # Convert decimal degrees to radians
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        # Radius of earth in meters
        r = 6371000
        
        return c * r

    def get_nearby_access_points(self, user_lat: float, user_lon: float, radius: float = 1000) -> List[Dict]:
        """
        Get access points within a specified radius of the user
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get all access points with location data
        cursor.execute('''
            SELECT ap.id, ap.ap_name, ap.building, ap.floor, ap.room_number,
                   ap.latitude, ap.longitude,
                   pm.download_speed, pm.upload_speed, pm.latency, 
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
            WHERE ap.latitude IS NOT NULL AND ap.longitude IS NOT NULL
        ''')
        
        rows = cursor.fetchall()
        columns = [description[0] for description in cursor.description]
        
        nearby_aps = []
        for row in rows:
            ap_dict = dict(zip(columns, row))
            
            # Calculate distance if location data exists
            if ap_dict['latitude'] and ap_dict['longitude']:
                distance = self.haversine_distance(
                    user_lat, user_lon,
                    ap_dict['latitude'], ap_dict['longitude']
                )
                
                if distance <= radius:
                    ap_dict['distance'] = round(distance, 2)
                    ap_dict['quality_score'] = self.calculate_quality_score(ap_dict)
                    ap_dict['status'] = self.get_status_from_score(ap_dict['quality_score'])
                    nearby_aps.append(ap_dict)
        
        conn.close()
        
        # Sort by quality score descending
        nearby_aps.sort(key=lambda x: x.get('quality_score', 0), reverse=True)
        
        return nearby_aps

    def get_current_ap_status(self, user_lat: float, user_lon: float, radius: float = 50) -> Dict:
        """
        Get the status of the current access point (closest one)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get closest access point within a small radius
        cursor.execute('''
            SELECT ap.id, ap.ap_name, ap.building, ap.floor, ap.room_number,
                   ap.latitude, ap.longitude,
                   pm.download_speed, pm.upload_speed, pm.latency, 
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
            WHERE ap.latitude IS NOT NULL AND ap.longitude IS NOT NULL
            ORDER BY ABS(ap.latitude - ?) + ABS(ap.longitude - ?)
            LIMIT 1
        ''', (user_lat, user_lon))
        
        row = cursor.fetchone()
        if row:
            columns = [description[0] for description in cursor.description]
            ap_dict = dict(zip(columns, row))
            
            if ap_dict['latitude'] and ap_dict['longitude']:
                distance = self.haversine_distance(
                    user_lat, user_lon,
                    ap_dict['latitude'], ap_dict['longitude']
                )
                
                if distance <= radius:
                    ap_dict['distance'] = round(distance, 2)
                    ap_dict['quality_score'] = self.calculate_quality_score(ap_dict)
                    ap_dict['status'] = self.get_status_from_score(ap_dict['quality_score'])
                    conn.close()
                    return ap_dict
        
        conn.close()
        return None

    def calculate_quality_score(self, data: Dict) -> float:
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

    def get_status_from_score(self, score: float) -> str:
        """Convert quality score to status"""
        if score >= 80:
            return "Excellent"
        elif score >= 60:
            return "Good"
        elif score >= 40:
            return "Medium"
        else:
            return "Poor"

    def generate_recommendations(self, user_lat: float, user_lon: float, 
                               radius: float = 1000, num_recommendations: int = 5) -> Dict:
        """
        Generate personalized recommendations for the user
        """
        # Get current AP status
        current_ap = self.get_current_ap_status(user_lat, user_lon)
        
        # Get nearby access points
        nearby_aps = self.get_nearby_access_points(user_lat, user_lon, radius)
        
        # Filter out the current AP if it's in the list
        if current_ap:
            nearby_aps = [ap for ap in nearby_aps if ap['id'] != current_ap['id']]
        
        # Take top recommendations
        recommendations = nearby_aps[:num_recommendations]
        
        # Prepare recommendation summary
        recommendation_summary = {
            'user_location': {
                'latitude': user_lat,
                'longitude': user_lon
            },
            'current_ap': current_ap,
            'recommendations': recommendations,
            'total_nearby_aps': len(nearby_aps),
            'message': self._generate_advice_message(current_ap, recommendations)
        }
        
        return recommendation_summary

    def _generate_advice_message(self, current_ap: Dict, recommendations: List[Dict]) -> str:
        """
        Generate personalized advice message for the user
        """
        if not current_ap:
            return "We couldn't detect your current access point. Here are the best options nearby."
        
        current_score = current_ap.get('quality_score', 0)
        current_status = current_ap.get('status', 'Unknown')
        
        if current_score < 40:
            if recommendations:
                best_option = recommendations[0]
                return (f"Your current connection is {current_status}. "
                        f"Best nearby location: {best_option['building']} "
                        f"Floor {best_option['floor']} ({best_option['ap_name']}) "
                        f"with {best_option['download_speed'] or 0} Mbps speed.")
            else:
                return f"Your current connection is {current_status}. Unfortunately, no better options detected nearby."
        elif current_score < 60:
            if recommendations:
                best_option = recommendations[0]
                if best_option['quality_score'] > current_score:
                    return (f"Your current connection is {current_status}. "
                            f"You could get better performance at: {best_option['building']} "
                            f"Floor {best_option['floor']} ({best_option['ap_name']}).")
                else:
                    return f"Your current connection is {current_status}. Current location is among the best options."
            else:
                return f"Your current connection is {current_status}. Current location is likely the best option."
        else:
            return f"Your current connection is {current_status}. Enjoy your fast connection!"
    
    def get_trend_analysis(self, ap_id: int, hours_back: int = 24) -> List[Dict]:
        """
        Get trend analysis for a specific access point
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT download_speed, upload_speed, latency, connected_users, signal_strength, timestamp
            FROM performance_metrics
            WHERE ap_id = ? AND timestamp >= datetime('now', '-{} hours')
            ORDER BY timestamp ASC
        ''', (ap_id, hours_back))
        
        rows = cursor.fetchall()
        columns = [description[0] for description in cursor.description]
        
        trends = []
        for row in rows:
            metric_dict = dict(zip(columns, row))
            metric_dict['quality_score'] = self.calculate_quality_score(metric_dict)
            trends.append(metric_dict)
        
        conn.close()
        return trends

# Example usage
if __name__ == "__main__":
    engine = RecommendationEngine()
    
    # Example: Get recommendations for a user at approximate coordinates
    # These would normally come from the user's device GPS
    user_latitude = 40.7128  # Example: New York City coordinates
    user_longitude = -74.0060
    
    recommendations = engine.generate_recommendations(
        user_lat=user_latitude,
        user_lon=user_longitude,
        radius=1000,  # 1 km radius
        num_recommendations=5
    )
    
    print("WiFi Location Recommendations:")
    print("="*50)
    print(f"User Location: ({user_latitude}, {user_longitude})")
    print()
    
    if recommendations['current_ap']:
        current = recommendations['current_ap']
        print(f"Current AP: {current['ap_name']} at {current['building']} Floor {current['floor']}")
        print(f"Status: {current['status']} (Score: {current['quality_score']})")
        print(f"Speed: {current['download_speed'] or 0}↓ / {current['upload_speed'] or 0}↑ Mbps")
        print(f"Users: {current['connected_users'] or 0}")
        print()
    
    print("Recommended Locations:")
    for i, ap in enumerate(recommendations['recommendations'], 1):
        print(f"{i}. {ap['ap_name']} - {ap['building']} Floor {ap['floor']}")
        print(f"   Distance: {ap['distance']}m | Score: {ap['quality_score']} | Status: {ap['status']}")
        print(f"   Speed: {ap['download_speed'] or 0}↓ / {ap['upload_speed'] or 0}↑ Mbps")
        print(f"   Users: {ap['connected_users'] or 0}")
        print()
    
    print(f"Advice: {recommendations['message']}")