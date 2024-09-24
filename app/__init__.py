# flask 实例
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager, create_access_token, get_jwt_identity, jwt_required, current_user
from datetime import timedelta

app = Flask(__name__)
db = SQLAlchemy()
jwt = JWTManager()
migrate = Migrate()


def create_app():
    app = Flask(__name__)
    # 跨域
    CORS(app)
    app.config["SQLALCHEMY_DATABASE_URI"] = 'mysql+pymysql://root:1234@localhost:3306/backend_flask?charset=utf8'
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = 'my_flask'
    app.config["JWT_SECRET_KEY"] = "super-secret"
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(seconds=60*20)
    app.config["FLASKY_ADMIN"] = "zmc_li@foxmail.com"
    app.config["FLASk"] = "zmc_li@foxmail.com"
    app.config["FLASKY_POSTS_PER_PAGE"] = 10
    app.config["FLASKY_FOLLOWERS_PER_PAGE"] = 10
    app.config["FLASKY_COMMENTS_PER_PAGE"] = 10
    db.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)
    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint, url_prefix='/auth')

    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    from .api import api as api_blueprint
    app.register_blueprint(api_blueprint, url_prefix='/api/v1')

    from .models import User, Follow, Role, Permission
    from .fake import Fake
    @app.shell_context_processor
    def make_shell_context():
        return dict(db=db, User=User, Follow=Follow, Role=Role, Permission=Permission, Fake=Fake)

    @app.route("/logined")
    @jwt_required()
    def echo():
        current_usr = get_jwt_identity()
        return jsonify(login_in_as=current_usr), 200

    @app.route("/protected")
    @jwt_required()
    def protected():
        return jsonify(id=current_user.id,
                       password=current_user.password_hash,
                       username=current_user.name), 200

    @app.errorhandler(404)
    def address_404(e):
        return "未找到资源", 404

    @app.errorhandler(500)
    def address_500(e):
        return "服务端异常", 500

    return app
