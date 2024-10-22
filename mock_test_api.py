import os

import requests
# remote_url = os.getenv('ROMOTE_HOST')
# base_url = f'http://{remote_url}:4289'

remote_url =  '192.168.1.13'

base_url = f'http://{remote_url}:8081'
user = '123'
password = '123'

# 登录
r = requests.post(base_url+'/auth/login',json={'uiAccountName':user, 'uiPassword':password})
token = r.json()['token']
print(token)

# 随机生成文章
# r1 = requests.get(base_url+'/user_posts', headers={'Authorization':token})
# print(r1)

# 获取编号42文章的所有评论
# c = requests.get(base_url+'/api/v1/posts/42/comments/',headers={'Authorization':token})
# comments = c.json()['data']
# print(comments)
# print(c.json()['total'])

# 获取编号为42的文章
# p = requests.get(base_url+'/api/v1/posts/42',headers={'Authorization':token})
# post = p.json()['data']
# print(post)

# 修改编号为42的文章
# p = requests.put(base_url+'/api/v1/posts/42',headers={'Authorization':token},json={'body':'666'})
# post = p.json()['msg']
# data = p.json()['data']
# print(post)
# print(data)

# 获取用户资料
u = requests.get(base_url+'/api/v1/users/21',headers={'Authorization':token})
data = u.json()['data']
msg = u.json()['msg']
print(data)
print(msg)



