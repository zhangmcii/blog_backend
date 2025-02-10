from . import main
from .. import jwt
from flask import request, jsonify


@jwt.unauthorized_loader
def missing_token_callback(error):
    return jsonify(msg='token无效'), 401


@main.app_errorhandler(403)
def forbidden(e):
    if request.accept_mimetypes.accept_json and \
            not request.accept_mimetypes.accept_html:
        response = jsonify({'error': 'forbidden'})
        response.status_code = 403
        return response
    return '权限不足', 403


@main.app_errorhandler(404)
def page_not_found(e):
    print('404错误，已拦截!')
    if request.accept_mimetypes.accept_json and \
            not request.accept_mimetypes.accept_html:
        response = jsonify({'error': 'not found'})
        response.status_code = 404
        return response
    return '404错误', 404


@main.app_errorhandler(500)
def internal_server_error(e):
    if request.accept_mimetypes.accept_json and \
            not request.accept_mimetypes.accept_html:
        response = jsonify({'error': 'internal server error'})
        response.status_code = 500
        return response
    return '500错误', 500
