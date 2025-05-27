import time

from celery import shared_task
from flask import render_template
from flask_mail import Message
from app import mail




@shared_task(ignore_result=False)
def send_email(to, subject, **kwargs):
    try:
        message = Message(subject=subject, recipients=[to])
        message.html = render_template('email_temp.html', **kwargs)
        mail.send(message)
    except Exception as e:
        print(e)
        print('发送失败')

@shared_task(ignore_result=False)
def query_score(user_id):
    print(f'查询用户{user_id}的成绩')
    time.sleep(5)
    score = 'A+'
    print(f'查询用户{user_id}成绩查询成功')
    return {'status': 'SUCCESS', "score":score}

