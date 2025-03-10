from flask_jwt_extended import jwt_required, current_user, get_jwt_identity, decode_token
from . import main
from ..models import User, Role, Post, Permission, Comment, Follow, Praise, Log, Notification, NotificationType
from ..decorators import permission_required, admin_required, log_operate
from .. import db
from flask import jsonify, current_app, request, abort, url_for, redirect
from ..utils.time_util import DateUtils
from flask_sqlalchemy import record_queries
from ..fake import Fake
from .. import socketio
from flask_socketio import join_room, ConnectionRefusedError

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
@log_operate
def index():
    """处理博客文章的首页路由"""
    if request.method == 'POST' and current_user.can(Permission.WRITE):
        j = request.get_json()
        body_html = j.get('bodyHtml')
        post = Post(body=j.get('body'), body_html=body_html if body_html else None, author=current_user)
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
    post.body = j.get('body')
    post.body_html = j.get('bodyHtml') if j.get('bodyHtml') else None
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
    pagination = user.followers.order_by(Follow.timestamp.desc()).paginate(
        page=page, per_page=current_app.config['FLASKY_FOLLOWERS_PER_PAGE'],
        error_out=False)
    follows = []
    for item in pagination.items:
        if item.follower.username != username:
            is_following_back = Follow.query.filter_by(follower=user, followed=item.follower).first() is not None
            follows.append({
                'username': item.follower.username,
                'image': item.follower.image,
                'timestamp': DateUtils.datetime_to_str(item.timestamp),
                'is_following': is_following_back
            })
    return jsonify(data=follows, msg='success', total=user.followers.count() - 1)


@main.route('/followed_by/<username>')
def followed_by(username):
    # 关注者
    user = User.query.filter_by(username=username).first()
    if user is None:
        return jsonify(data='fail', msg="用户名不存在")
    page = request.args.get('page', 1, type=int)
    pagination = user.followed.order_by(Follow.timestamp.desc()).paginate(
        page=page, per_page=current_app.config['FLASKY_FOLLOWERS_PER_PAGE'],
        error_out=False)
    follows = []
    for item in pagination.items:
        if item.followed.username != username:
            is_following_back = Follow.query.filter_by(follower=item.followed, followed=user).first() is not None
            follows.append({
                'username': item.followed.username,
                'image': item.followed.image,
                'timestamp': DateUtils.datetime_to_str(item.timestamp),
                'is_following_back': is_following_back
            })
    return jsonify(data=follows, msg='success', total=user.followed.count() - 1)


@main.route('/can/<int:perm>')
@jwt_required(optional=True)
def can(perm):
    if (current_user):
        return jsonify(data=current_user.can(perm))
    return jsonify(data=False)


# --------------------------- 评论 ---------------------------
# get 评论已使用api中的
@main.route('/post/<int:id>', methods=['GET', 'POST'])
def post(id):
    """为文章提供固定链接、博客评论"""
    post = Post.query.get_or_404(id)
    if request.method == 'POST':
        # POST请求需要验证jwt
        jwt_required()
        j = request.get_json()
        comment = Comment(body=j.get('body'), post=post, author=current_user)
        # 父评论
        parent_comment_id = j.get('parentCommentId', None)
        if parent_comment_id:
            parent_comment = Comment.query.filter_by(id=parent_comment_id).first()
            comment = Comment(body=j.get('body'), post=post, author=current_user, parent_comment=parent_comment)
        # 将挂起的更改发送到数据库，但不会提交事务
        db.session.add(comment)
        db.session.flush()
        notification_post = Notification(receiver_id=post.author_id, trigger_user_id=comment.author_id, post_id=post.id,
                                    comment_id=comment.id, type=NotificationType.COMMENT)
        db.session.add(notification_post)
        if parent_comment_id:
            # 建议新的通知实例，通知回复的人
            notification_reply = Notification(receiver_id=parent_comment.author_id, trigger_user_id=comment.author_id,
                                              post_id=post.id,
                                              comment_id=comment.id, type=NotificationType.REPLY)
            db.session.add(notification_reply)
        db.session.commit()
        socketio.emit('new_notification', notification_post.to_json(), to=str(post.author_id))  # 发送到作者的房间
        if parent_comment_id:
            socketio.emit('new_notification', notification_reply.to_json(), to=str(parent_comment.author_id))  # 发送到父评论的房间
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


