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
