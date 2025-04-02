from flask import jsonify, request, g, url_for, current_app
from .. import db
from ..models import Post, Permission, Comment
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


@api.route('/posts/<int:id>/comments/')
def get_comments_new(id):
    post = Post.query.get_or_404(id)
    page = request.args.get('current', 1, type=int)
    per_page = request.args.get('size', current_app.config['FLASKY_COMMENTS_PER_PAGE'], type=int)

    # 得到不包含回复的评论
    pagination = post.comments.filter(Comment.parent_comment_id.is_(None)).order_by(Comment.timestamp.desc()).paginate(
        page=page, per_page=per_page, error_out=False)
    comments = pagination.items
    result = []
    for comment in comments:
        comment_id = comment.id
        # 根据comment_id得到该评论的点赞数
        # ----
        r = comment.to_json_new()
        reply, reply_total = get_reply_comment_by_id(comment_id, 1)
        r.update({'reply': {'total': reply_total, 'list': reply}})
        result.append(r)
    print('11', result)
    return jsonify(data=result, total=pagination.total, msg='success')


def get_reply_comment_by_id(parent_id, page):
    # 得到某个评论的所有回复评论
    query = Comment.query.filter_by(parent_comment_id=parent_id).order_by(Comment.timestamp.desc())
    pagination = query.paginate(
        page=page, per_page=current_app.config['FLASKY_COMMENTS_REPLY_PER_PAGE'], error_out=False)
    reply_comments = pagination.items
    for reply_comment in reply_comments:
        reply_comment_id = reply_comment.id
        # 根据reply_comment_id得到该评论的点赞数
        # ----
        pass
    return [comment.to_json_new() for comment in reply_comments], query.count()


@api.route('/reply_comments/')
def get_reply_comment():
    parent_id = request.args.get('parentId', type=int)
    page = request.args.get('page', type=int)
    print('parentId', parent_id)
    print('page', page)
    reply, total = get_reply_comment_by_id(parent_id, page)
    return jsonify(data=reply, total=total, msg='success')
