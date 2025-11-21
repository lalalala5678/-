"""
地理计算工具模块
包含距离计算和网格生成等函数。
"""
import math
import numpy as np
from config import SHIJIAZHUANG_BOUNDS, GRID_SIZE

def haversine(lat1, lon1, lat2, lon2):
    """
    计算地球上两点间的直线距离（Haversine公式）
    :return: 距离 (单位: km)
    """
    R = 6371  # 地球半径 (km)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

def generate_grid_points():
    """
    生成覆盖石家庄区域的网格点
    :return: list of {'lat': float, 'lng': float}
    """
    lats = np.linspace(SHIJIAZHUANG_BOUNDS['min_lat'], SHIJIAZHUANG_BOUNDS['max_lat'], GRID_SIZE)
    lngs = np.linspace(SHIJIAZHUANG_BOUNDS['min_lng'], SHIJIAZHUANG_BOUNDS['max_lng'], GRID_SIZE)
    grid = []
    for lat in lats:
        for lng in lngs:
            grid.append({'lat': lat, 'lng': lng})
    return grid
