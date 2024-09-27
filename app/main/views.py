from flask_jwt_extended import JWTManager, create_access_token, get_jwt_identity, jwt_required, current_user, \
    verify_jwt_in_request
from . import main
from ..models import User, Role, Post, Permission, Comment
from ..decorators import permission_required, admin_required
from .. import db
from flask import jsonify, current_app, request, abort, url_for, redirect
from ..utils.time_util import DateUtils
from flask_sqlalchemy import record_queries

"""编辑资料、博客文章、关注者信息、评论信息"""


@main.after_app_request
def after_request(response):
    for query in record_queries.get_recorded_queries():
        if query.duration >= current_app.config['FLASKY_SLOW_DB_QUERY_TIME']:
            current_app.logger.warning(
                'Slow query: %s\nParameters: %s\nDuration: %fs\nContext: %s\n'
                % (query.statement, query.parameters, query.duration,
                   query.context))
    return response


# --------------------------- 编辑资料 ---------------------------
@main.route('/edit-profile', methods=['POST'])
def edit_peofile():
    user_info = request.get_json()
    current_user.name = user_info.get('name')
    current_user.location = user_info.get('location')
    current_user.about_me = user_info.get('about_me')
    db.session.add(current_user)
    db.session.commit()
    return jsonify(data='success')


@main.route('/edit-profile/<int:id>', methods=['POST'])
@jwt_required()
@admin_required
def edit_peofile_admin(id):
    user = User.query.get_or_404(id)
    user_info = request.get_json()
    user.email = user_info.get('email')
    user.username = user_info.get('username')
    user.confirmed = user_info.get('confirmed')
    user.role = Role.query.get(int(user_info.get('role')))

    user.name = user_info.get('name')
    user.location = user_info.get('location')
    user.about_me = user_info.get('about_me')

    db.session.add(current_user)
    db.session.commit()
    return jsonify(data='success')


# --------------------------- 博客文章 ---------------------------
@main.route('/', methods=['GET', 'POST'])
def index():
    """处理博客文章的首页路由"""
    if request.method == 'POST' and current_user.can(Permission.WRITE):
        j = request.get_json()
        post = Post(body=j.get('content', None), author=current_user)
        db.session.add(post)
        db.session.commit()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', current_app.config['FLASKY_POSTS_PER_PAGE'], type=int)
    if request.args.get('tabName') == 'showFollowed':
        query = current_user.followed_posts
    else:
        query = Post.query
    paginate = query.order_by(Post.timestamp.desc()).paginate(page=page,
                                                              per_page=per_page,
                                                              error_out=False)
    posts = paginate.items
    return jsonify(data=[post.to_json() for post in posts], total=query.count(), msg='success')


@main.route('/user/<username>')
@jwt_required(optional=True)
def user(username):
    """获取博客文章的资料页面路由"""
    user = User.query.filter_by(username=username).first()
    if not user:
        abort(404)
    page = request.args.get('page', 1, type=int)
    pagination = user.posts.order_by(Post.timestamp.desc()).paginate(
        page=page, per_page=current_app.config['FLASKY_POSTS_PER_PAGE'],
        error_out=False)
    posts = pagination.items
    # 如果登录的用户时管理员，则会携带 电子邮件地址
    if current_user and current_user.is_administrator():
        return jsonify(data=user.to_json(user), posts=[post.to_json() for post in posts], total=user.posts.count(),
                       msg='success')
    j = user.to_json(user)
    j.pop('email', None)
    # j.pop('role', None)
    j.pop('confirmed', None)
    return jsonify(data=j, posts=[post.to_json() for post in posts], total=user.posts.count(), msg='success')


@main.route('/edit/<int:id>', methods=['GET', 'PUT'])
@jwt_required()
def edit(id):
    """编辑博客文章"""
    post = Post.query.get_or_404(id)
    if current_user.username != post.author.username and not current_user.can(Permission.ADMIN):
        abort(403)
    # 对表单编辑业务逻辑
    j = request.get_json()
    post.body = j.get('content')
    db.session.add(post)
    db.session.commit()
    return jsonify(data="success")


# --------------------------- 关注 ---------------------------

@main.route('/follow/<username>')
@jwt_required()
@permission_required(Permission.FOLLOW)
def follow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        return jsonify(data='fail', msg="用户名不存在")
    if current_user.is_following(user):
        return jsonify(data='fail', msg="你已经关注了该用户")
    current_user.follow(user)
    db.session.commit()
    return redirect(url_for('.user', username=username))


