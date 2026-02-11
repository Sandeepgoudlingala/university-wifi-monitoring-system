# University WiFi Quality Monitoring & Smart Location Recommendation System

## Overview
This is a comprehensive system for monitoring WiFi quality across a university campus, providing real-time analytics and smart location recommendations for students and staff.

## Features
- Real-time WiFi performance monitoring
- Quality scoring based on speed, latency, and user density
- Interactive campus map with access point locations
- Smart recommendations based on user location
- Mobile-responsive dashboard

## Deployment

### Local Development
1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the system:
```bash
python run_system.py
```

3. Access the dashboard at: http://localhost:5000

### Vercel Deployment

1. Install the Vercel CLI:
```bash
npm i -g vercel
```

2. Link your project:
```bash
vercel
```

3. Deploy:
```bash
vercel --prod
```

### Environment Variables
- `PRODUCTION=true` - Enables production mode (only starts the API server)

## Architecture
- **Backend**: Flask API server with SQLite database
- **Frontend**: HTML/CSS/JS dashboard with Leaflet.js maps
- **Data Collection**: Periodic performance metrics collection
- **Analytics**: Real-time analysis and quality scoring

## API Endpoints
- `GET /api/access-points` - Get all access points with current status
- `POST /api/performance-metrics` - Submit performance metrics
- `GET /api/recommendations` - Get recommended access points

## Tech Stack
- Python Flask
- SQLite
- JavaScript/HTML/CSS
- Leaflet.js for maps
- Gunicorn for production

## Production Notes
- The system uses an ephemeral database in production (data resets on each deployment)
- For persistent data in production, connect to a cloud database service
- The production mode only runs the API server without the simulation components