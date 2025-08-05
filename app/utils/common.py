import os
import socket


def get_avatars_url(key):
    return f'{os.getenv('QINIU_DOMAIN')}/{key}-slim'


def get_local_ip():
    """自动获取本机局域网 IPv4 地址"""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # 连接到一个外部地址（不需要实际连通）
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip


if __name__ == '__main__':
    ip = get_local_ip()
    print(ip)
