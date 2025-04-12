import time
from .. import redis

class UserStatus:
    def __init__(self):
        self.redis = redis

    def init_user_status(self,user_id):
        # 初始化用户状态
        self.redis.hset(f"user:{user_id}", mapping={
            "online": 1,
            "active_chat": "",
            "last_active": int(time.time())
        })

    def user_online(self, user_id):
        """标记用户在线"""
        self.redis.hset(f'user:{user_id}', 'online', 1)
        self.update_last_active(user_id)

    def user_offline(self, user_id):
        """标记用户离线"""
        self.redis.hdel(f'user:{user_id}', 'online')

    def update_last_active(self, user_id):
        """更新最后活跃时间"""
        self.redis.hset(f'user:{user_id}', 'last_active', int(time.time()))

    def is_online(self, user_id):
        """检查是否在线"""
        return self.redis.hexists(f'user:{user_id}', 'online')

    def get_last_active(self, user_id):
        """获取最后活跃时间"""
        return self.redis.hget(f'user:{user_id}', 'last_active' or 0)

    def expire(self, user_id, expire_time=60 * 5):
        """设置用户状态过期时间，默认5分钟"""
        self.redis.expire(f'user:{user_id}', expire_time)

    def active_chat(self, user_id, target_id):
        """记录聊天的目标用户"""
        self.redis.hset(f'user:{user_id}', 'active_chat', target_id)

    def get_user_status(self, user_id):
        if not redis.exists(f'user:{user_id}'):
            return None
        return self.redis.hgetall(f'user:{user_id}')

    def del_user_status(self, user_id):
        self.redis.delete(f'user:{user_id}')


