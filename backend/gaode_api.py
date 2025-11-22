import requests
import logging

# 配置 API Key
API_KEY = "914c04aa7bd473fbe1eb08054e065416"
# 驾车路径规划 V5 API 地址
DRIVING_URL = "https://restapi.amap.com/v5/direction/driving"

def get_driving_distance(origin, destination):
    """
    调用高德 API 计算两点间的驾车距离 (米)
    :param origin: 起点 {'lng': float, 'lat': float}
    :param destination: 终点 {'lng': float, 'lat': float}
    :return: float 距离(米), 如果失败返回 None
    """
    # 构建请求参数
    # 经度在前，纬度在后，小数点后不得超过6位
    origin_str = f"{origin['lng']:.6f},{origin['lat']:.6f}"
    dest_str = f"{destination['lng']:.6f},{destination['lat']:.6f}"
    
    params = {
        "key": API_KEY,
        "origin": origin_str,
        "destination": dest_str,
        "strategy": 32,  # 默认策略
        "show_fields": "cost" # 尽量返回详细信息以确保包含 distance
    }
    
    try:
        response = requests.get(DRIVING_URL, params=params, timeout=5)
        data = response.json()
        
        if data.get("status") == "1" and data.get("route", {}).get("paths"):
            # 获取第一条规划路径的距离
            path = data["route"]["paths"][0]
            distance = float(path.get("distance", 0))
            return distance
        else:
            logging.error(f"Gaode API Error: {data.get('info')}, Code: {data.get('infocode')}")
            return None
            
    except Exception as e:
        logging.error(f"Gaode API Request Failed: {str(e)}")
        return None
