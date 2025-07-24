import os


def get_avatars_url(key):
    return f'{os.getenv('QINIU_DOMAIN')}/{key}-slim'
