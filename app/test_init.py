import requests

# url = 'http://localhost:8081'

url = 'http://192.168.1.13:8081'

#
# res = requests.post(url+'/auth/login', json={'uiAccountName':'David Richardson', 'uiPassword':'123'})
# print(res.json())
# token = res.json().get('token')
#
#
# res = requests.get(url+'/logined')
# print(res.json())
#
# res = requests.get(url+'/logined', headers={'Authorization':token})
# print(res)
#
# res = requests.get(url+'/protected', headers={'Authorization':token})
# print(res)
#
#
# res = requests.get(url+'/main/user/zsc', headers={'Authorization':token})
# print(res)
#
#
# res = requests.get(url + '/followers/gaotao')
# print(res.text)

# res = requests.post(url + '/post/37',json={"body":6666})
# print(res.text)


# res = requests.post(url + '/auth/register',json={"username":6666, 'password':'123','email':'12'})
# print(res.text)

# res = requests.get(url + '/followers/')
# print(res.text)
import os
print(os.getenv('MAIL_PASSWORD'))