# -*- coding: utf-8 -*-
# flake8: noqa
import os

from qiniu import Auth, put_file, etag
import qiniu.config


#构建鉴权对象
q = Auth(os.getenv('access_key'), os.getenv('secret_key'))

#要上传的空间
bucket_name = 'zimage'

#上传后保存的文件名
key = '1.webp'

#生成上传 Token，可以指定过期时间等
token = q.upload_token(bucket_name, key, 3600)

# 图片处理参数
# fops = '?imageslim/zlevel/2'

#要上传文件的本地路径
localfile = './1.webp'

ret, info = put_file(token, key, localfile, version='v2')
print(info)
assert ret['key'] == key
assert ret['hash'] == etag(localfile)
