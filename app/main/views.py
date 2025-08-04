import os

from flask_jwt_extended import jwt_required, current_user, get_jwt_identity, decode_token, verify_jwt_in_request
from . import main
from ..models import User, Role, Post, Permission, Comment, Follow, Praise, Log, Notification, NotificationType, \
    Message, PostType, Image, ImageType, Tag
from ..decorators import permission_required, admin_required, log_operate
from .. import db
from flask import jsonify, current_app, request, abort, url_for, redirect
from ..utils.time_util import DateUtils
from ..utils.socket_util import ManageSocket
from ..utils.text_filter import DFAFilter
from flask_sqlalchemy import record_queries
from sqlalchemy import and_
from ..fake import Fake
from .. import socketio
from .. import limiter
from werkzeug.exceptions import TooManyRequests
from ..event import *
from flask_socketio import disconnect
from flask_socketio import join_room, ConnectionRefusedError
from qiniu import Auth, BucketManager, build_batch_delete
import time
import os
import json
from ..utils.common import get_avatars_url

"""编辑资料、博客文章、关注者信息、评论信息"""

manage_socket = ManageSocket()
# 初始化Auth状态
q = Auth(os.getenv('QINIU_ACCESS_KEY'), os.getenv('QINIU_SECRET_KEY'))
# 初始化BucketManager
bucket = BucketManager(q)


# 记录查询慢的sql
# @main.after_app_request
# def after_request(response):
#     for query in record_queries.get_recorded_queries():
#         if query.duration >= current_app.config['FLASKY_SLOW_DB_QUERY_TIME']:
#             current_app.logger.warning(
#                 'Slow query: %s\nParameters: %s\nDuration: %fs\n'
#                 % (query.statement, query.parameters, query.duration))
#     return response


# --------------------------- 编辑资料 ---------------------------
@main.route('/edit-profile', methods=['POST'])
@jwt_required()
def edit_profile():
    user_info = request.get_json()
    current_user.nickname = user_info.get('nickname')
    current_user.location = user_info.get('location')
    current_user.about_me = user_info.get('about_me')
    db.session.add(current_user)
    db.session.commit()
    return jsonify(msg='success')


@main.route('/edit-profile/<int:id>', methods=['POST'])
@jwt_required()
@admin_required
def edit_profile_admin(id):
    user = User.query.get_or_404(id)
    user_info = request.get_json()
    user.email = user_info.get('email')
    user.username = user_info.get('username')
    user.confirmed = user_info.get('confirmed')
    user.role = Role.query.get(int(user_info.get('role')))

    user.nickname = user_info.get('nickname')
    user.location = user_info.get('location')
    user.about_me = user_info.get('about_me')

    db.session.add(current_user)
    db.session.commit()
    return jsonify(msg='success')


# --------------------------- 博客文章 ---------------------------
@main.route('/', methods=['GET', 'POST'])
@log_operate
def index():
    """处理博客文章的首页路由"""
    if request.method == 'POST' and current_user.can(Permission.WRITE):
        j = request.get_json()
        body_html = j.get('bodyHtml')
        images = j.get('images')
        post = Post(body=j.get('body'), body_html=body_html if body_html else None,
                    type=PostType.IMAGE if body_html else PostType.TEXT,
                    author=current_user)
        db.session.add(post)
        db.session.flush()
        if images:
            images = [
                Image(url=image.get('url', ''), type=ImageType.POST, describe=image.get('pos', ''), related_id=post.id)
                for image in images]
            db.session.add_all(images)
        db.session.commit()
        new_post_notification(post.id)
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


def new_post_notification(post_id):
    # 查询当前用户的所有粉丝（排除自己）
    followers = Follow.query.filter_by(followed_id=current_user.id).all()

    # 为每个粉丝创建通知并推送
    for follow in followers:
        # 跳过作者自己（虽然逻辑上自己不会关注自己，但以防万一）
        if follow.follower_id == current_user.id:
            continue

        # 创建通知
        notification = Notification(
            receiver_id=follow.follower_id,  # 粉丝ID
            trigger_user_id=current_user.id,  # 触发用户（作者）
            post_id=post_id,  # 关联文章ID
            type=NotificationType.NewPost  # 通知类型：新文章
        )
        db.session.add(notification)
        db.session.flush()  # 刷新以获取通知ID

        # 实时推送给粉丝
        socketio.emit(
            'new_notification',
            notification.to_json(),
            to=str(follow.follower_id)  # 发送到粉丝的房间
        )

    # 提交所有通知
    db.session.commit()


