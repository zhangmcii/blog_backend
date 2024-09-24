from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, create_access_token, get_jwt_identity, jwt_required, current_user, \
    verify_jwt_in_request
from . import auth
from ..models import User


@auth.route('/login', methods=['post'])
def login():
    j = request.get_json()
    user = User.query.filter_by(username=j.get('uiAccountName')).one_or_none()
    if user:
        if user.verify_password(j.get('uiPassword')):
            token = create_access_token(identity=user,expires_delta=False)
            user.ping()
            return jsonify(msg="登录成功", token='Bearer ' + token, username=user.username, admin=user.is_administrator()), 200
    return jsonify(msg="登陆失败")


@auth.before_app_request
@jwt_required(optional=True)
def before_request():
    if current_user:
        current_user.ping()
        # if not current_user.confirmed and request.endpoint and request.blueprint != 'auth' and request.endpoint != 'static':
        #     return '用户邮件未认证'

# 用户资料编辑

# 管理员资料编辑
