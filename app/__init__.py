from flask import Flask, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, current_user
from flask_mail import Mail
from flask_redis import FlaskRedis
from flask_socketio import SocketIO
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from config import config
from .mycelery import celery_init_app
from dotenv import load_dotenv
import os

def my_key_func():
    """根据当前用户id限速"""
    return current_user.id if current_user else get_remote_address

db = SQLAlchemy()
jwt = JWTManager()
mail = Mail()
redis = FlaskRedis()
socketio = SocketIO()
limiter = Limiter(my_key_func, storage_uri=f'redis://:1234@{os.getenv('REDIS_HOST') or os.getenv('FLASK_RUN_HOST')}:6379/3')

def create_app(config_name):
    app = Flask(__name__)
    # 跨域
    CORS(app)

    # 执行celery启动命令时，需要加载环境变量
    if not os.getenv('APP_RUN'):
        # 获取当前文件的绝对路径
        current_file_path = os.path.abspath(__file__)
        # 获取当前文件所在目录的路径
        current_dir_path = os.path.dirname(current_file_path)
        # 获取父目录的路径
        parent_dir_path = os.path.dirname(current_dir_path)
        dotenv_path = os.path.join(parent_dir_path, '.env')
        if os.path.exists(dotenv_path):
            load_dotenv(dotenv_path)

    # 读取配置
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    host = os.getenv('REDIS_HOST') or os.getenv('FLASK_RUN_HOST')
    app.config.from_mapping(
        CELERY=dict(
            broker_url=f'redis://:1234@{host}:6379/1',
            result_backend=f'redis://:1234@{host}:6379/2',
        ),
    )

    db.init_app(app)
    jwt.init_app(app)
    mail.init_app(app)
    redis.init_app(app, decode_responses=True)
    celery_init_app(app)
    socketio.init_app(app, cors_allowed_origins="*", ping_timeout=30, ping_interval=60)
    limiter.init_app(app)

    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint, url_prefix='/auth')

    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    from .api import api as api_blueprint
    app.register_blueprint(api_blueprint, url_prefix='/api/v1')

    @app.errorhandler(Exception)
    def error_handler(e):
        if os.environ.get('FLASK_DEBUG', None):
            print(e)
        return jsonify(error=str(e)), 500

    return app