def get_user_data(username):
    """获取用户数据的公共逻辑"""
    user = User.query.filter_by(username=username).first()
    # 如果登录的用户时管理员，则会携带 电子邮件地址
    if current_user and current_user.is_administrator():
        return user.to_json()
    j = user.to_json()
    j.pop('email', None)
    j.pop('confirmed', None)
    return j


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
    return jsonify(posts=[post.to_json() for post in posts], total=user.posts.count(), msg='success')


@main.route('/users/<username>')
@jwt_required(optional=True)
def get_user_by_username(username):
    """根据用户名获取用户数据"""
    data = get_user_data(username)
    return jsonify(data=data, msg='success')


@main.route('/edit/<int:id>', methods=['GET', 'PUT'])
@jwt_required()
def edit(id):
    # PUT 文章已使用api中的
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
    data = get_user_data(username)
    return jsonify(data=data, msg='success')


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
    data = get_user_data(username)
    return jsonify(data=data, msg='success')


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
                'id': item.follower.id,
                'nickname': item.follower.nickname,
                'username': item.follower.username,
                'image': get_avatars_url(item.follower.image),
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
                'id': item.followed.id,
                'nickname': item.followed.nickname,
                'username': item.followed.username,
                'image': get_avatars_url(item.followed.image),
                'timestamp': DateUtils.datetime_to_str(item.timestamp),
                'is_following_back': is_following_back
            })
    return jsonify(data=follows, msg='success', total=user.followed.count() - 1)


@main.route('/can/<int:perm>')
@jwt_required(optional=True)
def can(perm):
    if current_user:
        return jsonify(data=current_user.can(perm))
    return jsonify(data=False)


# --------------------------- 评论 ---------------------------
@main.route('/post/<int:id>', methods=['POST'])
@limiter.limit("1/second;3/minute", exempt_when=lambda: current_user.role_id == 3)
@jwt_required()
def post(id):
    """发布评论（适配direct_parent关系）"""
    post = Post.query.get_or_404(id)
    verify_jwt_in_request()
    data = request.get_json()
    at = data.get('at')
    # 直接父id
    direct_parent_id = data.get('directParentId')
    try:
        direct_parent = None
        root_comment = None

        # 若是根评论，  则direct_parent=root_commentNone = None
        # 若是一级回复，则direct_parent=root_commentNone = 根评论对象
        # 若是其他回复，则direct_parent = 直接评论对象， root_commentNone = 根评论对象
        if direct_parent_id:
            # 直接父id
            direct_parent = Comment.query.get(direct_parent_id)
            # 获取根评论：如果父评论本身有根评论则继承，否则父评论就是根评论
            root_comment = direct_parent.root_comment if direct_parent.root_comment_id else direct_parent
        # 创建评论（设置两个父级关系）
        comment = Comment(
            body=DFAFilter().filter(data.get('body'), '*'),
            post=post,
            author=current_user,
            direct_parent=direct_parent,
            root_comment=root_comment
        )
        db.session.add(comment)
        db.session.flush()
        # 通知
        notifications = notice_by_comment_type(direct_parent, root_comment, post, comment, at)
        db.session.add_all(notifications)
        db.session.commit()
        # 实时推送
        for notification in notifications:
            socketio.emit(
                'new_notification',
                notification.to_json(),
                to=str(notification.receiver_id)
            )
        current_comment = {
            'id': comment.id,
            'parentId': comment.root_comment_id,
            'uid': current_user.id,
            'content': comment.body,
            'createTime': DateUtils.datetime_to_str(comment.timestamp),
            'user': {
                'username': current_user.nickname if current_user.nickname else current_user.username,
                'avatar': get_avatars_url(current_user.image)
            },
            'reply': ''
        }
        return jsonify(data=current_comment, msg='success', detail='')
    except TooManyRequests:
        raise
    except Exception as e:
        db.session.rollback()
        return jsonify(data='', total=0, currentPage=1, msg='fail', detail=str(e)), 500


