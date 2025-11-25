from flask import Flask, jsonify, request
from backend.service import get_outage_heatmap
from backend.algorithm import dispatch_algorithm
from backend.gaode_api import get_driving_distance
from backend.scheduler import run_schedule

app = Flask(__name__)

# 注意：前端使用 Vite 代理 (proxy) 转发 /api 请求到 5000 端口
# 因此这里不需要配置 CORS，除非前端和后端部署在不同域名下

@app.route('/api/schedule-deterministic', methods=['POST'])
def route_schedule_deterministic():
    """确定性停电调度"""
    data = request.json
    # data 结构: { tasks: [...], vehicles: [...], depots: [...] }
    if not data:
        return jsonify({'status': 'error', 'message': 'Empty body'}), 400
        
    result = run_schedule(data)
    if result.get('status') == 'error':
        return jsonify(result), 400
    return jsonify(result)

@app.route('/api/outage-heatmap', methods=['GET'])
def route_outage_heatmap():
    """获取断电概率热力图"""
    raw_data = get_outage_heatmap()
    # 1. 将原始数据映射到算法网格
    dispatch_algorithm.map_outage_to_grid(raw_data)
    # 2. 返回网格化的数据，确保前端显示的分辨率与算法一致
    grid_data = dispatch_algorithm.get_outage_heat_points()
    return jsonify(grid_data)

@app.route('/api/optimize', methods=['POST'])
def route_optimize():
    """执行车辆调度优化"""
    data = request.json
    vehicles = data.get('vehicles', [])
    parking_spots = data.get('parkingSpots', [])
    
    if not vehicles or not parking_spots:
        return jsonify({'error': 'Missing vehicles or parking spots'}), 400

    optimized_vehicles, loss, support_heatmap = dispatch_algorithm.find_best_spots(vehicles, parking_spots)
    
    return jsonify({
        'vehicles': optimized_vehicles,
        'loss': loss,
        'supportHeatmap': support_heatmap
    })

@app.route('/api/calculate-loss', methods=['POST'])
def route_calculate_loss():
    """计算当前状态的 Loss"""
    data = request.json
    vehicles = data.get('vehicles', [])
    
    dispatch_algorithm.calculate_total_support(vehicles)
    loss = dispatch_algorithm.calculate_loss()
    support_heatmap = dispatch_algorithm.get_support_heat_points()
    
    return jsonify({
        'loss': loss,
        'supportHeatmap': support_heatmap
    })

@app.route('/api/test-distance', methods=['POST'])
def route_test_distance():
    """测试高德 API 距离计算"""
    data = request.json
    origin = data.get('origin')
    destination = data.get('destination')
    
    if not origin or not destination:
        return jsonify({'error': 'Missing origin or destination'}), 400
        
    dist = get_driving_distance(origin, destination)
    if dist is None:
        return jsonify({'error': 'API Call Failed'}), 500
        
    return jsonify({'distance_meters': dist, 'distance_km': dist / 1000.0})

if __name__ == '__main__':
    app.run(debug=True, port=5000)