@main.route('/unfollow/<username>')
@jwt_required()
@permission_required(Permission.FOLLOW)
def unfollow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        return jsonify(data='fail', msg="用户名不存在")
    if not current_user.is_following(user):
        return jsonify(data='fail', msg="你未关注该用户")
    current_user.unfollow(user)
    db.session.commit()
    return redirect(url_for('.user', username=username))


@main.route('/followers/<username>')
def followers(username):
    # 粉丝
    user = User.query.filter_by(username=username).first()
    if user is None:
        return jsonify(data='fail', msg="用户名不存在")
    page = request.args.get('page', 1, type=int)
    pagination = user.followers.paginate(
        page=page, per_page=current_app.config['FLASKY_FOLLOWERS_PER_PAGE'],
        error_out=False)
    follows = [{'username': item.follower.username, 'timestamp': DateUtils.datetime_to_str(item.timestamp)}
               for item in pagination.items if item.follower.username != username]
    return jsonify(data=follows, msg='success')


@main.route('/followed_by/<username>')
def followed_by(username):
    # 关注者
    user = User.query.filter_by(username=username).first()
    if user is None:
        return jsonify(data='fail', msg="用户名不存在")
    page = request.args.get('page', 1, type=int)
    pagination = user.followed.paginate(
        page=page, per_page=current_app.config['FLASKY_FOLLOWERS_PER_PAGE'],
        error_out=False)
    follows = [{'username': item.followed.username, 'timestamp': DateUtils.datetime_to_str(item.timestamp)}
               for item in pagination.items if item.followed.username != username]
    return jsonify(data=follows, msg='success')


@main.route('/can/<int:perm>')
@jwt_required(optional=True)
def can(perm):
    if (current_user):
        return jsonify(data=current_user.can(perm))
    return jsonify(data=False)


# --------------------------- 评论 ---------------------------
@main.route('/post/<int:id>', methods=['GET', 'POST'])
def post(id):
    """为文章提供固定链接、博客评论"""
    post = Post.query.get_or_404(id)
    if request.method == 'POST':
        j = request.get_json()
        comment = Comment(body=j.get('body'), post=post, author=current_user)
        db.session.add(comment)
        db.session.commit()
        return redirect(url_for('.post', id=post.id, page=-1))
    page = request.args.get('page', 1, type=int)
    if page == -1:
        page = (post.comments.count() - 1) // current_app.config['FLASKY_COMMENTS_PER_PAGE'] + 1
    pagination = post.comments.order_by(Comment.timestamp.asc()).paginate(
        page=page, per_page=current_app.config['FLASKY_COMMENTS_PER_PAGE'],
        error_out=False)
    comments = [
        {'body': item.body, 'timestamp': DateUtils.datetime_to_str(item.timestamp), 'author': item.author.username,
         'disabled': item.disabled} for
        item in pagination.items]
    return jsonify(data=comments, total=post.comments.count(), currentPage=page, msg='success')


@main.route('/moderate')
@jwt_required()
@permission_required(Permission.MODERATE)
def moderate():
    """管理评论"""
    page = request.args.get('page', 1, type=int)
    query = Comment.query
    pagination = query.order_by(Comment.timestamp.desc()).paginate(
        page=page, per_page=current_app.config['FLASKY_COMMENTS_PER_PAGE'],
        error_out=False)
    comments = [
        {'body': item.body, 'timestamp': DateUtils.datetime_to_str(item.timestamp), 'author': item.author.username,
         'id': item.id, 'disabled': item.disabled} for
        item in pagination.items]
    return jsonify(data=comments, total=query.count(), msg='success')


@main.route('/moderate/enable/<int:id>')
@jwt_required()
@permission_required(Permission.MODERATE)
def moderate_enable(id):
    """恢复评论"""
    comment = Comment.query.get_or_404(id)
    comment.disabled = False
    db.session.add(comment)
    db.session.commit()
    return redirect(url_for('.moderate',
                            page=request.args.get('page', 1, type=int)))


@main.route('/moderate/disable/<int:id>')
@jwt_required()
@permission_required(Permission.MODERATE)
def moderate_disable(id):
    """禁用评论"""
    comment = Comment.query.get_or_404(id)
    comment.disabled = True
    db.session.add(comment)
    db.session.commit()
    return redirect(url_for('.moderate',
                            page=request.args.get('page', 1, type=int)))
