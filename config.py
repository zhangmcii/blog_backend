import os
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    JWT_SECRET_KEY = "super-secret"
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(seconds=60 * 20)

    SECRET_KEY = os.environ.get('SECRET_KEY') or 'hard to guess string'
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.qq.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', '587'))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in \
                   ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME') or "zmc_li@foxmail.com"
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    # 发送者的邮箱
    MAIL_DEFAULT_SENDER = "zmc_li@foxmail.com"

    FLASKY_MAIL_SUBJECT_PREFIX = '[Flasky]'
    FLASKY_MAIL_SENDER = 'Flasky Admin <flasky@example.com>'
    FLASKY_ADMIN = 'zmc_li@foxmail.com'
    SSL_REDIRECT = False

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_RECORD_QUERIES = True

    FLASKY_POSTS_PER_PAGE = 10
    FLASKY_FOLLOWERS_PER_PAGE = 15
    FLASKY_COMMENTS_PER_PAGE = 10
    FLASKY_LOG_PER_PAGE = 15

    FLASKY_SLOW_DB_QUERY_TIME = 0.5

    @staticmethod
    def init_app(app):
        pass


class DevelopmentConfig(Config):
    DEBUG = True
    # mysql
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or \
                              'mysql+pymysql://LAPTOP-R3BSJ27E:1234@' + os.getenv('FLASK_RUN_HOST',
                                                                                  '') + ':3306/backend_flask?charset=utf8mb4'
    # redis
    REDIS_URL = os.environ.get('DEV_REDIS_URL') or "redis://:1234@" + os.getenv('FLASK_RUN_HOST',
                                                                                '') + ":6379/0"  # 格式：redis://:<password>@<host>:<port>/<db>

class TestingConfig(Config):
    # TESTING = True会导致flask_mail发送不了邮件
    TESTING = True
    DEBUG = True
    # mysql
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL') or \
                              'mysql+pymysql://LAPTOP-R3BSJ27E:1234@' + os.getenv('FLASK_RUN_HOST',
                                                                                  '') + ':3306/test_backend_flask?charset=utf8mb4'
    # redis
    REDIS_URL = os.environ.get('TEST_REDIS_URL') or "redis://:1234@" + os.getenv('FLASK_RUN_HOST',
                                                                                 '') + ":6379/0"  # 格式：redis://:<password>@<host>:<port>/<db>
    WTF_CSRF_ENABLED = False


class ProductionConfig(Config):
    # mysql
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
                              'mysql+pymysql://LAPTOP-R3BSJ27E:1234@' + os.getenv('FLASK_RUN_HOST',
                                                                                  '') + ':3306/backend_flask?charset=utf8mb4'
    # redis
    REDIS_URL = os.environ.get('REDIS_URL') or "redis://:1234@" + os.getenv('FLASK_RUN_HOST',
                                                                            '') + ":6379/0"  # 格式：redis://:<password>@<host>:<port>/<db>

    @classmethod
    def init_app(cls, app):
        Config.init_app(app)

        # email errors to the administrators
        import logging
        from logging.handlers import SMTPHandler
        credentials = None
        secure = None
        if getattr(cls, 'MAIL_USERNAME', None) is not None:
            credentials = (cls.MAIL_USERNAME, cls.MAIL_PASSWORD)
            if getattr(cls, 'MAIL_USE_TLS', None):
                secure = ()
        mail_handler = SMTPHandler(
            mailhost=(cls.MAIL_SERVER, cls.MAIL_PORT),
            fromaddr=cls.FLASKY_MAIL_SENDER,
            toaddrs=[cls.FLASKY_ADMIN],
            subject=cls.FLASKY_MAIL_SUBJECT_PREFIX + ' Application Error',
            credentials=credentials,
            secure=secure)
        mail_handler.setLevel(logging.ERROR)
        app.logger.addHandler(mail_handler)


class HerokuConfig(ProductionConfig):
    SSL_REDIRECT = True if os.environ.get('DYNO') else False

    @classmethod
    def init_app(cls, app):
        ProductionConfig.init_app(app)

        # handle reverse proxy server headers
        try:
            from werkzeug.middleware.proxy_fix import ProxyFix
        except ImportError:
            from werkzeug.contrib.fixers import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app)

        # log to stderr
        import logging
        from logging import StreamHandler
        file_handler = StreamHandler()
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)


class DockerConfig(ProductionConfig):
    @classmethod
    def init_app(cls, app):
        ProductionConfig.init_app(app)

        # log to stderr
        import logging
        from logging import StreamHandler
        file_handler = StreamHandler()
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)


class UnixConfig(ProductionConfig):
    @classmethod
    def init_app(cls, app):
        ProductionConfig.init_app(app)

        # log to syslog
        import logging
        from logging.handlers import SysLogHandler
        syslog_handler = SysLogHandler()
        syslog_handler.setLevel(logging.INFO)
        app.logger.addHandler(syslog_handler)


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'heroku': HerokuConfig,
    'docker': DockerConfig,
    'unix': UnixConfig,

    'default': DevelopmentConfig
}
