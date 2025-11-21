"""
调度优化服务模块
包含车辆选址调度的核心算法。
"""
import numpy as np
from utils import data_store
from utils.geo import haversine

def run_greedy_dispatch():
    """
    运行贪心算法进行车辆调度。
    目标：最小化 (断电需求 - 车辆支援)^2 的总和
    :return: 调度结果字典 {vehicle_id: spot_id}
    """
    parking_spots = data_store.parking_spots
    vehicles = data_store.vehicles
    outage_data = data_store.get_outage_data()

    if not parking_spots or not vehicles or not outage_data:
        raise ValueError("缺少必要数据（停车点、车辆或断电热力图）")

    # 1. 准备数据
    # 提取断电热力图的值作为"需求"
    grid_points = [{'lat': p[0], 'lng': p[1]} for p in outage_data]
    outage_values = [p[2] for p in outage_data]
    
    outage_arr = np.array(outage_values)
    # 归一化需求 (如果全是0则不变)
    if outage_arr.max() > 0:
        outage_norm = outage_arr / outage_arr.max()
    else:
        outage_norm = outage_arr

    # 2. 初始化状态
    # 重置车辆位置
    for v in vehicles:
        v['spot_id'] = None
    
    # 按照载荷降序排列车辆，优先调度大车
    sorted_vehicles = sorted(vehicles, key=lambda x: x['capacity'], reverse=True)
    
    assignments = {} # vehicle_id -> spot_id
    
    # 预计算所有停车点到所有网格点的距离矩阵
    # 格式: spot_distances[spot_id] = np.array([dist_to_grid_0, dist_to_grid_1, ...])
    spot_distances = {}
    for spot in parking_spots:
        dists = []
        for gp in grid_points:
            d = haversine(spot['lat'], spot['lng'], gp['lat'], gp['lng'])
            dists.append(d + 0.1) # 加 0.1 防止除零错误
        spot_distances[spot['id']] = np.array(dists)

    current_support_raw = np.zeros(len(grid_points))
    available_spots = set(s['id'] for s in parking_spots)
    
    # 3. 贪心迭代
    for vehicle in sorted_vehicles:
        best_spot_id = None
        min_loss = float('inf')
        
        # 尝试将当前车辆放入每一个候选停车点
        for spot_id in list(available_spots):
            # 计算增量支援
            # 支援力模型: Capacity / Distance
            contribution = vehicle['capacity'] / spot_distances[spot_id]
            
            # 叠加到当前总支援
            temp_support_raw = current_support_raw + contribution
            
            # 归一化支援 (为了与 Demand 比较形状)
            if temp_support_raw.max() > 0:
                temp_support_norm = temp_support_raw / temp_support_raw.max()
            else:
                temp_support_norm = temp_support_raw
                
            # 计算损失函数: Sum((Demand - Supply)^2)
            loss = np.sum((outage_norm - temp_support_norm)**2)
            
            if loss < min_loss:
                min_loss = loss
                best_spot_id = spot_id
        
        # 确认分配
        if best_spot_id is not None:
            assignments[vehicle['id']] = best_spot_id
            # 更新当前的总支援状态
            current_support_raw += vehicle['capacity'] / spot_distances[best_spot_id]
            
            # 更新内存中的车辆状态
            for v in vehicles:
                if v['id'] == vehicle['id']:
                    v['spot_id'] = best_spot_id
                    break
                    
    return assignments
