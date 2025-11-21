from flask import Flask, render_template, request, jsonify
import requests
import numpy as np
import math
import json
import random

app = Flask(__name__)

def get_api_key():
    try:
        with open('map_api_key.txt', 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        return None

API_KEY = get_api_key()

# --- In-Memory Data Storage ---
# Parking Spots: [{'id': 0, 'lat': 38.0, 'lng': 114.5}, ...]
parking_spots = []
spot_counter = 0

# Vehicles: [{'id': 0, 'capacity': 100, 'spot_id': None}]
vehicles = []
vehicle_counter = 0

# Simulation Constants
SHIJIAZHUANG_BOUNDS = {
    'min_lat': 37.9, 'max_lat': 38.2,
    'min_lng': 114.3, 'max_lng': 114.7
}
GRID_SIZE = 100 # Increased resolution to prevent heatmap striping artifacts

# Outage Heatmap (Stored as a list of [lat, lng, intensity])
outage_heatmap_data = []

@app.route('/')
def index():
    return render_template('index.html')

# --- Parking Spots API ---
@app.route('/api/spots', methods=['GET', 'POST'])
def handle_spots():
    global spot_counter
    if request.method == 'POST':
        data = request.json
        spot = {
            'id': spot_counter,
            'lat': data['lat'],
            'lng': data['lng']
        }
        parking_spots.append(spot)
        spot_counter += 1
        return jsonify({'success': True, 'spot': spot})
    return jsonify({'spots': parking_spots})

@app.route('/api/spots/clear', methods=['POST'])
def clear_spots():
    global parking_spots, spot_counter
    parking_spots = []
    spot_counter = 0
    # Also reset vehicle positions
    for v in vehicles:
        v['spot_id'] = None
    return jsonify({'success': True})

# --- Vehicles API ---
@app.route('/api/vehicles', methods=['GET', 'POST'])
def handle_vehicles():
    global vehicle_counter
    if request.method == 'POST':
        data = request.json
        count = int(data.get('count', 1))
        capacity = float(data.get('capacity', 100.0))
        new_vehicles = []
        for _ in range(count):
            v = {
                'id': vehicle_counter,
                'capacity': capacity,
                'spot_id': None # Initially not parked
            }
            vehicles.append(v)
            new_vehicles.append(v)
            vehicle_counter += 1
        return jsonify({'success': True, 'vehicles': new_vehicles})
    return jsonify({'vehicles': vehicles})

@app.route('/api/vehicles/clear', methods=['POST'])
def clear_vehicles():
    global vehicles, vehicle_counter
    vehicles = []
    vehicle_counter = 0
    return jsonify({'success': True})

# --- Heatmap Logic ---

def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

def generate_grid_points():
    """Generates a grid of points covering Shijiazhuang."""
    lats = np.linspace(SHIJIAZHUANG_BOUNDS['min_lat'], SHIJIAZHUANG_BOUNDS['max_lat'], GRID_SIZE)
    lngs = np.linspace(SHIJIAZHUANG_BOUNDS['min_lng'], SHIJIAZHUANG_BOUNDS['max_lng'], GRID_SIZE)
    grid = []
    for lat in lats:
        for lng in lngs:
            grid.append({'lat': lat, 'lng': lng})
    return grid

@app.route('/api/heatmap/outage/generate', methods=['POST'])
def generate_outage_heatmap():
    global outage_heatmap_data
    # Generate random Gaussian blobs
    num_blobs = random.randint(3, 6)
    blobs = []
    for _ in range(num_blobs):
        blobs.append({
            'lat': random.uniform(SHIJIAZHUANG_BOUNDS['min_lat'], SHIJIAZHUANG_BOUNDS['max_lat']),
            'lng': random.uniform(SHIJIAZHUANG_BOUNDS['min_lng'], SHIJIAZHUANG_BOUNDS['max_lng']),
            'sigma': random.uniform(0.02, 0.05),
            'intensity': random.uniform(0.5, 1.0)
        })
    
    grid = generate_grid_points()
    raw_data = []
    
    # First pass: Calculate raw values
    for point in grid:
        val = 0
        for blob in blobs:
            dist_sq = (point['lat'] - blob['lat'])**2 + (point['lng'] - blob['lng'])**2
            val += blob['intensity'] * np.exp(-dist_sq / (2 * blob['sigma']**2))
        raw_data.append({'lat': point['lat'], 'lng': point['lng'], 'val': val})
    
    # Second pass: Find max for normalization
    max_val = max([d['val'] for d in raw_data]) if raw_data else 1.0
    if max_val == 0: max_val = 1.0
    
    # Third pass: Normalize and scale dynamically based on grid density
    # Heuristic: With higher density, we need lower intensity per point to avoid saturation.
    # Factor = 2.0 / GRID_SIZE seems to work well for Leaflet heat (2.0 / 100 = 0.02, maybe too low? let's try 5.0/GRID_SIZE = 0.05)
    # User reported 0.05 is too light. Let's try 10.0 / GRID_SIZE = 0.1 for GRID_SIZE=100
    dynamic_scale = 15.0 / GRID_SIZE # Results in 0.15 for size 100
    
    final_data = []
    for item in raw_data:
        normalized_val = (item['val'] / max_val) * dynamic_scale
        if normalized_val > 0.001:
             final_data.append([item['lat'], item['lng'], float(normalized_val)])
            
    outage_heatmap_data = final_data
    return jsonify({'success': True, 'data': final_data})

@app.route('/api/heatmap/outage', methods=['GET'])
def get_outage_heatmap():
    return jsonify({'data': outage_heatmap_data})


# --- Optimization Logic ---

@app.route('/api/optimize', methods=['POST'])
def optimize_dispatch():
    """
    Greedy algorithm to assign vehicles to parking spots to minimize loss.
    Loss = Sum( (Norm(Outage) - Norm(Support))^2 )
    """
    mode = request.json.get('mode', 'linear') # 'linear' or 'api' (API not fully implemented for grid due to limits)
    
    if not parking_spots:
        return jsonify({'error': 'No parking spots defined'}), 400
    if not vehicles:
        return jsonify({'error': 'No vehicles defined'}), 400
    if not outage_heatmap_data:
        return jsonify({'error': 'No outage heatmap generated'}), 400

    # 1. Prepare Data
    # Convert outage data to a simpler structure for calculation
    # Use the same grid points as generated in outage heatmap
    grid_points = [] 
    outage_values = []
    
    # We need a consistent grid index. 
    # Let's re-generate the standard grid and map outage values to it.
    # To be precise, let's just use the outage_heatmap_data points as our evaluation points
    # because those are the "demand" points.
    for p in outage_heatmap_data:
        grid_points.append({'lat': p[0], 'lng': p[1]})
        # Note: outage_heatmap_data is already scaled down by 0.6. 
        # We should probably use the relative values for optimization or revert scaling?
        # For optimization loss function, relative shape matters most.
        outage_values.append(p[2])
        
    outage_arr = np.array(outage_values)
    if outage_arr.max() > 0:
        outage_norm = outage_arr / outage_arr.max()
    else:
        outage_norm = outage_arr

    # 2. Greedy Assignment
    # Reset vehicle assignments
    for v in vehicles:
        v['spot_id'] = None
    
    # Track available capacity at each spot (assuming infinite capacity per spot for now, 
    # or we can limit 1 vehicle per spot. User said "which car stops where", implies mapping.
    # Let's assume 1 spot can hold multiple cars for now to simplify, or 1-to-1?
    # "Find which car stops where" -> usually 1 car per spot if spots are discrete.
    # Let's assume spots are finite resources.
    available_spots = set(s['id'] for s in parking_spots)
    
    # Sort vehicles by capacity (descending) to place biggest assets first? 
    # Or just iterate. Let's sort.
    sorted_vehicles = sorted(vehicles, key=lambda x: x['capacity'], reverse=True)
    
    assignments = {} # vehicle_id -> spot_id
    
    # Pre-calculate distances from all spots to all grid points
    # spot_distances[spot_id][grid_index]
    spot_distances = {}
    for spot in parking_spots:
        dists = []
        for gp in grid_points:
            d = haversine(spot['lat'], spot['lng'], gp['lat'], gp['lng'])
            dists.append(d + 0.1) # Avoid division by zero
        spot_distances[spot['id']] = np.array(dists)

    current_support_raw = np.zeros(len(grid_points))
    
    for vehicle in sorted_vehicles:
        best_spot_id = None
        min_loss = float('inf')
        
        # Try placing this vehicle at every available spot
        # Note: If we allow multiple cars per spot, we don't remove from available_spots.
        # Let's allow multiple cars per spot for this version as "Parking Point" might be a large area.
        
        for spot_id in list(available_spots): # Iterate over all spots
            # Calculate hypothetical support increase
            # Support = Capacity / Distance
            contribution = vehicle['capacity'] / spot_distances[spot_id]
            
            temp_support_raw = current_support_raw + contribution
            
            # Normalize Support (Global normalization is tricky during incremental, 
            # but for greedy we just need relative improvement). 
            # Let's normalize based on current max to match outage scale.
            if temp_support_raw.max() > 0:
                temp_support_norm = temp_support_raw / temp_support_raw.max()
            else:
                temp_support_norm = temp_support_raw
                
            # Loss = Sum((Outage_Norm - Support_Norm)^2)
            loss = np.sum((outage_norm - temp_support_norm)**2)
            
            if loss < min_loss:
                min_loss = loss
                best_spot_id = spot_id
        
        # Assign best spot
        if best_spot_id is not None:
            assignments[vehicle['id']] = best_spot_id
            # Update current support permanently
            current_support_raw += vehicle['capacity'] / spot_distances[best_spot_id]
            # If we wanted 1-to-1 mapping, we would remove best_spot_id from available_spots here
            # available_spots.remove(best_spot_id) 
            
            # Update vehicle object
            # Find original vehicle obj to update
            for v in vehicles:
                if v['id'] == vehicle['id']:
                    v['spot_id'] = best_spot_id
                    break

    return jsonify({'success': True, 'assignments': assignments})

@app.route('/api/heatmap/support', methods=['GET'])
def get_support_heatmap():
    # Calculate current support heatmap based on vehicle assignments
    if not vehicles or not outage_heatmap_data:
        return jsonify({'data': []})
        
    grid_points = [{'lat': p[0], 'lng': p[1]} for p in outage_heatmap_data]
    
    total_support = np.zeros(len(grid_points))
    
    active_vehicles = [v for v in vehicles if v['spot_id'] is not None]
    if not active_vehicles:
         return jsonify({'data': []})

    # Cache spots for lookup
    spot_map = {s['id']: s for s in parking_spots}

    for v in active_vehicles:
        spot = spot_map.get(v['spot_id'])
        if not spot: continue
        
        dists = []
        for gp in grid_points:
            d = haversine(spot['lat'], spot['lng'], gp['lat'], gp['lng'])
            dists.append(d + 0.1)
        dists = np.array(dists)
        
        total_support += v['capacity'] / dists
        
    # Format for heatmap [lat, lng, intensity]
    # Normalize to match outage intensity range roughly for visual comparison
    # Dynamic scaling: 15.0 / GRID_SIZE (same as outage)
    dynamic_scale = 15.0 / GRID_SIZE
    
    if total_support.max() > 0:
        total_support = (total_support / total_support.max()) * dynamic_scale
        
    data = []
    for i, val in enumerate(total_support):
        if val > 0.001:
            data.append([grid_points[i]['lat'], grid_points[i]['lng'], float(val)])
            
    return jsonify({'data': data})

# --- Existing Routes ---
@app.route('/plan_route', methods=['POST'])
def plan_route():
    # (Keep existing implementation)
    if not API_KEY:
        return jsonify({'error': 'API Key not found'}), 500
    data = request.json
    origin = data.get('origin') 
    destination = data.get('destination')
    if not origin or not destination:
        return jsonify({'error': 'Missing origin or destination'}), 400
    url = "https://restapi.amap.com/v5/direction/driving"
    params = {
        'key': API_KEY, 'origin': origin, 'destination': destination,
        'strategy': 32, 'show_fields': 'polyline'
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        result = response.json()
        if result.get('status') == '1' and result.get('route') and result['route']['paths']:
            path = result['route']['paths'][0]
            all_polylines = []
            for step in path.get('steps', []):
                if 'polyline' in step: all_polylines.append(step['polyline'])
            full_path_coords = []
            for pl_str in all_polylines:
                points = pl_str.split(';')
                for p in points:
                    lon, lat = map(float, p.split(','))
                    full_path_coords.append([lat, lon])
            return jsonify({'success': True, 'path': full_path_coords, 'distance': path.get('distance'), 'duration': path.get('duration')})
        else:
            return jsonify({'success': False, 'error': result.get('info', 'Unknown error')})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
