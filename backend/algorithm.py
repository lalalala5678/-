import math
import random
from backend.gaode_api import get_driving_distance

# 配置常量 (需与前端保持一致或由前端传入，这里先硬编码)
CITY_CENTER = [114.5149, 38.0428]
GRID_RESOLUTION = 50  # 提高网格分辨率以获得更细腻的热力图

class DispatchAlgorithm:
    def __init__(self):
        self.grid = []
        self.resolution = GRID_RESOLUTION
        # 初始化网格
        self.init_grid(CITY_CENTER)

    def init_grid(self, center):
        self.grid = []
        range_val = 0.15
        step = (2 * range_val) / self.resolution
        
        for i in range(self.resolution):
            for j in range(self.resolution):
                self.grid.append({
                    'lng': center[0] - range_val + step * i,
                    'lat': center[1] - range_val + step * j,
                    'outageProb': 0,
                    'supportValue': 0
                })

    def calculate_distance(self, p1, p2):
        """
        计算两点间距离 (Haversine formula)
        p1, p2: {'lat': float, 'lng': float}
        """
        R = 6371
        d_lat = (p2['lat'] - p1['lat']) * math.pi / 180
        d_lng = (p2['lng'] - p1['lng']) * math.pi / 180
        
        a = (math.sin(d_lat / 2) * math.sin(d_lat / 2) +
             math.cos(p1['lat'] * math.pi / 180) * 
             math.cos(p2['lat'] * math.pi / 180) * 
             math.sin(d_lng / 2) * math.sin(d_lng / 2))
        
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    def map_outage_to_grid(self, heat_points):
        """将热力点映射到网格上的断电概率"""
        for cell in self.grid:
            prob = 0
            for p in heat_points:
                # 计算网格中心到热力点的距离
                d = math.sqrt((cell['lng'] - p['lng'])**2 + (cell['lat'] - p['lat'])**2)
                
                # 距离衰减
                if d < 0.05:
                    prob += p['count'] * math.exp(-d * 100)
            
            cell['outageProb'] = prob
            
        self._normalize('outageProb')

    def calculate_total_support(self, vehicles):
        """计算所有车辆对网格的支援力度"""
        for cell in self.grid:
            support = 0
            for v in vehicles:
                if v.get('lng') is None or v.get('lat') is None:
                    continue
                
                dist = self.calculate_distance(
                    {'lng': v['lng'], 'lat': v['lat']},
                    {'lng': cell['lng'], 'lat': cell['lat']}
                )
                
                # 载荷越大，支援半径和强度越大
                # 修改为负指数衰减: load * exp(-dist * k)
                # 系数 k=1，衰减非常慢，使热力图呈现连片效果
                support += v['load'] * math.exp(-dist)
            
            cell['supportValue'] = support
        
        self._normalize('supportValue')

    def _normalize(self, field):
        """归一化网格字段"""
        values = [c[field] for c in self.grid]
        max_val = max(values) if values else 1
        min_val = min(values) if values else 0
        
        # 避免除以零
        val_range = max_val - min_val if max_val != min_val else 1
        
        for c in self.grid:
            c[field] = (c[field] - min_val) / val_range

    def calculate_loss(self):
        """计算损失函数"""
        loss = 0
        for cell in self.grid:
            diff = cell['outageProb'] - cell['supportValue']
            loss += diff**2
        return loss

    def get_support_heat_points(self):
        """获取前端渲染用的支援热力点"""
        points = []
        for cell in self.grid:
            # 过滤掉太小的值，减少传输量
            if cell['supportValue'] > 0.001:
                points.append({
                    'lng': cell['lng'],
                    'lat': cell['lat'],
                    'count': cell['supportValue'] * 100
                })
        return points

    def get_outage_heat_points(self):
        """获取前端渲染用的断电概率热力点 (基于网格)"""
        points = []
        for cell in self.grid:
            if cell['outageProb'] > 0.001:
                points.append({
                    'lng': cell['lng'],
                    'lat': cell['lat'],
                    'count': cell['outageProb'] * 100
                })
        return points

    def find_best_spots(self, vehicles, parking_spots):
        """
        寻找最优停车点 - 迭代贪心策略
        每一辆车选择能使当前总损失函数最小的停车点
        """
        if not parking_spots:
            return vehicles, 0, []

        # 1. 按载荷从大到小排序，优先安排大车
        sorted_vehicles = sorted(vehicles, key=lambda v: v['load'], reverse=True)
        
        # 用于存储已分配好位置的车辆
        placed_vehicles = []
        
        # 当前最佳状态的网格缓存 (初始状态为0)
        # 为了优化性能，我们不每次都重新计算所有已分配车辆的支援值
        # 而是维护一个 accumulation grid，每确定一辆车就叠加它的贡献
        current_support_grid = [0] * len(self.grid)

        # 预计算：所有停车点到所有网格的距离衰减系数
        # 格式: { spot_index: [ factor_for_cell_0, factor_for_cell_1, ... ] }
        # 这样在循环中就不必重复计算距离了
        spot_decay_factors = {}
        for idx, spot in enumerate(parking_spots):
            factors = []
            for cell in self.grid:
                # 这里暂时使用直线距离以保证计算速度
                # 如果必须用 API 驾车距离，那2500个网格点 * 停车点数会导致 API 请求爆炸
                # 建议：网格计算维持直线距离，仅在最终确认停车点可行性时考虑 API
                dist = self.calculate_distance(spot, {'lng': cell['lng'], 'lat': cell['lat']})
                # 支援模型: load * exp(-dist)
                # 保持与 calculate_total_support 一致
                factor = math.exp(-dist)
                factors.append(factor)
            spot_decay_factors[idx] = factors

        # 开始逐个分配车辆
        for vehicle in sorted_vehicles:
            best_spot = None
            min_loss = float('inf')
            best_support_contribution = [] # 暂存该车在最佳点的贡献值数组

            # 尝试每一个停车点
            for spot_idx, spot in enumerate(parking_spots):
                # 计算假设把车停在这里，产生的总支援分布
                # New = Current + Vehicle_Contribution
                trial_support_values = []
                contribution = []
                load = vehicle['load']
                
                for i in range(len(self.grid)):
                    val = load * spot_decay_factors[spot_idx][i]
                    contribution.append(val)
                    trial_support_values.append(current_support_grid[i] + val)
                
                # 计算 Loss
                # 注意：需要先归一化 trial_support_values
                # 为了性能，我们只针对 trial_support_values 做临时归一化
                max_val = max(trial_support_values) if trial_support_values else 1
                min_val = min(trial_support_values) if trial_support_values else 0
                rng = max_val - min_val if max_val != min_val else 1
                
                trial_loss = 0
                for i in range(len(self.grid)):
                    norm_support = (trial_support_values[i] - min_val) / rng
                    # 网格本身的 outageProb 已经是归一化过的 (在 map_outage_to_grid 中)
                    diff = self.grid[i]['outageProb'] - norm_support
                    trial_loss += diff**2
                
                if trial_loss < min_loss:
                    min_loss = trial_loss
                    best_spot = spot
                    best_support_contribution = contribution

            # 找到该车的最佳位置后，确定分配
            if best_spot:
                new_v = vehicle.copy()
                new_v['lat'] = best_spot['lat']
                new_v['lng'] = best_spot['lng']
                new_v['status'] = 'busy'
                placed_vehicles.append(new_v)
                
                # 更新累积网格状态
                for i in range(len(current_support_grid)):
                    current_support_grid[i] += best_support_contribution[i]

        # 所有车辆分配完毕，重新计算一次最终状态以更新 algorithm 内部的 grid
        self.calculate_total_support(placed_vehicles)
        final_loss = self.calculate_loss()
        support_heatmap = self.get_support_heat_points()
        
        return placed_vehicles, final_loss, support_heatmap

# 全局单例实例
dispatch_algorithm = DispatchAlgorithm()
