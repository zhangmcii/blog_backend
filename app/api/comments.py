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


# @api.route('/posts/<int:id>/comments/')
# def get_post_comments(id):
#     post = Post.query.get_or_404(id)
#     page = request.args.get('page', 1, type=int)
#     per_page = request.args.get('per_page',current_app.config['FLASKY_COMMENTS_PER_PAGE'], type=int)
#     pagination = post.comments.order_by(Comment.timestamp.asc()).paginate(
#         page=page, per_page=per_page, error_out=False)
#     comments = pagination.items
#     return jsonify(data=[comment.to_json() for comment in comments],total=pagination.total,msg='success')


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


# @api.route('/posts/<int:id>/comments/')
# def get_comments_new(id):
#     post = Post.query.get_or_404(id)
#     page = request.args.get('page', 1, type=int)
#     per_page = request.args.get('size', current_app.config['FLASKY_COMMENTS_PER_PAGE'], type=int)
#
#     # 得到不包含回复的评论
#     pagination = post.comments.filter(Comment.parent_comment_id.is_(None)).order_by(Comment.timestamp.desc()).paginate(
#         page=page, per_page=per_page, error_out=False)
#     comments = pagination.items
#     result = []
#     for comment in comments:
#         comment_id = comment.id
#         r = comment.to_json_new()
#         reply, reply_total = get_reply_comment_by_id(comment_id, 1)
#         r.update({'reply': {'total': reply_total, 'list': reply}})
#         result.append(r)
#     return jsonify(data=result, total=pagination.total, msg='success')
#
#
# def get_reply_comment_by_id(parent_id, page):
#     # 得到某个评论的所有回复评论
#     query = Comment.query.filter_by(parent_comment_id=parent_id).order_by(Comment.timestamp.desc())
#     pagination = query.paginate(
#         page=page, per_page=current_app.config['FLASKY_COMMENTS_REPLY_PER_PAGE'], error_out=False)
#     reply_comments = pagination.items
#     return [comment.to_json_new() for comment in reply_comments], query.count()
#
#
# @api.route('/reply_comments/')
# def get_reply_comment():
#     parent_id = request.args.get('parentId', type=int)
#     page = request.args.get('page', type=int)
#     print('parentId', parent_id)
#     print('page', page)
#     reply, total = get_reply_comment_by_id(parent_id, page)
#     return jsonify(data=reply, total=total, msg='success')


@api.route('/posts/<int:id>/comments/')
def get_comments_new(id):
    """获取文章的根评论及第一层回复（适配direct_parent关系）"""
    post = Post.query.get_or_404(id)
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('size', current_app.config['FLASKY_COMMENTS_PER_PAGE'], type=int)

    # 获取根评论分页（parent_comment_id为None）
    root_comments_pagination = post.comments.filter(Comment.parent_comment_id.is_(None)).order_by(
        Comment.timestamp.desc()).paginate(page=page, per_page=per_page, error_out=False)

    comments = []
    for root_comment in root_comments_pagination.items:
        comment_data = root_comment.to_json_new()
        # 获取该根评论下的第一层直接回复（direct_parent_id=根评论ID）
        first_level_replies, reply_total = get_replies_by_parent(root_comment.id, page=1, include_nested=False)
        comment_data.update({
            'replies': {
                'list': first_level_replies,
                'total': reply_total,
                'has_more': reply_total > current_app.config['FLASKY_COMMENTS_REPLY_PER_PAGE']
            }
        })
        comments.append(comment_data)

    return jsonify(data=comments, total=root_comments_pagination.total, current_page=page, msg='success')


def get_replies_by_parent(parent_id, page, include_nested=True):
    """
    获取指定父评论的所有直接回复
    :param parent_id: 直接父评论ID（对应direct_parent_id）
    :param include_nested: 是否包含嵌套回复（当需要无限层级时使用递归）
    """
    # 基础查询：直接回复
    query = Comment.query.filter_by(direct_parent_id=parent_id).order_by(Comment.timestamp.asc())

    # 分页查询
    pagination = query.paginate(page=page, per_page=current_app.config['FLASKY_COMMENTS_REPLY_PER_PAGE'],
                                error_out=False)

    replies = []
    for reply in pagination.items:
        reply_data = reply.to_json_new()
        if include_nested:
            # 递归获取嵌套回复
            nested_replies, _ = get_replies_by_parent(reply.id, page=1)
            reply_data['replies'] = nested_replies
        replies.append(reply_data)

    return replies, query.count()


@api.route('/comments/replies')
def get_comment_replies():
    """获取指定评论的回复分页（支持无限层级嵌套）"""
    parent_id = request.args.get('parent_id', type=int)
    page = request.args.get('page', 1, type=int)

    # 验证父评论存在且属于当前文章
    parent_comment = Comment.query.filter_by(id=parent_id).first_or_404()

    # 分页时不自动嵌套，前端按需请求
    replies, total = get_replies_by_parent(parent_id=parent_id, page=page, include_nested=False)

    return jsonify(data=replies, total=total, current_page=page, msg='success')
