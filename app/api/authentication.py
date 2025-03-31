from . import api
from flask_jwt_extended import verify_jwt_in_request
from flask import request, jsonify
import re

skip_post_pattern = r'^/api/v1/posts/.*$'


@api.before_request
def auth():
    try:
        # 对/api/v1/posts开头的请求放行
        if re.match(skip_post_pattern, request.path):
            return
        else:
            verify_jwt_in_request()
    except Exception:
        return jsonify({'message': 'Unauthorized'}), 401
