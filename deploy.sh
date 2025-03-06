source /Users/v/Documents/proj/blog/blog_front/front.sh
source backend.sh

function run_container() {
  echo "传入参数为:  $1"
  cmd_front=""
  cmd_backend=""
  remote_cmd_front="docker rm -f flasky_front;docker rmi nizhenshi/flasky_front;docker load -i flasky_front.tar;docker run --name flasky_front -d -p 1717:80  nizhenshi/flasky_front:latest;"
  remote_cmd_backend="docker rm -f flasky_backend;docker rmi nizhenshi/flasky_backend;docker load -i flasky_backend.tar;docker run --name flasky_backend -d -p 4289:5000 --network database_n  -e DATABASE_URL=mysql+pymysql://flasky:1234@mysql/flasky -e MAIL_USERNAME=zmc_li@foxmail.com -e MAIL_PASSWORD=idycznxncyvhdeef -e REDIS_URL=redis://:1234@myredis:6379/0  -e REDIS_HOST=myredis  nizhenshi/flasky_backend:latest;"

  if [ $1 == "front" ];then
    cmd_front=$remote_cmd_front
  elif [ $1 == "backend" ]; then
    cmd_backend=$remote_cmd_backend
  elif [ $1 == "all" ]; then
    cmd_front=$remote_cmd_front
    cmd_backend=$remote_cmd_backend
  fi
  echo "cmd_front:" $cmd_front
  echo "cmd_backend:" $cmd_backend
  ssh $ROMOTE_USER@$ROMOTE_HOST "cd /root/user;$cmd_front $cmd_backend"
  if [[ $? -eq 0 ]];then
    echo "执行成功"
  else
    echo "执行失败"
  fi
}


function deploy_front(){
  front_to_remote
  run_container "front"
}

function deploy_backend() {
    backend_to_remote
    run_container "backend"
}

function deploy() {
    front_to_remote &
    front=$!
    backend_to_remote &
    backend=$!
    wait $front
    wait $backend
    run_container "all"
}

deploy_backend