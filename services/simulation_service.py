"""
模拟服务模块
负责生成断电模拟数据和计算车辆支援覆盖情况。
"""
import random
import numpy as np
from config import SHIJIAZHUANG_BOUNDS, GRID_SIZE
from utils.geo import generate_grid_points, haversine
from utils import data_store

def generate_outage_heatmap():
    """
    生成模拟的断电概率热力图（高斯分布）
    :return: 处理后的热力图数据列表 [[lat, lng, intensity], ...]
    """
    # 随机生成几个高斯中心（故障高发区）
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
    
    # 1. 计算原始叠加值
    for point in grid:
        val = 0
        for blob in blobs:
            dist_sq = (point['lat'] - blob['lat'])**2 + (point['lng'] - blob['lng'])**2
            val += blob['intensity'] * np.exp(-dist_sq / (2 * blob['sigma']**2))
        raw_data.append({'lat': point['lat'], 'lng': point['lng'], 'val': val})
    
    # 2. 归一化前准备
    max_val = max([d['val'] for d in raw_data]) if raw_data else 1.0
    if max_val == 0: max_val = 1.0
    
    # 3. 动态缩放
    # 根据网格密度动态调整强度系数，防止前端显示过曝
    dynamic_scale = 15.0 / GRID_SIZE 
    
    final_data = []
    for item in raw_data:
        normalized_val = (item['val'] / max_val) * dynamic_scale
        if normalized_val > 0.001:
             final_data.append([item['lat'], item['lng'], float(normalized_val)])
            
    # 存入 Data Store 供后续调度算法使用
    data_store.set_outage_data(final_data)
    
    return final_data

def calculate_support_heatmap():
    """
    根据当前车辆调度位置，计算支援能力热力图
    :return: 热力图数据列表 [[lat, lng, intensity], ...]
    """
    vehicles = data_store.vehicles
    outage_data = data_store.get_outage_data()
    parking_spots = data_store.parking_spots
    
    if not vehicles or not outage_data:
        return []
        
    # 复用断电热力图的网格点作为评估基础
    grid_points = [{'lat': p[0], 'lng': p[1]} for p in outage_data]
    
    total_support = np.zeros(len(grid_points))
    
    # 获取已停放的车辆
    active_vehicles = [v for v in vehicles if v['spot_id'] is not None]
    if not active_vehicles:
         return []

    # 构建停车点索引
    spot_map = {s['id']: s for s in parking_spots}

    for v in active_vehicles:
        spot = spot_map.get(v['spot_id'])
        if not spot: continue
        
        # 计算该车对所有网格点的支援力（距离衰减）
        dists = []
        for gp in grid_points:
            d = haversine(spot['lat'], spot['lng'], gp['lat'], gp['lng'])
            dists.append(d + 0.1) # 防止除以零
        dists = np.array(dists)
        
        total_support += v['capacity'] / dists
        
    # 归一化与动态缩放
    dynamic_scale = 15.0 / GRID_SIZE
    
    if total_support.max() > 0:
        total_support = (total_support / total_support.max()) * dynamic_scale
        
    data = []
    for i, val in enumerate(total_support):
        if val > 0.001:
            data.append([grid_points[i]['lat'], grid_points[i]['lng'], float(val)])
            
    return data
