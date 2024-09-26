from flask import render_template, request, jsonify,redirect,current_app
from . import main
from .. import jwt


@jwt.unauthorized_loader
def missing_token_callback(error):
    return '401'

@main.app_errorhandler(403)
def forbidden(e):
    if request.accept_mimetypes.accept_json and \
            not request.accept_mimetypes.accept_html:
        response = jsonify({'error': 'forbidden'})
        response.status_code = 403
        return response
    return '403错误', 403


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



# 
# @main.app_errorhandler(404)
# def not_found(e):
#     print('拦截执行了')
#     return '404被拦截'