from threading import Lock


# 管理socket连接
class ManageSocket:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        self.user_socket = {}  # { user_id: set(sid_1, sid_2) }
        self.socket_user = {}  # { socket_id: user_id }
        self.lock = Lock()

    def add_user_socket(self, user_id, sid):
        with self.lock:
            # 清理已存在的
            if sid in self.socket_user:
                old_user = self.socket_user['sid']
                self.user_socket[old_user].discard(sid)
                if not self.user_socket[old_user]:
                    del self.user_socket[old_user]
            # 添加新映射
            if user_id not in self.user_socket:
                self.user_socket[user_id] = set()
            self.user_socket[user_id].add(sid)
            self.socket_user[sid] = user_id

    def get_user_socket(self, user_id):
        with self.lock:
            # 避免副本线程问题
            return self.user_socket.get(user_id, set()).copy()

    def remove_user_socket(self, sid):
        with self.lock:
            if sid in self.socket_user:
                user_id = self.socket_user[sid]
                self.user_socket[user_id].discard(sid)
                del self.socket_user[sid]
                if not self.user_socket[user_id]:
                    del self.user_socket[user_id]
