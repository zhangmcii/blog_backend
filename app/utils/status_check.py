import time
from threading import Thread
from .status import UserStatus
from ..models import User

status_manager = UserStatus()


# 定时任务（每分钟执行）
def check_inactive_users():
    duration = 30
    print(f'加入检测用户状态线程， 每{duration}s执行一次')
    while True:
        # 每30秒执行一次
        time.sleep(duration)
        print('检测用户状态开始..')

        # 获取所有用户
        all_users = User.query.all()

        for user in all_users:
            last_active = status_manager.get_last_active(user.id)
            if time.time() - last_active > 60:  # 超过60秒未活跃
                status_manager.del_user_status(user.id)

Thread(target=check_inactive_users, daemon=True).start()

