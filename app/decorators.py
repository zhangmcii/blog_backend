from functools import wraps
from flask import abort, request
from flask_jwt_extended import current_user
from .models import Permission, Log
from . import db


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
        if current_user:
            oplog = Log(username=current_user.username, operate='访问首页', ip=request.remote_addr)
        else:
            oplog = Log(username='游客', operate='访问首页', ip=request.remote_addr)
        db.session.add(oplog)
        db.session.commit()
        r = f(*args, **kwargs)
        return r

    return decorate
