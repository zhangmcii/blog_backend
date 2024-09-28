from flask import request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, current_user

from . import auth
from ..models import User
from .. import db
from ..email import send_email


@auth.before_app_request
@jwt_required(optional=True)
def before_request():
    if current_user:
        current_user.ping()
        # if not current_user.confirmed and request.endpoint and request.blueprint != 'auth' and request.endpoint != 'static':
        #     return '用户邮件未认证'


@auth.route('/login', methods=['post'])
def login():
    j = request.get_json()
    user = User.query.filter_by(username=j.get('uiAccountName')).one_or_none()
    if user:
        if user.verify_password(j.get('uiPassword')):
            token = create_access_token(identity=user, expires_delta=False)
            user.ping()
            return jsonify(msg="登录成功", token='Bearer ' + token, username=user.username,
                           admin=user.is_administrator(), roleId=user.role_id, isConfirmed=user.confirmed), 200
    return jsonify(msg="登陆失败")


@auth.route('/register', methods=['POST'])
def register():
    print('执行了')
    j = request.get_json()
    u = User.query.filter_by(username=j.get('username')).first()
    if u:
        return jsonify(data='', msg='fail', detail='该用户名已被注册，请换一个')
    user = User(email=j.get('email'), username=j.get('username'), password=j.get('password'))
    db.session.add(user)
    db.session.commit()
    return jsonify(data='', msg='success', detail='')


@auth.route('/applyCode', methods=['POST'])
@jwt_required(optional=True)
def apply_code():
    email = request.get_json().get('email')
    action = request.get_json().get('action')
    if action == 'confirm' and User.query.filter_by(email=email).first():
        return jsonify(data='', msg='fail', detail='填写的邮箱已经存在')
    if action == 'confirm' and current_user.email and email != current_user.email:
        return jsonify(data='', msg='fail', detail='请输入该用户的正确的邮件')
    if (action == 'confirm' or action == 'change') and not current_user.email:
        current_user.email = request.get_json().get('email')
        db.session.add(current_user)
        db.session.commit()
    code = User.generate_code(email)
    # 重置密码
    send_email(email, 'Confirm Your Account',
               '', user={'username': 'User'} if action == 'reset' else current_user, code=code)
    return jsonify(data='', msg='success')


@auth.route('/confirm', methods=['POST'])
@jwt_required()
def confirm():
    email = request.get_json().get('email')
    code = request.get_json().get('code')
    if current_user.email and email != current_user.email:
        return jsonify(data='', msg='fail', detail='输入的邮件与用户的邮件不一致')
    if current_user.confirm(email, code):
        db.session.commit()
        return jsonify(data='', msg='success')
    return jsonify(data='', msg='fail', detail='绑定失败')


@auth.route('/changeEmail', methods=['POST'])
@jwt_required()
def change_email():
    email = request.get_json().get('email')
    code = request.get_json().get('code')
    password = request.get_json().get('password')
    if User.query.filter_by(email=email).first():
        return jsonify(data='', msg='fail', detail='填写的邮箱已经存在')
    if current_user.email == email:
        return jsonify(data='', msg='fail', detail='请更换新的邮箱地址')
    # 密码
    if not current_user.verify_password(password):
        return jsonify(data='', msg='fail', detail='密码错误')
    # 验证码
    if current_user.change_email(email, code):
        db.session.commit()
        return jsonify(data='', msg='success', detail='')
    return jsonify(data='', msg='fail', detail='验证码错误')


@auth.route('/changePassword', methods=['POST'])
@jwt_required()
def change_password():
    oldPassword = request.get_json().get('oldPassword')
    newPassword = request.get_json().get('newPassword')
    if current_user.verify_password(oldPassword):
        current_user.password = newPassword
        db.session.add(current_user)
        db.session.commit()
        return jsonify(data='', msg='success', detail='')
    return jsonify(data='', msg='fail', detail='密码错误')


@auth.route('/resetPassword', methods=['POST'])
def reset_password():
    email = request.get_json().get('email')
    code = request.get_json().get('code')
    password = request.get_json().get('password')
    print(request.get_json())
    # 验证码
    if User.compare_code(email, code):
        user = User.query.filter_by(email=email).first()
        if not user:
            return jsonify(data='', msg='fail', detail='此邮箱尚未绑定')
        print(user)
        user.password = password
        db.session.add(user)
        db.session.commit()
        return jsonify(data='', msg='success', detail='')
    return jsonify(data='', msg='fail', detail='验证码错误')
