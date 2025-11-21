"""
地图服务模块
封装与高德地图 API 的交互逻辑。
"""
import requests
from config import API_KEY

def get_driving_route(origin, destination):
    """
    调用高德地图驾车路径规划 API
    :param origin: 起点坐标 "lon,lat"
    :param destination: 终点坐标 "lon,lat"
    :return: (path_coords, distance, duration) or raises Exception
    """
    if not API_KEY:
        raise ValueError("API Key 未配置")

    url = "https://restapi.amap.com/v5/direction/driving"
    params = {
        'key': API_KEY,
        'origin': origin,
        'destination': destination,
        'strategy': 32, # 默认策略
        'show_fields': 'polyline'
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        result = response.json()
        
        if result.get('status') == '1' and result.get('route') and result['route']['paths']:
            path = result['route']['paths'][0]
            
            # 解析 Polyline
            all_polylines = []
            for step in path.get('steps', []):
                if 'polyline' in step:
                     all_polylines.append(step['polyline'])
            
            # 转换为坐标点列表 [[lat, lon], ...] 供前端 Leaflet 使用
            full_path_coords = []
            for pl_str in all_polylines:
                points = pl_str.split(';')
                for p in points:
                    lon, lat = map(float, p.split(','))
                    full_path_coords.append([lat, lon])
            
            return full_path_coords, path.get('distance'), path.get('duration')
        else:
            error_info = result.get('info', 'Unknown error form Map API')
            raise Exception(f"Map API Error: {error_info}")

    except Exception as e:
        raise e
