from flask import Flask, render_template, request, jsonify
import requests

app = Flask(__name__)

def get_api_key():
    try:
        with open('map_api_key.txt', 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        return None

API_KEY = get_api_key()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/plan_route', methods=['POST'])
def plan_route():
    if not API_KEY:
        return jsonify({'error': 'API Key not found'}), 500

    data = request.json
    origin = data.get('origin') # format: "lon,lat"
    destination = data.get('destination') # format: "lon,lat"

    if not origin or not destination:
        return jsonify({'error': 'Missing origin or destination'}), 400

    url = "https://restapi.amap.com/v5/direction/driving"
    params = {
        'key': API_KEY,
        'origin': origin,
        'destination': destination,
        'strategy': 32, # Default strategy
        'show_fields': 'polyline'
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        result = response.json()
        
        if result.get('status') == '1' and result.get('route') and result['route']['paths']:
            path = result['route']['paths'][0]
            # steps -> polyline
            all_polylines = []
            for step in path.get('steps', []):
                if 'polyline' in step:
                     all_polylines.append(step['polyline'])
            
            # Combine all polyline strings into one list of points
            # Format "lon,lat;lon,lat" -> [[lat, lon], [lat, lon]] (Leaflet expects [lat, lon])
            full_path_coords = []
            for pl_str in all_polylines:
                points = pl_str.split(';')
                for p in points:
                    lon, lat = map(float, p.split(','))
                    full_path_coords.append([lat, lon]) # Leaflet: [Lat, Lng]
            
            return jsonify({
                'success': True,
                'path': full_path_coords,
                'distance': path.get('distance'),
                'duration': path.get('duration')
            })
        else:
            return jsonify({'success': False, 'error': result.get('info', 'Unknown error from Map API')})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
