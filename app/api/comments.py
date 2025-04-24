from flask import jsonify, request, g, url_for, current_app
from flask_jwt_extended import current_user
from redis.cluster import command

from .. import db
from ..models import Post, Permission, Comment, Praise
from . import api
from .decorators import permission_required


@api.route('/comments/')
def get_comments():
    page = request.args.get('page', 1, type=int)
    pagination = Comment.query.order_by(Comment.timestamp.desc()).paginate(
        page=page, per_page=current_app.config['FLASKY_COMMENTS_PER_PAGE'],
        error_out=False)
    comments = pagination.items
    prev = None
    if pagination.has_prev:
        prev = url_for('api.get_comments', page=page - 1)
    next = None
    if pagination.has_next:
        next = url_for('api.get_comments', page=page + 1)
    return jsonify({
        'comments': [comment.to_json() for comment in comments],
        'prev': prev,
        'next': next,
        'count': pagination.total
    })


@api.route('/comments/<int:id>')
def get_comment(id):
    comment = Comment.query.get_or_404(id)
    return jsonify(comment.to_json())


@api.route('/posts/<int:id>/comments/', methods=['POST'])
@permission_required(Permission.COMMENT)
def new_post_comment(id):
    post = Post.query.get_or_404(id)
    comment = Comment.from_json(request.json)
    comment.author = g.current_user
    comment.post = post
    db.session.add(comment)
    db.session.commit()
    return jsonify(comment.to_json()), 201, \
        {'Location': url_for('api.get_comment', id=comment.id)}


@api.route('/posts/<int:id>/comments/')
def get_comments_new(id):
    """获取文章的根评论及第一层回复（适配direct_parent关系）"""
    post = Post.query.get_or_404(id)
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('size', current_app.config['FLASKY_COMMENTS_PER_PAGE'], type=int)
    # 获取根评论分页（parent_comment_id为None）
    root_comments_pagination = post.comments.filter(Comment.root_comment_id.is_(None)).order_by(
        Comment.timestamp.desc()).paginate(page=page, per_page=per_page, error_out=False)

    comments = []
    for root_comment in root_comments_pagination.items:
        comment_data = root_comment.to_json_new()
        # 获取该根评论下的第一层直接回复（direct_parent_id=根评论ID）
        first_level_replies, reply_total = get_replies_by_parent(root_comment.id, page=1)
        comment_data.update({
            'reply': {
                'list': first_level_replies,
                'total': reply_total,
            }
        })
        comments.append(comment_data)

    return jsonify(data=comments, total=root_comments_pagination.total, current_page=page, msg='success')


def get_replies_by_parent(root_comment_id, page):
    """
    获取指定父评论的所有直接回复
    :param root_comment_id: 根父评论ID
    """
    # 基础查询：直接回复
    query = Comment.query.filter_by(root_comment_id=root_comment_id).order_by(Comment.timestamp.desc())
    # 分页查询
    pagination = query.paginate(page=page, per_page=current_app.config['FLASKY_COMMENTS_REPLY_PER_PAGE'],
                                error_out=False)
    replies = []
    for reply in pagination.items:
        reply_data = reply.to_json_new()
        replies.append(reply_data)

    return replies, query.count()


@api.route('/reply_comments/')
def get_comment_replies():
    """获取指定评论的回复分页（支持无限层级嵌套）"""
    root_comment_id = request.args.get('rootCommentId', type=int)
    page = request.args.get('page', 1, type=int)
    # 分页时不自动嵌套，前端按需请求
    replies, total = get_replies_by_parent(root_comment_id=root_comment_id, page=page)

    return jsonify(data=replies, total=total, current_page=page, msg='success')
