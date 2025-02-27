from functools import wraps
from xmlrpc.client import DateTime

from flask import abort, request
from flask_jwt_extended import current_user
from .models import Permission, Log
from . import db
from .utils.time_util import DateUtils


def permission_required(permission):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.can(permission):
                abort(403)
            return f(*args, **kwargs)

        return decorated_function

    return decorator


def admin_required(f):
    return permission_required(Permission.ADMIN)(f)


def log_operate(f):
    def decorate(*args, **kwargs):
        if request.args.get('page', 1, type=int) != 1:
            return f(*args, **kwargs)

        # 用户身份信息
        is_register = True if current_user else False
        username = current_user.username if is_register else '游客'
        client_ip = request.remote_addr

        # 构建查询条件
        log_filter = {'username': username}
        if not is_register:
            log_filter = {'ip': client_ip}

        # 获取最近访问记录
        last_visit = Log.query.filter_by(**log_filter).order_by(Log.operate_time.desc()).first()

        # 判断访问间隔
        now = DateUtils.now_time()
        should_log = not last_visit or DateUtils.datetime_diff(now,
                                                               DateUtils.datetime_to_str(last_visit.operate_time), 5)

        # 记录日志
        if should_log:
            db.session.add(Log(username=current_user.username if current_user else '游客', operate='访问首页',
                               ip=request.remote_addr))
            db.session.commit()
        return f(*args, **kwargs)

    return decorate
