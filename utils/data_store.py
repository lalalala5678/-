"""
内存数据存储模块
用于模拟数据库，在内存中维护应用程序的状态。
"""

# 停车点列表: [{'id': int, 'lat': float, 'lng': float, 'marker': obj(optional)}]
parking_spots = []
_spot_counter = 0

# 车辆列表: [{'id': int, 'capacity': float, 'spot_id': int|None}]
vehicles = []
_vehicle_counter = 0

# 断电热力图数据缓存: list of [lat, lng, intensity]
outage_heatmap_data = []

def add_spot(lat, lng):
    global _spot_counter
    spot = {
        'id': _spot_counter,
        'lat': lat,
        'lng': lng
    }
    parking_spots.append(spot)
    _spot_counter += 1
    return spot

def clear_spots():
    global parking_spots, _spot_counter
    parking_spots.clear()
    _spot_counter = 0
    # 也要重置车辆的停放位置
    for v in vehicles:
        v['spot_id'] = None

def add_vehicles(count, capacity):
    global _vehicle_counter
    new_vehicles = []
    for _ in range(count):
        v = {
            'id': _vehicle_counter,
            'capacity': capacity,
            'spot_id': None # 初始未停放
        }
        vehicles.append(v)
        new_vehicles.append(v)
        _vehicle_counter += 1
    return new_vehicles

def clear_vehicles():
    global vehicles, _vehicle_counter
    vehicles.clear()
    _vehicle_counter = 0

def set_outage_data(data):
    global outage_heatmap_data
    outage_heatmap_data = data

def get_outage_data():
    return outage_heatmap_data
