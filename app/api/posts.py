import os

from flask import jsonify, request, url_for, current_app, abort
from flask_jwt_extended import current_user, jwt_required
from .. import db
from ..models import Post, Permission, PostType
from . import api
from ..main.views import del_qiniu_image


@api.route('/posts/')
def get_posts():
    page = request.args.get('page', 1, type=int)
    pagination = Post.query.paginate(
        page=page, per_page=current_app.config['FLASKY_POSTS_PER_PAGE'],
        error_out=False)
    posts = pagination.items
    prev = None
    if pagination.has_prev:
        prev = url_for('api.get_posts', page=page - 1)
    next = None
    if pagination.has_next:
        next = url_for('api.get_posts', page=page + 1)
    return jsonify({
        'posts': [post.to_json() for post in posts],
        'prev': prev,
        'next': next,
        'count': pagination.total
    })


@api.route('/posts/<int:id>')
def get_post(id):
    post = Post.query.get_or_404(id)
    return jsonify(data=post.to_json(), msg='success')


@api.route('/posts/', methods=['POST'])
def new_post():
    post = Post.from_json(request.json)
    post.author = current_user
    db.session.add(post)
    db.session.commit()
    return jsonify(post.to_json())


@api.route('/posts/<int:id>', methods=['PUT'])
@jwt_required()
def edit_post(id):
    post = Post.query.get_or_404(id)
    if current_user.username != post.author.username and not current_user.can(Permission.ADMIN):
        abort(403)
    # 对表单编辑业务逻辑
    j = request.get_json()
    post.body = j.get('body', post.body)
    post.body_html = j.get('bodyHtml') if j.get('bodyHtml') else None
    db.session.add(post)
    db.session.commit()
    return jsonify(data=post.to_json(), msg="success")


@api.route('/posts/<int:id>', methods=['DELETE'])
@jwt_required()
def del_post(id):
    # 删除文章，同时也要删除文章中的图片url
    is_contain_image, data = None, None
    try:
        p = Post.query.filter_by(id=id, author_id=current_user.id).first()
        is_contain_image = p.type == PostType.IMAGE
        if is_contain_image:
            # 删除图片
            data = {'bucket_name': os.getenv('QINIU_BUCKET_NAME',''), 'key': p.images.split(';') if p.images else []}
        db.session.delete(p)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify(data='', msg='fail', detail=str(e))
    if is_contain_image:
        # 传递j,执行图片删除
        del_qiniu_image(**data)
    return jsonify(data='', msg='success', detail='')
