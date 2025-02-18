from datetime import timedelta
from flask import current_app, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from . import db
from . import jwt
from .utils.time_util import DateUtils
from flask_jwt_extended import current_user, create_access_token
import random
from . import redis
from .exceptions import ValidationError


class Permission:
    FOLLOW = 1
    COMMENT = 2
    WRITE = 4
    MODERATE = 8
    ADMIN = 16


class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    default = db.Column(db.Boolean, default=False, index=True)
    permissions = db.Column(db.Integer)
    users = db.relationship('User', backref='role', lazy='dynamic')

    def __init__(self, **kwargs):
        super(Role, self).__init__(**kwargs)
        if self.permissions is None:
            self.permissions = 0

    @staticmethod
    def insert_roles():
        db.create_all()
        roles = {
            'User': [Permission.FOLLOW, Permission.COMMENT, Permission.WRITE],
            'Moderator': [Permission.FOLLOW, Permission.COMMENT,
                          Permission.WRITE, Permission.MODERATE],
            'Administrator': [Permission.FOLLOW, Permission.COMMENT,
                              Permission.WRITE, Permission.MODERATE,
                              Permission.ADMIN],
        }
        default_role = 'User'
        for r in roles:
            role = Role.query.filter_by(name=r).first()
            if role is None:
                role = Role(name=r)
            role.reset_permissions()
            for perm in roles[r]:
                role.add_permission(perm)
            role.default = (role.name == default_role)
            db.session.add(role)
        db.session.commit()

    def add_permission(self, perm):
        if not self.has_permission(perm):
            self.permissions += perm

    def remove_permission(self, perm):
        if self.has_permission(perm):
            self.permissions -= perm

    def reset_permissions(self):
        self.permissions = 0

    def has_permission(self, perm):
        return self.permissions & perm == perm

    def __repr__(self):
        return '<Role %r>' % self.name


class Follow(db.Model):
    __tablename__ = 'follows'
    follower_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    followed_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    timestamp = db.Column(db.DateTime, default=DateUtils.now_time)


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(64), unique=True, index=True)
    username = db.Column(db.String(64), unique=True, index=True)
    password_hash = db.Column(db.String(255))
    confirmed = db.Column(db.Boolean, default=False)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    # 用户资料
    name = db.Column(db.String(64))
    location = db.Column(db.String(64))
    about_me = db.Column(db.Text())
    member_since = db.Column(db.DateTime(), default=DateUtils.now_time)
    last_seen = db.Column(db.DateTime(), default=DateUtils.now_time)
    image = db.Column(db.String(255))
    # 图像
    avatar_hash = db.Column(db.String(32))

    posts = db.relationship('Post', backref='author', lazy='dynamic')

    praises = db.relationship('Praise', backref='author', lazy='dynamic')

    # 关注
    followed = db.relationship('Follow', foreign_keys=[Follow.follower_id],
                               backref=db.backref('follower', lazy='joined'), lazy='dynamic',
                               cascade='all, delete-orphan')
    followers = db.relationship('Follow', foreign_keys=[Follow.followed_id],
                                backref=db.backref('followed', lazy='joined'), lazy='dynamic',
                                cascade='all, delete-orphan')
    comments = db.relationship('Comment', backref='author', lazy='dynamic')

    @property
    def followed_posts(self):
        return Post.query.join(Follow, Follow.followed_id == Post.author_id).filter(Follow.follower_id == self.id)

    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        if not self.role:
            if self.email == current_app.config['FLASKY_ADMIN'] and self.confirmed:
                self.role = Role.query.filter_by(name='Administrator').first()
            else:
                self.role = Role.query.filter_by(default=True).first()
        self.follow(self)

    def ping(self):
        self.last_seen = DateUtils.now_time()
        db.session.add(self)
        db.session.commit()

    def can(self, perm):
        return self.role is not None and self.role.has_permission(perm)

    def is_administrator(self):
        return self.can(Permission.ADMIN)

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_confirmation_token(self, expiration=3600):
        additional_claims = {"confirm": self.id}
        confirm_token = create_access_token(identity=current_user, additional_claims=additional_claims,
                                            expires_delta=timedelta(seconds=expiration))
        return confirm_token

    @staticmethod
    def generate_code(email, expiration=60 * 3):
        code = random.randint(100000, 999999)
        print('email', email)
        print('code', code)
        redis.setex(email, expiration, code)
        return code

    @staticmethod
    def compare_code(email, code):
        try:
            result = User.get_value(email)
            print('result', result)
        except Exception as e:
            print('redis 取值失败', e)
            return False
        if not result:
            print('无对应键')
            return False
        if code != result:
            print('验证码不匹配')
            return False
        return True

    def confirm(self, email, code):
        if User.compare_code(email, code):
            self.confirmed = True
            # 角色设置管理员
            if self.email == current_app.config['FLASKY_ADMIN'] and self.confirmed:
                self.role = Role.query.filter_by(name='Administrator').first()
            db.session.add(self)
            redis.delete(email)
            return True
        else:
            return False

    def change_email(self, new_email, code):
        if User.compare_code(new_email, code):
            self.email = new_email
            db.session.add(self)
            return True
        else:
            return False

    @staticmethod
    def get_value(key):
        # 获取键值
        value = redis.get(key)
        if value:
            return value.decode()
        return value

    def follow(self, user):
        if not self.is_following(user):
            f = Follow(follower=self, followed=user)
            db.session.add(f)

    def unfollow(self, user):
        f = self.followed.filter_by(followed_id=user.id).first()
        if f:
            db.session.delete(f)

    def is_following(self, user):
        if user and not user.id:
            return False
        return self.followed.filter_by(
            followed_id=user.id).first() is not None

    def is_followed_by(self, user):
        if user and not user.id:
            return False
        return self.followers.filter_by(
            follower_id=user.id).first() is not None

    @staticmethod
    def add_self_follows():
        for user in User.query.all():
            if not user.is_following(user):
                user.follow(user)
                db.session.add(user)
                db.session.commit()

    def to_json(self, user):
        json_user = {
            'url': url_for('api.get_user', id=self.id),
            'id': self.id,
            'username': self.username,
            'name': self.name,
            'location': self.location,
            'about_me': self.about_me,
            'member_since': DateUtils.datetime_to_str(self.member_since),
            'last_seen': DateUtils.datetime_to_str(self.last_seen),
            'image': self.image,
            'admin': self.is_administrator(),

            'email': self.email,
            'role': self.role.id,
            'confirmed': self.confirmed,

            'posts_url': url_for('api.get_user_posts', id=self.id),
            'followed_posts_url': url_for('api.get_user_followed_posts',
                                          id=self.id),
            'post_count': self.posts.count(),
            'followers_count': self.followers.count() - 1,
            'followed_count': self.followed.count() - 1,
            # 是否被当前用户关注
            'is_followed_by_current_user': self.is_followed_by(current_user) if current_user else self.is_followed_by(
                user),
            # 是否关注了当前用户
            'is_following_current_user': self.is_following(current_user) if current_user else self.is_following(user)
        }
        return json_user

    def __repr__(self):
        return '<User %r>' % self.username


