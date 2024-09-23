from flask_jwt_extended import JWTManager, create_access_token, get_jwt_identity, jwt_required, current_user, \
    verify_jwt_in_request
from . import main
from ..models import User, Post, Permission
from ..decorators import permission_required
from flask import jsonify, current_app,request,abort

"""博客文章、关注者信息、评论信息"""


# --------------------------- 博客文章 ---------------------------
@main.route('/', methods=['GET', 'POST'])
def index():
    """处理博客文章的首页路由"""
    # if current_user.can(Permission.WRITE):
    #     return '写入成功'
    # show_followed = False
    # if show_followed:
    #     query = current_user.followed_posts
    # else:
    #     query = Post.query
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', current_app.config['FLASKY_POSTS_PER_PAGE'], type=int)
    query = Post.query
    paginate = query.order_by(Post.timestamp.desc()).paginate(page=page,
                                                            per_page=per_page,
                                                            error_out=False)
    posts = paginate.items
    # 分页
    return jsonify(data=[post.to_json() for post in posts],total=len(posts))


@main.route('/user/<username>')
@jwt_required(optional=True)
def user(username):
    """获取博客文章的资料页面路由"""
    user = User.query.filter_by(username=username).first()
    if not user:
        abort(404)

    # posts = user.posts.order_by(Post.timestamp.desc()).all()
    # 如果登录的用户时管理员，则会携带 电子邮件地址
    print(current_user)
    if current_user and current_user.is_administrator():
        return jsonify(data=user.to_json())
    j = user.to_json()
    j.pop('email', None)
    return jsonify(data=j)


@main.route('/edit/<int:id>', methods=['GET', 'POST'])
@jwt_required()
def edit(id):
    """编辑博客文章"""
    post = Post.query.get_or_404(id)
    if current_user != post.author and not current_user.can(Permission.ADMIN):
        abort(403)
    # 对表单编辑业务逻辑
    return "编辑成功"


# --------------------------- 关注 ---------------------------

@main.route('/follow/<username>')
@jwt_required()
@permission_required(Permission.FOLLOW)
def follow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.')
        return redirect(url_for('.index'))
    if current_user.is_following(user):
        flash('You are already following this user.')
        return redirect(url_for('.user', username=username))
    current_user.follow(user)
    db.session.commit()
    flash('You are now following %s.' % username)
    return redirect(url_for('.user', username=username))


@main.route('/unfollow/<username>')
@jwt_required()
@permission_required(Permission.FOLLOW)
def unfollow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.')
        return redirect(url_for('.index'))
    if not current_user.is_following(user):
        flash('You are not following this user.')
        return redirect(url_for('.user', username=username))
    current_user.unfollow(user)
    db.session.commit()
    flash('You are not following %s anymore.' % username)
    return redirect(url_for('.user', username=username))


@main.route('/followers/<username>')
def followers(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.')
        return redirect(url_for('.index'))
    return "followers"


@main.route('/followed_by/<username>')
def followed_by(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.')
        return redirect(url_for('.index'))
    return "followed_by"


# --------------------------- 评论 ---------------------------
@main.route('/post/<int:id>', methods=['GET', 'POST'])
def post(id):
    """为文章提供固定链接、博客评论"""
    post = Post.query.get_or_404(id)
    # 评论业务逻辑
    return "评论成功"


@main.route('/moderate')
@jwt_required()
@permission_required(Permission.MODERATE)
def moderate():
    """管理评论"""
    return "分页的评论"


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
