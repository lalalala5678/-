"""
主程序入口
负责初始化 Flask 应用并注册各个模块的蓝图。
"""
from flask import Flask
from routes.view_routes import view_bp
from routes.api_routes import api_bp

def create_app():
    app = Flask(__name__)
    
    # 注册蓝图
    # view_bp 处理 / 和 /plan_route
    app.register_blueprint(view_bp)
    
    # api_bp 处理 /api/*
    app.register_blueprint(api_bp)
    
    return app

if __name__ == '__main__':
    app = create_app()
    print("启动电力车智能调度系统...")
    print("访问地址: http://127.0.0.1:5000")
    app.run(debug=True, port=5000)