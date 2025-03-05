from app import create_app

flask_app = create_app('development')
celery_app = flask_app.extensions["celery"]