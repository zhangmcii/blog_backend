# flask 实例
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, get_jwt_identity, jwt_required, current_user
from flask_mail import Mail
from flask_redis import FlaskRedis
from config import config

app = Flask(__name__)
db = SQLAlchemy()
jwt = JWTManager()
mail = Mail()
redis = FlaskRedis()


def create_app(config_name):
    app = Flask(__name__)
    # 跨域
    CORS(app)

    # 读取配置
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    db.init_app(app)
    jwt.init_app(app)
    mail.init_app(app)
    redis.init_app(app)

    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint, url_prefix='/auth')

    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    from .api import api as api_blueprint
    app.register_blueprint(api_blueprint, url_prefix='/api/v1')

    from .models import User, Follow, Role, Permission
    from .fake import Fake

    return app