@main.route('/user_posts')
@admin_required
@jwt_required()
def user_image():
    """批量生成用户和文章"""
    Role.insert_roles()
    Fake.users()
    Fake.posts()
    return jsonify(data='', msg='success')


@main.route('/image', methods=['POST'])
@jwt_required()
def add_user_and_post():
    """存储用户图像地址"""
    image = request.get_json().get('image')
    current_user.image = image
    db.session.add(current_user)
    db.session.commit()
    return jsonify(image=image, msg='success')


@main.route('/praise/<int:id>', methods=['GET', 'POST'])
@jwt_required()
def praise(id):
    """文章点赞"""
    post = Post.query.get_or_404(id)
    if request.method == 'POST':
        praise = Praise(post=post, author=current_user)
        db.session.add(praise)

        # 将挂起的更改发送到数据库，但不会提交事务
        if current_user.id != post.author_id:
            db.session.flush()
            notification = Notification(receiver_id=post.author_id, trigger_user_id=praise.author_id, post_id=post.id,
                                        comment_id=praise.id, type=NotificationType.LIKE)
            db.session.add(notification)
        db.session.commit()
        if current_user.id != post.author_id:
            socketio.emit('new_notification', notification.to_json(), to=str(post.author_id))  # 发送到作者的房间
        db.session.commit()
        return jsonify(praise_total=post.praise.count(), has_praised=True, msg='success', detail='')
    return jsonify(praise_toal=post.praise.count(), msg='success', detail='')


@main.route('/logs', methods=['GET'])
@admin_required
@jwt_required()
def logs():
    """处理博客文章的首页路由"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', current_app.config['FLASKY_LOG_PER_PAGE'], type=int)
    query = Log.query
    paginate = query.order_by(Log.operate_time.desc()).paginate(page=page,
                                                                per_page=per_page,
                                                                error_out=False)
    logs = paginate.items
    return jsonify(data=[log.to_json() for log in logs], total=query.count(), msg='success')


@main.route('/deleteLog', methods=['POST'])
@admin_required
@jwt_required()
def delete_log():
    try:
        ids = request.get_json().get('ids', [])
        if not ids:
            return
        Log.query.filter(Log.id.in_(ids)).delete()
        db.session.commit()
        return jsonify(data='', msg='success')
    except Exception:
        db.session.rollback()
        return jsonify(data='', msg='fail')


@main.route('/comm', methods=['POST'])
@jwt_required()
def create_comment():
    current_user_id = get_jwt_identity()
    # 通过WebSocket推送通知给作者
    socketio.emit('new_notification', {
        'type': 'comment',
        'message': f'用户{current_user_id}评论了你的文章',
        # 'article_id': article_id
    })  # 发送到作者的房间

    return jsonify({"message": "Comment created"}), 200


# 处理WebSocket连接
@socketio.on('connect')
@jwt_required(optional=True)
def handle_connect(auth):
    try:
        # 从Socket.IO连接中获取JWT（通常通过查询参数或头传递）
        token = request.args.get('token')
        if not token:
            raise ConnectionRefusedError('Unauthorized')
        raw_token = token.replace("Bearer ", "", 1)
        # 手动解码 Token
        decoded_token = decode_token(raw_token)
        current_user_id = decoded_token["sub"]

        # 检查用户是否存在
        if not User.query.get(current_user_id):
            raise ConnectionRefusedError("用户不存在")
        # 将用户加入以自身ID命名的房间
        join_room(str(current_user_id))
        u = User.query.get(current_user_id)
        print(f"用户 {u.username} connected to room")

    except Exception as e:
        print(f"WebSocket connection failed: {str(e)}")
        raise ConnectionRefusedError('Authentication failed')


# 处理WebSocket连接
@socketio.on('disconnect')
def handle_connect(reason):
    print(f'用户断开了', reason)


@main.route('/notification/unread')
@jwt_required()
def get_unread_notification():
    d = Notification.query.filter_by(receiver_id=current_user.id).order_by(Notification.created_at.desc()).all()
    return jsonify(data=[item.to_json() for item in d], msg='success')

@main.route('/notification/read', methods=['POST'])
@jwt_required()
def mark_read_notification():
    ids = request.get_json().get('ids',[])
    Notification.query.filter(Notification.id.in_(ids),Notification.receiver_id == current_user.id).update({'is_read':True}, synchronize_session=False)
    db.session.commit()
    return jsonify(data='', msg='success')