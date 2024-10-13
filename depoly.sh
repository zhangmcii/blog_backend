source /e/project/vue-proj/responsive/front.sh
source ./backend.sh

function run_container() {
    remote_cmd_front="docker rm -f flasky_front;docker rmi nizhenshi/flasky_front;docker load -i flasky_front.tar;docker run --name flasky_front -d -p 1717:80  nizhenshi/flasky_front:latest;"
    remote_cmd_backend="docker rm -f flasky_backend;docker rmi nizhenshi/flasky_backend;docker load -i flasky_backend.tar;docker run --name flasky_backend -d -p 4289:5000 --network database_n  -e DATABASE_URL=mysql+pymysql://flasky:1234@mysql/flasky -e MAIL_USERNAME=zmc_li@foxmail.com -e MAIL_PASSWORD=idycznxncyvhdeef -e REDIS_URL=redis://:1234@myredis:6379/0  nizhenshi/flasky_backend:latest;"
    ssh $ROMOTE_USER@$ROMOTE_HOST "cd /root/user;$remote_cmd_front $remote_cmd_backend"
    if [[ $? -eq 0 ]];then
      echo "执行成功"
    else
      echo "执行失败"
    fi
}

front_to_remote &
front=$!
backend_to_remote &
backend=$!
wait $front
wait $backend

run_container


