#!/bin/bash

function backend_to_remote() {
    backend_tar="flasky_backend.tar"
    if [[ -e  $backend_tar ]];then
      rm -f $backend_tar
      echo "已删除 $backend_tar"
    fi
    docker build -t nizhenshi/flasky_backend .
    docker save -o flasky_backend.tar nizhenshi/flasky_backend

    LOCAL_FILE=$backend_tar
    REMOTE_FILE="/root/user/"
    scp $LOCAL_FILE $ROMOTE_USER@$ROMOTE_HOST:$REMOTE_FILE
    if [[ $? -eq 0 ]];then
      echo "传输成功 $LOCAL_FILE"
    else
      echo "传输失败"
    fi
    if [[ -e  $backend_tar ]];then
      rm -f $backend_tar
      echo "已删除 $backend_tar"
    fi
}