def notice_by_comment_type(direct_parent, root_comment, post, comment, at_list):
    """
        根评论: 通知文章作者
        一级回复或其他回复: 不通知文章作者，仅通知被直接回复的用户
    """
    notifications = []
    # 根评论
    if not direct_parent and not root_comment:
        if current_user.id != post.author_id:
            notifications.append(Notification(
                receiver_id=post.author_id,
                trigger_user_id=current_user.id,
                post_id=post.id,
                comment_id=comment.id,
                type=NotificationType.COMMENT
            ))
    # 一级回复或其他回复
    else:
        if current_user.id != direct_parent.author_id:
            notifications.append(Notification(
                receiver_id=direct_parent.author_id,
                trigger_user_id=current_user.id,
                post_id=post.id,
                comment_id=comment.id,
                type=NotificationType.REPLY
            ))

    # @的通知
    for receiver_id in at_list:
        notifications.append(Notification(
            receiver_id=receiver_id,
            trigger_user_id=current_user.id,
            post_id=post.id,
            comment_id=comment.id,
            type=NotificationType.AT
        ))
    return notifications


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
    return jsonify(image=get_avatars_url(image), msg='success')


@main.route('/praise/<int:id>', methods=['GET', 'POST'])
def praise(id):
    """文章点赞"""
    post = Post.query.get_or_404(id)
    if request.method == 'POST':
        # POST 请求需要 JWT 验证
        verify_jwt_in_request()
        # 防止用户重复点赞
        p = Praise.query.filter_by(author_id=current_user.id, post_id=id).first()
        if p:
            return jsonify(data='', msg='fail', detail='您已经点赞过了~')
        praise = Praise(post=post, author=current_user)
        db.session.add(praise)
        try:
            # 将挂起的更改发送到数据库，但不会提交事务
            if current_user.id != post.author_id:
                db.session.flush()
                notification = Notification(receiver_id=post.author_id, trigger_user_id=praise.author_id,
                                            post_id=post.id,
                                            comment_id=None, type=NotificationType.LIKE)
                db.session.add(notification)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return jsonify(praise_total=0, msg='fail', detail=f'操作失败，已回滚.{str(e)}'), 500
        if current_user.id != post.author_id:
            socketio.emit('new_notification', notification.to_json(), to=str(post.author_id))  # 发送到作者的房间
        return jsonify(praise_total=post.praise.count(), has_praised=True, msg='success', detail='')
    return jsonify(praise_toal=post.praise.count(), msg='success', detail='')


@main.route('/praise/comment/<int:id>', methods=['GET', 'POST'])
def praise_comment(id):
    """文章点赞"""
    comment = Comment.query.get_or_404(id)
    if request.method == 'POST':
        # POST 请求需要 JWT 验证
        verify_jwt_in_request()
        praise = Praise(comment=comment, author=current_user)
        db.session.add(praise)
        try:
            # 将挂起的更改发送到数据库，但不会提交事务
            if current_user.id != comment.author_id:
                db.session.flush()
                notification = Notification(receiver_id=comment.author_id, trigger_user_id=praise.author_id,
                                            post_id=comment.post_id,
                                            comment_id=comment.id, type=NotificationType.LIKE)
                db.session.add(notification)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return jsonify(praise_total=0, msg='fail', detail=f'点赞操作失败，已回滚.{str(e)}'), 500
        if current_user.id != comment.author_id:
            socketio.emit('new_notification', notification.to_json(), to=str(comment.author_id))  # 发送到作者的房间
        return jsonify(praise_total=comment.praise.count(), msg='success', detail='')
    return jsonify(praise_toal=comment.praise.count(), msg='success', detail='')


@main.route('/has_praised/<int:post_id>')
def has_praised_comment_id(post_id):
    """查找某文章下当前用户已点赞的评论id"""
    comment_ids = db.session.query(Praise.comment_id).join(Comment).filter(
        Praise.author_id == current_user.id,
        Comment.post_id == post_id,
        Praise.comment_id.isnot(None)
    ).distinct().all()
    return jsonify(data=[item[0] for item in comment_ids], msg='success')


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


@main.route('/notification/unread')
@jwt_required()
def get_unread_notification():
    d = Notification.query.filter_by(receiver_id=current_user.id).order_by(Notification.created_at.desc()).all()
    return jsonify(data=[item.to_json() for item in d], msg='success')


@main.route('/notification/read', methods=['POST'])
@jwt_required()
def mark_read_notification():
    ids = request.get_json().get('ids', [])
    Notification.query.filter(Notification.id.in_(ids), Notification.receiver_id == current_user.id).update(
        {'is_read': True}, synchronize_session=False)
    db.session.commit()
    return jsonify(data='', msg='success')