class AnonymousUser:
    def can(self, permissions):
        return False

    def is_administrator(self):
        return False


@jwt.user_identity_loader
def user_identify_lookup(user):
    return user.id


@jwt.user_lookup_loader
def user_lookup_callback(__jwt_header, jwt_data):
    identify = jwt_data["sub"]
    return User.query.filter_by(id=identify).one_or_none()


class Post(db.Model):
    __tablename__ = 'posts'
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)
    body_html = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=DateUtils.now_time)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    comments = db.relationship('Comment', backref='post', lazy='dynamic')
    praise = db.relationship('Praise', backref='post', lazy='dynamic')

    def to_json(self):
        json_post = {
            'url': url_for('api.get_post', id=self.id),
            'id': self.id,
            'body': self.body,
            'body_html': self.body_html,
            'timestamp': DateUtils.datetime_to_str(self.timestamp),
            'author': self.author.username,
            'nick_name': self.author.name,
            'comment_count': self.comments.count(),
            'image': self.author.image,
            'praise_num': self.praise.count(),
            'has_praised': Praise.hasPraised(self.id)
        }
        return json_post

    @staticmethod
    def from_json(json_post):
        body = json_post.get('body')
        if body is None or body == '':
            raise ValidationError('post does not have a body')
        return Post(body=body)


class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text)
    body_html = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=DateUtils.now_time)
    disabled = db.Column(db.Boolean)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'))

    # 子评论
    parent_comment_id = db.Column(db.Integer, db.ForeignKey('comments.id'))
    # remote_side设置为多对一
    parent_comment = db.relationship('Comment', back_populates='sub_comment', remote_side=[id])
    # 默认一对多
    sub_comment = db.relationship('Comment', back_populates='parent_comment', cascade='all, delete-orphan')

    def to_json(self):
        json_comment = {
            'id': self.id,
            'author': self.author.username,
            'body': self.body,
            'body_html': self.body_html,
            'disabled': self.disabled,
            'timestamp': DateUtils.datetime_to_str(self.timestamp),
            'parent_comment_id': self.parent_comment_id
            # 'url': url_for('api.get_comment', id=self.id),
            # 'post_url': url_for('api.get_post', id=self.post_id),
            # 'author_url': url_for('api.get_user', id=self.author_id),
        }
        return json_comment

    @staticmethod
    def from_json(json_comment):
        body = json_comment.get('body')
        if body is None or body == '':
            raise ValidationError('comment does not have a body')
        return Comment(body=body)


class Praise(db.Model):
    __tablename__ = 'praise'
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'))

    @staticmethod
    def hasPraised(post_id):
        r = Praise.query.filter_by(post_id=post_id, author_id=current_user.id).first()
        return True if r else False
