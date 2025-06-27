from flask import request
from flask_jwt_extended import jwt_required, decode_token
from flask_socketio import join_room, disconnect, ConnectionRefusedError
from . import socketio, db
from .utils.socket_util import ManageSocket
from .utils.status import UserStatus
from .models import User, Message, Notification, NotificationType

status_manager = UserStatus()
socket_manager = ManageSocket()


@socketio.on('connect')
@jwt_required(optional=True)
def handle_connect():
    user_id = verify_token_in_websocket()
    status_manager.init_user_status(user_id)
    record_user_connect(user_id)
    join_room(str(user_id))
    print(f"用户 {user_id} connected to room。新连接：{request.sid}")


@socketio.on('disconnect')
@jwt_required(optional=True)
def handle_disconnect():
    user_id = verify_token_in_websocket()
    socket_manager.remove_user_socket(request.sid)
    status_manager.del_user_status(user_id)
    print(f'用户{user_id}断开了：', status_manager.get_user_status(user_id))


@socketio.on('heartbeat')
@jwt_required(optional=True)
def handle_heartbeat():
    user_id = verify_token_in_websocket()
    status_manager.update_last_active(user_id)


@socketio.on('enter_chat')
@jwt_required(optional=True)
def handle_enter_chat(data):
    user_id = verify_token_in_websocket()
    target_id = data['targetId']

    status_manager.active_chat(user_id, target_id)
    status_manager.update_last_active(user_id)
    status_manager.expire(60 * 5)

    # 标记已读并清除通知
    Message.query.filter(Message.receiver_id == user_id, Message.sender_id == target_id,
                         Message.is_read == False).update({'is_read': True}, synchronize_session='fetch')
    # 有问题 不应该删除。 应该标记为已读
    query = Notification.query.filter_by(receiver_id=user_id, trigger_user_id=target_id, type=NotificationType.CHAT,
                                         is_read=False).update({'is_read': True})
    # query = Notification.query.filter_by(receiver_id=user_id, trigger_user_id=target_id, type=NotificationType.CHAT).delete()
    print('query', query)
    db.session.commit()
    print(f'{user_id}进入聊天页{target_id}了')


@socketio.on('send_message')
@jwt_required(optional=True)
def handle_send_message(data):
    sender_id = verify_token_in_websocket()
    receiver_id = data['receiver_id']
    print(f'{sender_id}发给{receiver_id}的新消息：{data['content']}')
    msg = Message(sender_id=sender_id, receiver_id=receiver_id, content=data['content'])
    db.session.add(msg)
    db.session.flush()
    try:
        receiver_status = status_manager.get_user_status(receiver_id)
        print('receiver_status', receiver_status)
        if receiver_status and receiver_status.get('active_chat') == str(sender_id):
            print(f'{sender_id},{receiver_id}都在聊天页面')
            msg.is_read = True
            socketio.emit('new_message', msg.to_json(), to=str(receiver_id))
        else:
            # 接收者离线或者不在聊天页面，都生成通知
            notification = Notification(receiver_id=receiver_id, trigger_user_id=sender_id, type=NotificationType.CHAT)
            db.session.add(notification)
            db.session.flush()
            if receiver_status is not None and receiver_status.get('online') == '1':
                print(f'{receiver_id}在线但不在聊天页')
                socketio.emit('new_notification', notification.to_json(), to=str(receiver_id))
            else:
                print(f'{receiver_id}离线，消息已保存，下次上线可查看通知')
        db.session.commit()
        socketio.emit('message_sent', msg.to_json(), room=request.sid)
    except Exception as e:
        db.session.rollback()
        print('消息发送失败', str(e))


def verify_token_in_websocket():
    """连接websocket时验证用户身份"""
    try:
        token = request.args.get('token')
        if not token:
            raise ConnectionRefusedError('Unauthorized')
        raw_token = token.replace("Bearer ", "", 1)
        # 手动解码 Token
        decoded_token = decode_token(raw_token)
        user_id = decoded_token["sub"]
    except Exception:
        raise ConnectionRefusedError("websocket身份验证失败，token解析错误")
    # 检查用户是否存在
    if not User.query.get(user_id):
        raise ConnectionRefusedError("websocket身份验证失败，用户不在")
    return user_id


def record_user_connect(user_id):
    """记录已连接的用户"""
    old_sids = socket_manager.user_socket.get(user_id, set())
    for sid in list(old_sids):
        disconnect(sid)
        socket_manager.remove_user_socket(sid)
    # 记录连接
    # 读取不了current_user.username。因为这不是http请求，无法应用jwt_required，所以读取不了current_user对象的属性
    socket_manager.add_user_socket(user_id, request.sid)
