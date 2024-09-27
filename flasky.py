import click
import os
from flask_migrate import Migrate, upgrade
from app.models import User, Role
from app import create_app, db
from app.models import User, Follow, Role, Permission, Post, Comment
from app.fake import Fake

app = create_app(os.getenv('FLASK_CONFIG') or 'default')
migrate = Migrate(app, db)


@app.cli.command('deploy')
def deploy():
    upgrade()

    Role.insert_roles()

    User.add_self_follows()
    print('deploy command 执行成功')


@app.shell_context_processor
def make_shell_context():
    return dict(db=db, User=User, Follow=Follow, Role=Role,
                Permission=Permission, Post=Post, Comment=Comment, Fake=Fake)


@app.cli.command()
@click.option('--length', default=25,
              help='Number of functions to include in the profiler report.')
@click.option('--profile-dir', default=None,
              help='Directory where profiler data files are saved.')
def profile(length, profile_dir):
    """Start the application under the code profiler."""
    from werkzeug.middleware.profiler import ProfilerMiddleware
    app.wsgi_app = ProfilerMiddleware(app.wsgi_app, restrictions=[length],
                                      profile_dir=profile_dir)
    app.run()


def profile_1(length=25, profile_dir=None):
    """Start the application under the code profiler."""
    profile_dir = r'E:\project\Python\Flask_proj\PythonProject3_前后端分离\venv\backend_boke\profile'
    from werkzeug.middleware.profiler import ProfilerMiddleware
    app.wsgi_app = ProfilerMiddleware(app.wsgi_app, restrictions=[length],
                                      profile_dir=profile_dir)
    app.run(host='192.168.1.13', port=8081)


@app.cli.command('add')
@click.argument('some')
def add(some):
    print(some)

if __name__ == "__main__":
    profile_1()
