#!/bin/sh
source venv/bin/activate

# 转为utf-8
while true; do
    flask deploy
    if [[ "$?" == "0" ]]; then
        echo Depoly success
        break
    fi
    echo Deploy command failed, retrying in 5 secs...
    sleep 5
done

celery -A app.make_celery worker --loglevel INFO -P eventlet &
exec gunicorn -b :5000 --worker-class eventlet -w 3 --access-logfile - --error-logfile - flasky:app