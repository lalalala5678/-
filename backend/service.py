import math
import random
import time

# 石家庄中心坐标
CITY_CENTER = [114.5149, 38.0428]

def get_outage_heatmap():
    """
    模拟获取断电概率热力图数据
    (从原前端 MockApiService 移植)
    """
    # 模拟网络延迟
    time.sleep(0.2)
    
    heat_points = []
    # 生成一些高热力区域中心
    centers = [
        {'x': 0.05, 'y': 0.05},
        {'x': -0.08, 'y': -0.02},
        {'x': 0.02, 'y': -0.08}
    ]

    for _ in range(120):
        # 围绕几个中心点随机分布
        center = random.choice(centers)
        lng = CITY_CENTER[0] + center['x'] + (random.random() - 0.5) * 0.1
        lat = CITY_CENTER[1] + center['y'] + (random.random() - 0.5) * 0.1

        heat_points.append({
            'lng': lng,
            'lat': lat,
            'count': math.floor(random.random() * 80) + 20 # 20-100 的基础热力值
        })
    
    return heat_points
