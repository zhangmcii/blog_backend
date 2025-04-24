import os


def get_avatars_url(key):
    return f'http://{os.getenv('QINIU_DOMAIN')}/{key}-slim'