@main.route('/socketData')
@admin_required
@jwt_required()
def online():
    # 在线人数信息
    user_ids = manage_socket.user_socket.keys()
    users = []
    for user_id in user_ids:
        u = User.query.get(user_id)
        users.append({'username': u.username, 'nickName': u.nickname})
    online_total = len(users)
    return jsonify(data=users, msg='success', total=online_total)


@main.route('/msg', methods=['GET'])
@jwt_required()
def get_message_history():
    current_user_id = current_user.id
    other_user_id = request.args.get('userId')
    page = request.args.get('page', 1, type=int)
    query = Message.query.filter(
        ((Message.sender_id == current_user_id) & (Message.receiver_id == other_user_id)) |
        ((Message.sender_id == other_user_id) & (Message.receiver_id == current_user_id))
    ).order_by(Message.timestamp.desc())
    pagination = query.paginate(
        page=page, per_page=current_app.config['FLASKY_CHAT_PER_PAGE'], error_out=False)
    messages = pagination.items
    r = []
    _id = len(messages)
    for message in messages:
        r1 = message.to_json()
        r1.update({'id': _id})
        r.append(r1)
        _id -= 1
    return jsonify(data=r, msg='success', total=pagination.total, detail='')


@main.route('/msg/read', methods=['POST'])
@jwt_required()
def mark_messages_read():
    message_ids = request.json.get('ids', [])
    Message.query.filter(
        Message.id.in_(message_ids),
        Message.receiver_id == current_user.id()
    ).update({'is_read': True}, synchronize_session=False)
    db.session.commit()
    return jsonify(data='', msg='success', detail='')


@main.route('/get_upload_token', methods=['GET'])
def get_upload_token():
    # 定义上传策略
    policy = {
        # 限制上传文件的最大尺寸，单位为字节，这里设置为 10MB
        'fsizeLimit': 10 * 1024 * 1024,
        # 设置上传凭证的有效期，单位为秒，这里设置为 1 小时
        'deadline': int(time.time()) + 3600,
        # 'callbackUrl': 'http://172.18.66.95:8082/upload_callback',
        # 'callbackBody':'filename=$(fname)&filesize=$(fsize)&blog_text=$(x:blog_text)',
        # 'callbackBodyType':'application/json'
    }
    # 生成上传凭证，传入上传策略
    token = q.upload_token(os.getenv('QINIU_BUCKET_NAME'), policy=policy)
    return jsonify({'upload_token': token})


@main.route('/get_signed_image_urls', methods=['POST'])
def get_signed_image_urls():
    """获取私有存储图片url(暂时没用上)"""
    data = request.get_json()
    keys = data.get('keys', [])
    if not keys:
        return jsonify({'error': 'Missing keys parameter'}), 400
    signed_urls = []
    for key in keys:
        # 添加图片瘦身参数，这里以调整图片质量为 80 为例
        fops = 'imageMogr2/quality/80'
        base_url = f'{os.getenv('QINIU_DOMAIN')}/{key}'
        # 拼接处理参数到基础 URL
        processed_url = base_url + '?' + fops
        # 生成带处理参数的签名 URL
        private_url = q.private_download_url(processed_url, expires=3600)
        signed_urls.append(private_url)
    return jsonify({'signed_urls': signed_urls})


# @main.route('/upload_callback', methods=['POST'])
# def post_image():
#     data = request.get_json()
#     blog_text = data.get('blog_text', '')
#     file_name = data.get('filename')
#     print('收到回调通知', data)
#     return jsonify(data=data, msg='success', detail='')


@main.route('/rich_post', methods=['POST'])
@limiter.limit("2/day", exempt_when=lambda: current_user.role_id == 3)
@jwt_required()
def create_post():
    data = request.get_json()
    content = data.get('content', '')
    image_urls = data.get('imageUrls', [])
    p = Post(body=content, body_html=None, type=PostType.IMAGE, author=current_user)
    db.session.add(p)
    db.session.flush()
    images = [Image(url=url, type=ImageType.POST, related_id=p.id) for url in image_urls]
    db.session.add_all(images)
    db.session.commit()
    return jsonify(data=[p.to_json()], msg='success', detail='')


@main.route('/del_image', methods=['DELETE'])
@jwt_required()
def delete_image():
    j = request.get_json()
    bucket_name = j.get('bucket')
    keys = j.get('key', [])
    del_qiniu_image(keys, bucket_name)
    return jsonify(data='', msg='success', detail='')


