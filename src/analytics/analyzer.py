import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import sqlite3
from datetime import datetime, timedelta
import json
from collections import defaultdict

class WiFiAnalyzer:
    def __init__(self, db_path='wifi_data.db'):
        self.db_path = db_path
        
    def load_data(self, days_back=7):
        """Load performance data for the last N days"""
        conn = sqlite3.connect(self.db_path)
        
        query = f'''
            SELECT ap.ap_name, ap.building, ap.floor, ap.room_number,
                   pm.download_speed, pm.upload_speed, pm.latency, 
                   pm.connected_users, pm.signal_strength, pm.bandwidth_usage,
                   pm.timestamp
            FROM performance_metrics pm
            JOIN access_points ap ON pm.ap_id = ap.id
            WHERE pm.timestamp >= datetime('now', '-{days_back} days')
            ORDER BY pm.timestamp DESC
        '''
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        # Convert timestamp to datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        return df

    def calculate_quality_scores(self, df):
        """Calculate quality scores for all records in dataframe"""
        def calculate_single_score(row):
            download_speed = row['download_speed'] or 0
            upload_speed = row['upload_speed'] or 0
            latency = row['latency'] or float('inf')
            connected_users = row['connected_users'] or 0
            signal_strength = row['signal_strength'] or -80  # Default signal strength
            
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
        
        df['quality_score'] = df.apply(calculate_single_score, axis=1)
        return df

    def get_top_performers(self, df, n=5):
        """Get top N performing access points"""
        latest_metrics = df.loc[df.groupby('ap_name')['timestamp'].idxmax()]
        top_performers = latest_metrics.nlargest(n, 'quality_score')
        return top_performers[['ap_name', 'quality_score', 'download_speed', 'upload_speed', 'latency', 'connected_users']]

    def get_worst_performers(self, df, n=5):
        """Get bottom N performing access points"""
        latest_metrics = df.loc[df.groupby('ap_name')['timestamp'].idxmax()]
        worst_performers = latest_metrics.nsmallest(n, 'quality_score')
        return worst_performers[['ap_name', 'quality_score', 'download_speed', 'upload_speed', 'latency', 'connected_users']]

    def get_building_analysis(self, df):
        """Analyze performance by building"""
        latest_metrics = df.loc[df.groupby('ap_name')['timestamp'].idxmax()]
        building_stats = latest_metrics.groupby('building').agg({
            'quality_score': ['mean', 'std', 'count'],
            'download_speed': 'mean',
            'upload_speed': 'mean',
            'latency': 'mean'
        }).round(2)
        
        return building_stats

    def get_peak_hours_analysis(self, df):
        """Analyze peak usage hours"""
        df['hour'] = df['timestamp'].dt.hour
        hourly_avg = df.groupby('hour').agg({
            'quality_score': 'mean',
            'connected_users': 'mean',
            'download_speed': 'mean'
        }).round(2)
        
        return hourly_avg

    def get_congestion_analysis(self, df):
        """Analyze access points based on user congestion"""
        latest_metrics = df.loc[df.groupby('ap_name')['timestamp'].idxmax()]
        
        # Classify by congestion level
        latest_metrics['congestion_level'] = pd.cut(
            latest_metrics['connected_users'], 
            bins=[0, 5, 15, 30, float('inf')], 
            labels=['Low', 'Medium', 'High', 'Severe']
        )
        
        congestion_stats = latest_metrics.groupby('congestion_level').size().to_dict()
        return congestion_stats

    def generate_report(self, days_back=7):
        """Generate a comprehensive analysis report"""
        print(f"Generating WiFi Quality Analysis Report for last {days_back} days...")
        print("="*60)
        
        df = self.load_data(days_back)
        df = self.calculate_quality_scores(df)
        
        if df.empty:
            print("No data available for analysis.")
            return {}
        
        print(f"Total records analyzed: {len(df)}")
        print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
        print()
        
        # Top performers
        print("🏆 TOP 5 PERFORMING ACCESS POINTS:")
        top_performers = self.get_top_performers(df)
        print(top_performers.to_string(index=False))
        print()
        
        # Worst performers
        print("⚠️  BOTTOM 5 PERFORMING ACCESS POINTS:")
        worst_performers = self.get_worst_performers(df)
        print(worst_performers.to_string(index=False))
        print()
        
        # Building analysis
        print("🏢 BUILDING PERFORMANCE ANALYSIS:")
        building_analysis = self.get_building_analysis(df)
        print(building_analysis.to_string())
        print()
        
        # Peak hours
        print("🕐 PEAK USAGE HOURS ANALYSIS:")
        peak_hours = self.get_peak_hours_analysis(df)
        print(peak_hours.to_string())
        print()
        
        # Congestion analysis
        print("🚦 CONGESTION LEVEL ANALYSIS:")
        congestion_analysis = self.get_congestion_analysis(df)
        for level, count in congestion_analysis.items():
            print(f"{level}: {count} access points")
        print()
        
        # Overall statistics
        latest_metrics = df.loc[df.groupby('ap_name')['timestamp'].idxmax()]
        avg_quality = latest_metrics['quality_score'].mean()
        avg_download = latest_metrics['download_speed'].mean()
        avg_upload = latest_metrics['upload_speed'].mean()
        avg_latency = latest_metrics['latency'].mean()
        
        print("📊 OVERALL NETWORK STATISTICS:")
        print(f"Average Quality Score: {avg_quality:.2f}/100")
        print(f"Average Download Speed: {avg_download:.2f} Mbps")
        print(f"Average Upload Speed: {avg_upload:.2f} Mbps")
        print(f"Average Latency: {avg_latency:.2f} ms")
        
        # Prepare summary for return
        report_summary = {
            'total_records': len(df),
            'date_range': {
                'start': str(df['timestamp'].min()),
                'end': str(df['timestamp'].max())
            },
            'top_performers': top_performers.to_dict('records'),
            'worst_performers': worst_performers.to_dict('records'),
            'building_analysis': building_analysis.to_dict(),
            'peak_hours': peak_hours.to_dict(),
            'congestion_analysis': congestion_analysis,
            'overall_stats': {
                'avg_quality_score': round(avg_quality, 2),
                'avg_download_speed': round(avg_download, 2),
                'avg_upload_speed': round(avg_upload, 2),
                'avg_latency': round(avg_latency, 2)
            }
        }
        
        return report_summary

    def create_visualizations(self, days_back=7, save_to_file=True):
        """Create visualizations for the analysis"""
        df = self.load_data(days_back)
        df = self.calculate_quality_scores(df)
        
        if df.empty:
            print("No data available for visualization.")
            return
        
        # Create figure with subplots
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle('WiFi Network Performance Analysis', fontsize=16)
        
        # 1. Quality Score Distribution
        latest_metrics = df.loc[df.groupby('ap_name')['timestamp'].idxmax()]
        axes[0, 0].hist(latest_metrics['quality_score'], bins=20, edgecolor='black')
        axes[0, 0].set_title('Distribution of Quality Scores')
        axes[0, 0].set_xlabel('Quality Score')
        axes[0, 0].set_ylabel('Number of Access Points')
        
        # 2. Download Speed vs Connected Users
        axes[0, 1].scatter(latest_metrics['connected_users'], latest_metrics['download_speed'], alpha=0.6)
        axes[0, 1].set_title('Download Speed vs Connected Users')
        axes[0, 1].set_xlabel('Connected Users')
        axes[0, 1].set_ylabel('Download Speed (Mbps)')
        
        # 3. Average Performance by Building
        building_avg = latest_metrics.groupby('building')['quality_score'].mean().sort_values(ascending=False)
        axes[1, 0].bar(range(len(building_avg)), building_avg.values)
        axes[1, 0].set_title('Average Quality Score by Building')
        axes[1, 0].set_xlabel('Building')
        axes[1, 0].set_ylabel('Average Quality Score')
        axes[1, 0].set_xticks(range(len(building_avg)))
        axes[1, 0].set_xticklabels(building_avg.index, rotation=45, ha='right')
        
        # 4. Peak Hours Analysis
        hourly_avg = self.get_peak_hours_analysis(df)
        axes[1, 1].plot(hourly_avg.index, hourly_avg['quality_score'], marker='o')
        axes[1, 1].set_title('Average Quality Score by Hour of Day')
        axes[1, 1].set_xlabel('Hour of Day')
        axes[1, 1].set_ylabel('Average Quality Score')
        
        plt.tight_layout()
        
        if save_to_file:
            plt.savefig('wifi_analysis_visualization.png', dpi=300, bbox_inches='tight')
            print("Visualization saved as 'wifi_analysis_visualization.png'")
        
        plt.show()

# Example usage
if __name__ == "__main__":
    analyzer = WiFiAnalyzer()
    
    # Generate analysis report
    report = analyzer.generate_report(days_back=7)
    
    # Create visualizations
    analyzer.create_visualizations(days_back=7)