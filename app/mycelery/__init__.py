from celery import Celery, Task


def celery_init_app(app) -> Celery:
    """
       启动目录(mac环境)：  cd blog_backend
       celery -A app.make_celery worker --loglevel INFO

       windows: celery -A app.make_celery worker --loglevel INFO -P eventlet
    """
    class FlaskTask(Task):
        def __call__(self, *args: object, **kwargs: object) -> object:
            with app.app_context():
                return self.run(*args, **kwargs)

    celery_app = Celery(app.name, task_cls=FlaskTask, BROKER_CONNECTION_RETRY_ON_STARTUP=True)
    celery_app.config_from_object(app.config["CELERY"])
    celery_app.set_default()
    app.extensions["celery"] = celery_app
    return celery_app


