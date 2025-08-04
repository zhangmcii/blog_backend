from flask import jsonify, request, current_app, url_for
from . import api
from ..models import User, Post, Follow
from flask_jwt_extended import current_user, jwt_required
from .. import db
from ..utils.common import get_avatars_url


@api.route('/users/<int:id>')
def get_user(id):
    user = User.query.get_or_404(id)
    return jsonify(data=user.to_json(), msg='success')


@api.route('/users/<int:id>/posts/')
def get_user_posts(id):
    user = User.query.get_or_404(id)
    page = request.args.get('page', 1, type=int)
    pagination = user.posts.order_by(Post.timestamp.desc()).paginate(
        page=page, per_page=current_app.config['FLASKY_POSTS_PER_PAGE'],
        error_out=False)
    posts = pagination.items
    prev = None
    if pagination.has_prev:
        prev = url_for('api.get_user_posts', id=id, page=page - 1)
    next = None
    if pagination.has_next:
        next = url_for('api.get_user_posts', id=id, page=page + 1)
    return jsonify({
        'posts': [post.to_json() for post in posts],
        'prev': prev,
        'next': next,
        'count': pagination.total
    })


@api.route('/users/<int:id>/timeline/')
def get_user_followed_posts(id):
    user = User.query.get_or_404(id)
    page = request.args.get('page', 1, type=int)
    pagination = user.followed_posts.order_by(Post.timestamp.desc()).paginate(
        page=page, per_page=current_app.config['FLASKY_POSTS_PER_PAGE'],
        error_out=False)
    posts = pagination.items
    prev = None
    if pagination.has_prev:
        prev = url_for('api.get_user_followed_posts', id=id, page=page - 1)
    next = None
    if pagination.has_next:
        next = url_for('api.get_user_followed_posts', id=id, page=page + 1)
    return jsonify({
        'posts': [post.to_json() for post in posts],
        'prev': prev,
        'next': next,
        'count': pagination.total
    })


# 在关注列表中，根据用户昵称或者账号搜索
@api.route('/search_followed', methods=['GET'])
def search_followed():
    search_query = request.args.get('name', '').strip()
    # 关注者
    user = User.query.filter_by(username=current_user.username).first()
    if not user:
        return jsonify(data='', msg="用户不存在")

    followed_user_ids = user.followed.with_entities(Follow.followed_id).all()
    followed_user_ids = [item[0] for item in followed_user_ids]
    # 搜索用户名或账号
    followed_users = User.query.filter(
        User.id.in_(followed_user_ids),
        db.or_(
            User.username.ilike(f'%{search_query}%'),
            User.nickname.ilike(f'%{search_query}%')
        )
    ).all()
    follows = [{'username': item.username, 'image': get_avatars_url(item.image)}
               for item in followed_users if item.username != user.username]
    return jsonify(data=follows, msg='success')


@api.route('/search_fan', methods=['GET'])
def search_fan():
    search_query = request.args.get('name', '').strip()
    # 粉丝
    user = User.query.filter_by(username=current_user.username).first()
    if not user:
        return jsonify(data='', msg="用户不存在")

    followed_user_ids = user.followers.with_entities(Follow.follower_id).all()
    followed_user_ids = [item[0] for item in followed_user_ids]
    # 搜索用户名或账号
    followed_users = User.query.filter(
        User.id.in_(followed_user_ids),
        db.or_(
            User.username.ilike(f'%{search_query}%'),
            User.nickname.ilike(f'%{search_query}%')
        )
    ).all()
    follows = [{'username': item.username, 'image': get_avatars_url(item.image)}
               for item in followed_users if item.username != user.username]
    return jsonify(data=follows, msg='success')


@api.route('/update_user', methods=['POST'])
@jwt_required()
def update_user_profile():
    for key, value in request.json.items():
        if hasattr(current_user, key):
            setattr(current_user, key, value)
    db.session.commit()
    return jsonify(data='', msg='success', detail='')
