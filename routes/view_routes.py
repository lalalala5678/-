"""
视图路由模块
处理页面渲染和根路径相关的请求。
"""
from flask import Blueprint, render_template, request, jsonify
from services import map_service

view_bp = Blueprint('view', __name__)

@view_bp.route('/')
def index():
    return render_template('index.html')

@view_bp.route('/plan_route', methods=['POST'])
def plan_route():
    """
    兼容前端的路径规划接口
    """
    data = request.json
    origin = data.get('origin')
    destination = data.get('destination')

    if not origin or not destination:
        return jsonify({'error': 'Missing origin or destination'}), 400

    try:
        path, distance, duration = map_service.get_driving_route(origin, destination)
        return jsonify({
            'success': True,
            'path': path,
            'distance': distance,
            'duration': duration
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
