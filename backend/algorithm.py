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
                # 距离单位是 km
                support += v['load'] / (dist**2 + 0.1)
            
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

    def find_best_spots(self, vehicles, parking_spots):
        """
        寻找最优停车点 - 使用高德 API 计算真实驾车距离
        """
        if not parking_spots:
            return vehicles, 0, []

        # 简单的贪心分配：每辆车去最近的且还没被占用的停车点（这里简化为可重复停）
        # 为了演示 API 接入，我们将计算车辆当前位置(如果已知)到所有停车点的真实距离
        # 但由于车辆初始位置通常未知(为 None)，我们这里模拟：
        # 假设我们想要将车辆分配到能最大化覆盖高风险区域的停车点
        
        # 由于这是一个复杂的组合优化问题，我们这里采用简化策略：
        # 1. 找出断电概率最高的几个网格点 (Hotspots)
        # 2. 计算每个停车点到这些 Hotspots 的距离 (这里可以用直线距离近似，或者 API)
        # 3. 优先选择离 Hotspot 近的停车点
        
        # 第一步：找到最热的区域中心 (重心)
        max_prob_cell = max(self.grid, key=lambda c: c['outageProb'])
        hotspot_center = {'lng': max_prob_cell['lng'], 'lat': max_prob_cell['lat']}
        
        # 第二步：计算所有停车点到热点中心的真实驾车距离 (调用高德 API)
        # 注意：这会产生 len(parking_spots) 次 API 调用
        spot_scores = []
        for spot in parking_spots:
            # 调用 API 计算停车点到热点中心的距离
            # 注意：API返回的是米，转换成公里以匹配算法量级
            dist_meter = get_driving_distance(spot, hotspot_center)
            
            if dist_meter is not None:
                dist_km = dist_meter / 1000.0
            else:
                # 降级为直线距离
                dist_km = self.calculate_distance(spot, hotspot_center)
            
            # 距离越近，分数越高
            score = 1 / (dist_km + 0.1)
            spot_scores.append({'spot': spot, 'score': score})
            
        # 按分数排序
        spot_scores.sort(key=lambda x: x['score'], reverse=True)
        
        # 第三步：分配车辆
        optimized_vehicles = []
        for i, v in enumerate(vehicles):
            # 轮询分配给最好的几个停车点
            best_spot = spot_scores[i % len(spot_scores)]['spot']
            
            new_v = v.copy()
            new_v['lat'] = best_spot['lat']
            new_v['lng'] = best_spot['lng']
            new_v['status'] = 'busy'
            optimized_vehicles.append(new_v)
        
        # 计算新布局下的指标
        self.calculate_total_support(optimized_vehicles)
        loss = self.calculate_loss()
        support_heatmap = self.get_support_heat_points()
        
        return optimized_vehicles, loss, support_heatmap

# 全局单例实例
dispatch_algorithm = DispatchAlgorithm()
