"""
API 路由模块
定义与前端交互的所有 JSON 接口。
"""
from flask import Blueprint, request, jsonify
from utils import data_store
from services import simulation_service, optimization_service, map_service

api_bp = Blueprint('api', __name__, url_prefix='/api')

# --- 停车点管理 ---

@api_bp.route('/spots', methods=['GET', 'POST'])
def handle_spots():
    if request.method == 'POST':
        data = request.json
        spot = data_store.add_spot(data['lat'], data['lng'])
        return jsonify({'success': True, 'spot': spot})
    return jsonify({'spots': data_store.parking_spots})

@api_bp.route('/spots/clear', methods=['POST'])
def clear_spots():
    data_store.clear_spots()
    return jsonify({'success': True})

# --- 车辆管理 ---

@api_bp.route('/vehicles', methods=['GET', 'POST'])
def handle_vehicles():
    if request.method == 'POST':
        data = request.json
        count = int(data.get('count', 1))
        capacity = float(data.get('capacity', 100.0))
        new_vehicles = data_store.add_vehicles(count, capacity)
        return jsonify({'success': True, 'vehicles': new_vehicles})
    return jsonify({'vehicles': data_store.vehicles})

@api_bp.route('/vehicles/clear', methods=['POST'])
def clear_vehicles():
    data_store.clear_vehicles()
    return jsonify({'success': True})

# --- 热力图 ---

@api_bp.route('/heatmap/outage/generate', methods=['POST'])
def generate_outage_heatmap():
    try:
        data = simulation_service.generate_outage_heatmap()
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/heatmap/outage', methods=['GET'])
def get_outage_heatmap():
    return jsonify({'data': data_store.get_outage_data()})

@api_bp.route('/heatmap/support', methods=['GET'])
def get_support_heatmap():
    data = simulation_service.calculate_support_heatmap()
    return jsonify({'data': data})

# --- 调度优化 ---

@api_bp.route('/optimize', methods=['POST'])
def optimize_dispatch():
    try:
        assignments = optimization_service.run_greedy_dispatch()
        return jsonify({'success': True, 'assignments': assignments})
    except ValueError as ve:
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# --- 路径规划 (Map Service) ---

@api_bp.route('/plan_route', methods=['POST'])
def plan_route():
    # 注意：这里不是 /api/plan_route 而是要适配前端 fetch('/plan_route')，
    # 可以在 app.py 中注册 blueprint 时不加 prefix，或者这里单独处理。
    # 为了保持一致性，建议前端改用 /api/plan_route，但为了不改前端代码，
    # 我们可以在 app.py 注册一个单独的路由，或者在这里保持结构。
    # 假设我们在 app.py 中会将此 blueprint 注册在 /api 下。
    # 那么前端的 /plan_route 需要改为 /api/plan_route，
    # 或者我们创建一个不带前缀的 blueprint。
    pass 

# 这里单独定义一个不带前缀的路由蓝图，用于兼容旧的前端路径
# 或者更简单的，我们在 app.py 里处理路径规划路由，
# 或者在 view_routes 里处理。
# 最佳实践：统一 API 到 /api，这里我们先写逻辑。
