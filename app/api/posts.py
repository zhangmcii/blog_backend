import os
from flask import jsonify, request, url_for, current_app, abort
from flask_jwt_extended import current_user, jwt_required
from .. import db
from ..models import Post, Permission, Image, ImageType, PostType
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
    # 编辑markdown文章时新增图片
    images = j.get('images')
    if images:
        images = [
            Image(url=image.get('url', ''), type=ImageType.POST, describe=image.get('pos', ''), related_id=post.id)
            for image in images]
        db.session.add_all(images)
    db.session.commit()
    return jsonify(data=post.to_json(), msg="success")


@api.route('/posts/<int:id>', methods=['DELETE'])
@jwt_required()
def del_post(id):
    # 删除文章，同时也要删除文章中的图片url
    is_contain_image, data = None, None
    try:
        p = Post.query.filter_by(id=id, author_id=current_user.id).first()
        if not p:
            return jsonify(data='', msg='fail', detail='文章不存在')
        is_contain_image = p.type == PostType.IMAGE
        to_del_urls = []
        if is_contain_image:
            post_images = Image.query.filter(Image.type == ImageType.POST, Image.related_id == p.id).order_by(
                Image.id.asc()).all()
            to_del_urls = [image.url for image in post_images]
            # 删除图片
            data = {'bucket_name': os.getenv('QINIU_BUCKET_NAME', ''), 'keys': to_del_urls}
        db.session.delete(p)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify(data='', msg='fail', detail=str(e))
    if is_contain_image and to_del_urls:
        # 传递j,执行图片删除
        del_qiniu_image(**data)
    return jsonify(data='', msg='success', detail='')


@api.route("/posts/timeline/<int:user_id>")
def get_user_posts_grouped_by_year(user_id):
    """获取当前用户按年度分组的文章时间轴数据"""
    try:
        # 查询当前用户已发布的文章，按年份和发布时间排序
        posts = Post.query.filter(
            Post.author_id == user_id,
        ).order_by(
            Post.year.desc(),  # 先按年份倒序
            Post.timestamp.desc()  # 同一年的文章按发布时间倒序
        ).all()

        # 按年份分组，构建 {年份: 文章数组} 格式
        timeline_data = {}
        for post in posts:
            # 获取年份作为键（整数类型，如2025）
            year = post.year
            # 如果该年份还没有在字典中，初始化一个空列表
            if year not in timeline_data:
                timeline_data[year] = []
            # 将文章数据转换为字典并添加到对应年份的列表
            timeline_data[year].append({
                'id': post.id,
                'title': post.title,
                'timestamp': post.timestamp.strftime('%Y-%m-%d'),  # 格式化日期为字符串
                'description': post.summary  # 假设用summary字段作为description
            })

        return jsonify(
            data=timeline_data,  # 直接返回构建好的字典
            msg='success'
        )

    except Exception as e:
        return jsonify(
            data={},  # 错误时返回空对象
            msg=f'获取时间轴数据失败: {str(e)}'
        )
