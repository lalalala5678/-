import os

# 石家庄地理边界
SHIJIAZHUANG_BOUNDS = {
    'min_lat': 37.9, 'max_lat': 38.2,
    'min_lng': 114.3, 'max_lng': 114.7
}

# 热力图网格密度 (100x100)
GRID_SIZE = 100 

def get_api_key():
    """从文件中读取高德地图 API Key"""
    try:
        file_path = os.path.join(os.path.dirname(__file__), 'map_api_key.txt')
        with open(file_path, 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        return None

API_KEY = get_api_key()