def del_qiniu_image(keys, bucket_name=os.getenv('QINIU_BUCKET_NAME')):
    ops = build_batch_delete(bucket_name, keys)
    bucket.batch(ops)


@main.route('/dir_name')
def query_qiniu_key():
    """查询七牛云某个bucket指定目录的所有文件名"""
    # 前缀
    prefix = request.args.get('prefix', 'userBackground/static')
    current_page = int(request.args.get('currentPage', 1))
    page_size = int(request.args.get('pageSize', 6))
    complete_url = bool(int(request.args.get('completeUrl', True)))
    # 列举条目
    limit = 50
    # bucket名字
    bucket_name = request.args.get('bucket', os.getenv('QINIU_BUCKET_NAME'))
    # 列举出除'/'的所有文件以及以'/'为分隔的所有前缀
    delimiter = None
    # 标记
    marker = None
    ret, eof, info = bucket.list(bucket_name, prefix, marker, limit, delimiter)
    j = json.loads(info.text_body)
    item_list = j.get('items')

    start = (current_page - 1) * page_size
    end = start + page_size
    # 第一个元素丢弃
    return jsonify(data=[get_avatars_url(item.get('key')) if complete_url else item.get('key') for item in
                         item_list[start + 1:end + 1]],
                   total=len(item_list) - 1, msg='success', detail='')


@main.route('/user/<int:user_id>/interest_images')
def get_favorite_book_image(user_id):
    book_images = Image.query.filter(and_(Image.type == ImageType.BOOK, Image.related_id == user_id)).all()
    return jsonify(data=[image.to_json() for image in book_images], msg='success', detail='')


@main.route('/user/<int:user_id>/interest_images', methods=['POST'])
@jwt_required()
def upload_favorite_book_image(user_id):
    """上传兴趣封面"""
    j = request.get_json()
    interest_urls = j.get('urls', [])
    interest_names = j.get('names', [])
    type_url = None
    if j.get('type') == 'movie':
        type_url = ImageType.MOVIE
    elif j.get('type') == 'book':
        type_url = ImageType.BOOK
    # 删除上次上传的
    last_upload_images = Image.query.filter(and_(Image.type == type_url, Image.related_id == user_id)).all()
    if last_upload_images:
        image_keys = [image.url for image in last_upload_images]
        del_qiniu_image(image_keys)
        for item in last_upload_images:
            db.session.delete(item)
        db.session.commit()
    images = [Image(url=url, type=type_url, describe=name, related_id=user_id) for url, name in
              zip(interest_urls, interest_names)]
    if images:
        db.session.add_all(images)
        db.session.commit()
    d = [image.to_json() for image in images]
    return jsonify(data=d, msg='success', detail=''), 200


# @main.route('/article/<int:article_id>/upload_image', methods=['POST'])
# def upload_article_image(article_id):
#     image_url = request.get_json().get('image_url')  # 假设前端传来了图片URL
#
#     new_image = Image(
#         url=image_url,
#         type='article',
#         related_id=article_id
#     )
#     db.session.add(new_image)
#     db.session.commit()
#
#     return jsonify({'message': 'Article image uploaded successfully'}), 201
#
#
# @main.route('/comment/<int:comment_id>/upload_image', methods=['POST'])
# def upload_comment_image(comment_id):
#     image_url = request.get_json().get('image_url')  # 假设前端传来了图片URL
#
#     new_image = Image(
#         url=image_url,
#         type='comment',
#         related_id=comment_id
#     )
#     db.session.add(new_image)
#     db.session.commit()
#
#     return jsonify({'message': 'Comment image uploaded successfully'}), 201

@main.route('/tags_list')
def get_all_tags():
    tags = Tag.query.all()
    return jsonify(data=[tag.name for tag in tags], msg='success', detail='')


@main.route('/update_user_tag', methods=['POST'])
@jwt_required()
def edit_user_tag():
    d = request.get_json()
    tag_add = set(d.get('tagAdd', []))
    tag_remove = set(d.get('tagRemove', []))
    # 添加新的标签
    for tag_name in tag_add:
        tag = Tag.query.filter_by(name=tag_name).first()
        if not tag:
            tag = Tag(name=tag_name)
            db.session.add(tag)
        current_user.tags.append(tag)

    # 删除被移除的标签
    for tag_name in tag_remove:
        tag = Tag.query.filter_by(name=tag_name).first()
        if tag:
            current_user.tags.remove(tag)
    db.session.commit()
    return jsonify(data='', msg='success', detail='')
