from faker import Faker
from .models import User, Post
from . import db
from random import randint
from flask import current_app

fake = Faker('zh-cn')


class Fake:
    locales = 'zh-cn'

    @staticmethod
    def users(count=10):
        fake = Faker(Fake.locales)
        db.create_all()
        i = 0
        while i < count:
            u = User(email=fake.email(), username=fake.user_name(), password='123', name=fake.name(),
                     location=fake.city(),
                     about_me='about me 个性说说')
            db.session.add(u)
            i += 1
            try:
                db.session.commit()
            except Exception as e:
                print(e)
                print("提交回滚")
                db.session.rollback()

    @staticmethod
    def posts(count=10):
        fake = Faker(Fake.locales)
        user_count = User.query.count()
        for i in range(count):
            u = User.query.offset(randint(0, user_count - 1)).first()
            p = Post(body=fake.text(), timestamp=fake.past_date(), author=u)
            db.session.add(p)
        db.session.commit()

    @staticmethod
    def admin():
        fake = Faker(Fake.locales)
        try:
            # 添加到User表
            u = User(email=current_app.config['FLASKY_ADMIN'], username='zmc', password='zmc', name='追梦少年',
                     location='上海',
                     about_me='随便说点啥...')
            db.session.add(u)
            db.session.commit()

            # 添加管理员的文章到post表
            u1 = User.query.filter_by(username='zmc').first()
            p = Post(body=fake.text(), timestamp=fake.past_date(), author=u1)
            db.session.add(p)
            db.session.commit()
        except Exception as e:
            print('出现异常,回滚', e)
            db.session.rollback()
