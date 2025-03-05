from celery import shared_task
from flask import render_template, current_app
from flask_mail import Message
from . import mail



# 发送一个html 多线程
@shared_task(ignore_result=False)
def send_email(to, subject, template, **kwargs):
    try:
        message = Message(subject=subject, recipients=[to])
        message.html = render_template('email_temp.html', **kwargs)
        mail.send(message)
    except Exception as e:
        print(e)
        print('发送失败')
